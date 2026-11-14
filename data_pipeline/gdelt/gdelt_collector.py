#!/usr/bin/env python3
"""
gdelt_collector.py - GDELT 2.0 GKG collector for IntelliHedge V2 (Stage 1).

Two sub-commands:

  check-archive   Verify the live archive: lastupdate.txt, the master file list
                  (is it stale?) and direct HEAD probes of the first/last 15-minute
                  slot of the target period. Writes archive_check.json.

  download        Download every 15-minute GKG file in [--start, --end] (UTC dates,
                  inclusive). File names are GENERATED from the timestamp, so the
                  collector does NOT depend on masterfilelist.txt being current.
                  Files are validated (zip integrity, non-empty CSV member, optional
                  MD5 against the master list), retried on network errors, and never
                  re-downloaded if a valid copy already exists.

Raw files are stored untouched under --raw-dir; a manifest.csv records the outcome
for every expected slot (ok / cached / missing_404 / failed), which is the source of
truth for "missing dates / slots".

Examples
  python gdelt_collector.py check-archive --start 2026-10-01 --end 2026-10-31
  python gdelt_collector.py download --start 2026-10-01 --end 2026-10-31
  python gdelt_collector.py download --start 2026-10-01 --end 2026-10-07 --stream both
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator, Optional

import requests

LOG = logging.getLogger("gdelt_collector")

BASE_URLS = ["https://data.gdeltproject.org/gdeltv2", "http://data.gdeltproject.org/gdeltv2"]
SUFFIX = {"english": ".gkg.csv.zip", "translation": ".translation.gkg.csv.zip"}
MASTER = {"english": "masterfilelist.txt", "translation": "masterfilelist-translation.txt"}
LASTUPDATE = {"english": "lastupdate.txt", "translation": "lastupdate-translation.txt"}
USER_AGENT = "IntelliHedge-V2-research/1.0 (GDELT GKG evaluation)"
SLOT = timedelta(minutes=15)


# --------------------------------------------------------------------------- helpers
def parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def iter_slots(start: datetime, end_inclusive_day: datetime) -> Iterator[datetime]:
    """Every 15-minute slot from start 00:00 to end 23:45 UTC."""
    t = start
    stop = end_inclusive_day + timedelta(days=1)
    while t < stop:
        yield t
        t += SLOT


def slot_name(t: datetime) -> str:
    return t.strftime("%Y%m%d%H%M%S")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_zip(path: Path) -> tuple[bool, str]:
    """Return (ok, reason). A valid GKG file is a zip with one non-empty .csv member."""
    try:
        if path.stat().st_size == 0:
            return False, "empty file"
        if not zipfile.is_zipfile(path):
            return False, "not a zip file"
        with zipfile.ZipFile(path) as zf:
            bad = zf.testzip()
            if bad is not None:
                return False, f"corrupt member {bad}"
            members = [i for i in zf.infolist() if i.filename.lower().endswith(".csv")]
            if len(members) != 1:
                return False, f"expected 1 csv member, found {len(members)}"
            if members[0].file_size == 0:
                return False, "csv member is empty"
    except (zipfile.BadZipFile, OSError) as e:
        return False, f"zip error: {e}"
    return True, "ok"


# --------------------------------------------------------------------------- manifest
@dataclass
class Result:
    slot: str
    stream: str
    status: str            # ok | cached | missing_404 | failed
    url: str = ""
    http_status: Optional[int] = None
    bytes: int = 0
    sha256: str = ""
    md5_ok: Optional[bool] = None
    attempts: int = 0
    error: str = ""


# --------------------------------------------------------------------------- master list
def load_master_md5(stream: str, start: datetime, end: datetime, cache_dir: Path,
                    session: requests.Session) -> dict[str, tuple[int, str]]:
    """
    Stream masterfilelist and keep only entries inside the period.
    Returns {slot_name: (size, md5)}. Used for integrity checks only, never to decide
    which files exist (the list may be stale).
    """
    wanted_prefix = {f"{d:%Y%m%d}" for d in (start + timedelta(days=i)
                                           for i in range((end - start).days + 1))}
    out: dict[str, tuple[int, str]] = {}
    suffix = SUFFIX[stream]
    for base in BASE_URLS:
        url = f"{base}/{MASTER[stream]}"
        try:
            with session.get(url, stream=True, timeout=(15, 120)) as r:
                if r.status_code != 200:
                    LOG.warning("masterlist %s -> HTTP %s", url, r.status_code)
                    continue
                for raw in r.iter_lines(decode_unicode=True):
                    if not raw or not raw.endswith(suffix):
                        continue
                    parts = raw.split(" ")
                    if len(parts) != 3:
                        continue
                    size, md5, link = parts
                    fname = link.rsplit("/", 1)[-1]
                    ts = fname.split(".")[0]
                    if ts[:8] in wanted_prefix:
                        out[ts] = (int(size), md5)
            return out
        except requests.RequestException as e:
            LOG.warning("masterlist fetch failed (%s): %s", url, e)
    return out


# --------------------------------------------------------------------------- download
def download_one(session: requests.Session, t: datetime, stream: str, raw_dir: Path,
                 retries: int, backoff: float, timeout: int,
                 master: dict[str, tuple[int, str]], verify_md5: bool) -> Result:
    name = slot_name(t)
    fname = f"{name}{SUFFIX[stream]}"
    dest = raw_dir / name[:8] / fname
    dest.parent.mkdir(parents=True, exist_ok=True)
    res = Result(slot=name, stream=stream, status="failed", url=f"{BASE_URLS[0]}/{fname}")

    # 1. avoid unnecessary downloads
    if dest.exists():
        ok, why = validate_zip(dest)
        if ok:
            res.status, res.bytes, res.sha256 = "cached", dest.stat().st_size, sha256_file(dest)
            if name in master:
                res.md5_ok = md5_file(dest) == master[name][1]
            return res
        LOG.warning("cached file %s invalid (%s) - re-downloading", dest.name, why)
        dest.unlink()

    # 2. download with retries (https first, http as fallback on connection problems)
    last_err = ""
    for attempt in range(1, retries + 1):
        res.attempts = attempt
        base = BASE_URLS[0] if attempt % 2 == 1 else BASE_URLS[-1]
        url = f"{base}/{fname}"
        res.url = url
        part = dest.with_suffix(dest.suffix + ".part")
        try:
            with session.get(url, stream=True, timeout=(15, timeout)) as r:
                res.http_status = r.status_code
                if r.status_code == 404:
                    # GDELT occasionally skips a slot; confirm once more before declaring missing
                    if attempt >= 2:
                        res.status, res.error = "missing_404", "HTTP 404 (slot not published)"
                        return res
                    last_err = "HTTP 404"
                    time.sleep(backoff)
                    continue
                if r.status_code != 200:
                    last_err = f"HTTP {r.status_code}"
                    time.sleep(backoff * attempt)
                    continue
                expected = int(r.headers.get("Content-Length", 0))
                with part.open("wb") as f:
                    for chunk in r.iter_content(1 << 16):
                        f.write(chunk)
            size = part.stat().st_size
            if expected and size != expected:
                last_err = f"truncated download {size}/{expected} bytes"
                part.unlink(missing_ok=True)
                time.sleep(backoff * attempt)
                continue
            ok, why = validate_zip(part)
            if not ok:
                last_err = f"validation failed: {why}"
                part.unlink(missing_ok=True)
                time.sleep(backoff * attempt)
                continue
            if verify_md5 and name in master:
                good = md5_file(part) == master[name][1]
                res.md5_ok = good
                if not good:
                    last_err = "MD5 mismatch vs master list"
                    part.unlink(missing_ok=True)
                    time.sleep(backoff * attempt)
                    continue
            part.replace(dest)
            res.status, res.bytes, res.sha256, res.error = "ok", dest.stat().st_size, sha256_file(dest), ""
            return res
        except requests.RequestException as e:
            last_err = f"{type(e).__name__}: {e}"
            part.unlink(missing_ok=True)
            time.sleep(backoff * attempt)
    res.error = last_err
    return res


def cmd_download(args: argparse.Namespace) -> int:
    start, end = parse_date(args.start), parse_date(args.end)
    if end < start:
        LOG.error("--end is before --start")
        return 2
    streams = ["english", "translation"] if args.stream == "both" else [args.stream]
    raw_dir = Path(args.raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    all_results: list[Result] = []
    for stream in streams:
        master: dict[str, tuple[int, str]] = {}
        if args.verify_md5:
            LOG.info("Streaming %s for MD5 values (integrity only)...", MASTER[stream])
            master = load_master_md5(stream, start, end, raw_dir, session)
            LOG.info("  %d master-list entries found inside the period", len(master))
        slots = list(iter_slots(start, end))
        LOG.info("[%s] %d expected 15-min slots (%s .. %s)", stream, len(slots),
                 start.date(), end.date())
        done = 0
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(download_one, session, t, stream, raw_dir, args.retries,
                              args.backoff, args.timeout, master, args.verify_md5): t for t in slots}
            for fut in as_completed(futs):
                all_results.append(fut.result())
                done += 1
                if done % 100 == 0 or done == len(slots):
                    LOG.info("  %d/%d slots processed", done, len(slots))

    all_results.sort(key=lambda r: (r.stream, r.slot))
    manifest = raw_dir / "manifest.csv"
    with manifest.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(asdict(all_results[0]).keys()))
        w.writeheader()
        w.writerows(asdict(r) for r in all_results)

    # Missing-date / missing-slot report
    summary: dict = {"period": [args.start, args.end], "streams": {}}
    for stream in streams:
        rs = [r for r in all_results if r.stream == stream]
        by_status: dict[str, int] = {}
        for r in rs:
            by_status[r.status] = by_status.get(r.status, 0) + 1
        have = {r.slot for r in rs if r.status in ("ok", "cached")}
        days = sorted({r.slot[:8] for r in rs})
        missing_days = [d for d in days if not any(s.startswith(d) for s in have)]
        partial_days = {d: sum(1 for r in rs if r.slot.startswith(d) and r.status not in ("ok", "cached"))
                        for d in days}
        partial_days = {d: n for d, n in partial_days.items() if 0 < n < 96}
        summary["streams"][stream] = {
            "expected_slots": len(rs), "status_counts": by_status,
            "days_with_no_data": missing_days, "days_with_missing_slots": partial_days,
            "failed_slots": [r.slot for r in rs if r.status == "failed"][:50],
        }
    (raw_dir / "download_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    failed = sum(1 for r in all_results if r.status == "failed")
    if failed:
        LOG.warning("%d slots FAILED (network/validation). Re-run the same command to retry only those.", failed)
    return 0 if failed == 0 else 1


# --------------------------------------------------------------------------- archive check
def head_probe(session: requests.Session, fname: str) -> dict:
    out = {"file": fname}
    for base in BASE_URLS:
        url = f"{base}/{fname}"
        try:
            r = session.head(url, timeout=20, allow_redirects=True)
            out.update(url=url, http_status=r.status_code,
                       content_length=r.headers.get("Content-Length"),
                       last_modified=r.headers.get("Last-Modified"))
            return out
        except requests.RequestException as e:
            out.update(url=url, error=f"{type(e).__name__}: {e}")
    return out


def cmd_check_archive(args: argparse.Namespace) -> int:
    start, end = parse_date(args.start), parse_date(args.end)
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    report: dict = {"checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "target_period": [args.start, args.end]}

    # 1. lastupdate.txt - the live pointer
    for base in BASE_URLS:
        try:
            r = session.get(f"{base}/{LASTUPDATE['english']}", timeout=20)
            report["lastupdate"] = {"url": r.url, "http_status": r.status_code, "body": r.text.strip()}
            break
        except requests.RequestException as e:
            report["lastupdate"] = {"error": f"{type(e).__name__}: {e}"}

    # 2. master list freshness (streams the whole file once; it is large)
    if not args.skip_masterlist:
        latest, count_in_period, total = "", 0, 0
        prefixes = tuple(f"{(start + timedelta(days=i)):%Y%m%d}" for i in range((end - start).days + 1))
        try:
            with session.get(f"{BASE_URLS[0]}/{MASTER['english']}", stream=True, timeout=(15, 180)) as r:
                report["masterlist_http_status"] = r.status_code
                if r.status_code == 200:
                    for raw in r.iter_lines(decode_unicode=True):
                        if not raw.endswith(SUFFIX["english"]):
                            continue
                        total += 1
                        ts = raw.rsplit("/", 1)[-1].split(".")[0]
                        latest = max(latest, ts)
                        if ts.startswith(prefixes):
                            count_in_period += 1
            report["masterlist"] = {"gkg_entries": total, "latest_slot": latest,
                                    "entries_inside_target_period": count_in_period,
                                    "expected_inside_period": 96 * len(prefixes),
                                    "stale_for_target_period": count_in_period == 0 or latest < f"{end:%Y%m%d}234500"}
        except requests.RequestException as e:
            report["masterlist"] = {"error": f"{type(e).__name__}: {e}"}

    # 3. direct probes - the reliable method
    probes = [slot_name(start), slot_name(start + timedelta(hours=12)),
              slot_name(end + timedelta(hours=23, minutes=45))]
    report["direct_probes"] = [head_probe(session, f"{p}{SUFFIX['english']}") for p in probes]
    ok = [p for p in report["direct_probes"] if p.get("http_status") == 200]
    report["conclusion"] = (
        "Direct file URLs for the target period are reachable - use `download` (it generates URLs, "
        "ignoring the master list)." if ok else
        "No direct probe returned HTTP 200 - inspect the errors above (network block, or data not published).")
    Path(args.out).write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 0


# --------------------------------------------------------------------------- CLI
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-v", "--verbose", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--start", default="2026-10-01", help="first UTC date, YYYY-MM-DD (default 2026-10-01)")
        p.add_argument("--end", default="2026-10-31", help="last UTC date, inclusive (default 2026-10-31)")

    c = sub.add_parser("check-archive", help="verify live endpoints and period availability")
    common(c)
    c.add_argument("--out", default="archive_check.json")
    c.add_argument("--skip-masterlist", action="store_true", help="skip streaming the large master list")
    c.set_defaults(func=cmd_check_archive)

    d = sub.add_parser("download", help="download + validate GKG files")
    common(d)
    d.add_argument("--raw-dir", default="data/raw")
    d.add_argument("--stream", choices=["english", "translation", "both"], default="english",
                   help="english = *.gkg.csv.zip; translation = *.translation.gkg.csv.zip")
    d.add_argument("--workers", type=int, default=4, help="parallel downloads (be polite; default 4)")
    d.add_argument("--retries", type=int, default=5)
    d.add_argument("--backoff", type=float, default=2.0, help="base seconds for linear backoff")
    d.add_argument("--timeout", type=int, default=120, help="read timeout seconds")
    d.add_argument("--verify-md5", action="store_true",
                   help="also stream the master list and check MD5 where an entry exists")
    d.set_defaults(func=cmd_download)

    args = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
