#!/usr/bin/env python3
"""
sec_edgar_collector.py - SEC EDGAR Form 8-K collector for IntelliHedge V2 (Stage 2).

Why several endpoints (no single SEC API has everything):
  1. Daily index   /Archives/edgar/daily-index/YYYY/QTRn/master.YYYYMMDD.idx
                   -> authoritative list of every filing per filing date (completeness backbone).
  2. Submissions   data.sec.gov/submissions/CIK##########.json
                   -> per-company metadata: acceptanceDateTime, reportDate, items, primaryDocument,
                      tickers, exchanges, SIC.  (Does NOT list all filers' filings for a day.)
  3. Header        /Archives/edgar/data/<cik>/<acc-nodash>/<acc>.hdr.sgml
                   -> per-filing SGML header: <ACCEPTANCE-DATETIME>, item descriptions, filers.
  4. Index page    /Archives/edgar/data/<cik>/<acc>-index.html
                   -> document list incl. exhibits with their types.
  5. Primary doc   /Archives/edgar/data/<cik>/<acc-nodash>/<primaryDocument>
Company Facts / Frames (XBRL) APIs are NOT used: they carry financial-statement facts, not 8-K text.

SEC fair access (https://www.sec.gov/os/accessing-edgar-data): max 10 requests/second in total, and
a declared User-Agent with a contact e-mail. This script enforces a global rate limit (default 6/s,
hard cap 10/s), refuses to start without a User-Agent containing an e-mail address (NO default e-mail
is invented - you supply it), pauses ALL threads when it receives HTTP 403/429, and aborts after
repeated blocks instead of hammering the server.

Commands
  check-endpoints   probe every endpoint once and report status/format (writes endpoint_check.json)
  collect           run the collection (index -> submissions -> headers -> index pages -> documents)

Example
  set SEC_EDGAR_USER_AGENT=IntelliHedge-Research your.name@yourdomain.com      (Windows cmd)
  python sec_edgar_collector.py check-endpoints --start 2026-10-01
  python sec_edgar_collector.py collect --start 2026-10-01 --end 2026-10-31
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import requests

LOG = logging.getLogger("sec_edgar_collector")

WWW_BASE = "https://www.sec.gov"
DATA_BASE = "https://data.sec.gov"
HARD_MAX_RATE = 10.0   # SEC published maximum (requests/second, all machines combined)
EMAIL_RE = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")

# Days on which EDGAR is assumed closed (federal holidays 2026). ASSUMPTION used only to label an
# absent daily index as "expected" vs "unexpected missing"; a 404 is always recorded as-is.
DEFAULT_CLOSED = ("2026-01-01,2026-01-19,2026-02-16,2026-05-25,2026-06-19,2026-07-03,"
                  "2026-09-07,2026-10-12,2026-11-11,2026-11-26,2026-12-25")


# --------------------------------------------------------------------------- small helpers
def parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def quarter(d: date) -> int:
    return (d.month - 1) // 3 + 1


def acc_nodash(acc: str) -> str:
    return acc.replace("-", "")


def safe_name(name: str) -> str:
    """Make a filesystem-safe (Windows-safe) file name from an SEC document name."""
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name.split("/")[-1]) or "document"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def cik_int(cik: str) -> int:
    return int(str(cik).strip())


# --------------------------------------------------------------------------- rate limiting / HTTP
class BlockedError(RuntimeError):
    """Raised after repeated 403/429 responses - the run stops instead of hammering SEC."""


class Gate:
    """Global request gate: minimum spacing between requests + an all-threads pause."""

    def __init__(self, rate: float):
        self.interval = 1.0 / rate
        self._lock = threading.Lock()
        self._next = 0.0
        self._pause_until = 0.0
        self.request_times: list[float] = []   # kept for tests / diagnostics

    def wait(self) -> None:
        while True:
            with self._lock:
                now = time.monotonic()
                ready = max(self._next, self._pause_until)
                if now >= ready:
                    self._next = now + self.interval
                    self.request_times.append(now)
                    return
                delay = ready - now
            time.sleep(min(delay, 0.5))

    def pause(self, seconds: float) -> None:
        with self._lock:
            self._pause_until = max(self._pause_until, time.monotonic() + seconds)


@dataclass
class Fetch:
    status: Optional[int]
    content: bytes = b""
    error: str = ""
    attempts: int = 0
    content_encoding: str = ""
    content_length: Optional[int] = None


class SecClient:
    def __init__(self, user_agent: str, rate: float, retries: int, backoff: float,
                 pause_on_block: float, max_blocks: int, timeout: int):
        self.session = requests.Session()
        # requests adds Accept-Encoding: gzip, deflate by default; Host is set from the URL.
        self.session.headers.update({"User-Agent": user_agent})
        self.gate = Gate(rate)
        self.retries, self.backoff = retries, backoff
        self.pause_on_block, self.max_blocks, self.timeout = pause_on_block, max_blocks, timeout
        self._blocks = 0
        self._blk_lock = threading.Lock()
        self.total_requests = 0

    def get(self, url: str) -> Fetch:
        res = Fetch(status=None)
        for attempt in range(1, self.retries + 1):
            res.attempts = attempt
            self.gate.wait()
            self.total_requests += 1
            try:
                r = self.session.get(url, timeout=self.timeout)
            except requests.RequestException as e:
                res.error = f"{type(e).__name__}: {e}"
                time.sleep(self.backoff * attempt)
                continue
            res.status = r.status_code
            if r.status_code == 200:
                with self._blk_lock:
                    self._blocks = 0
                res.content = r.content
                res.content_encoding = r.headers.get("Content-Encoding", "")
                cl = r.headers.get("Content-Length")
                res.content_length = int(cl) if cl and cl.isdigit() else None
                res.error = ""
                return res
            if r.status_code in (403, 429):
                with self._blk_lock:
                    self._blocks += 1
                    n = self._blocks
                ra = r.headers.get("Retry-After")
                pause = max(self.pause_on_block * (2 ** min(n - 1, 4)),
                            float(ra) if ra and ra.replace(".", "", 1).isdigit() else 0)
                LOG.warning("HTTP %s from SEC (block #%d) - pausing ALL requests %.0fs: %s",
                            r.status_code, n, pause, url)
                self.gate.pause(pause)
                res.error = f"HTTP {r.status_code}"
                if n >= self.max_blocks:
                    raise BlockedError(f"{n} consecutive 403/429 responses; stopping. "
                                       "Check the User-Agent and lower --rate before retrying.")
                continue
            if r.status_code == 404:
                res.error = "HTTP 404"
                return res
            if r.status_code >= 500:
                res.error = f"HTTP {r.status_code}"
                time.sleep(self.backoff * attempt)
                continue
            res.error = f"HTTP {r.status_code}"
            return res
        return res


# --------------------------------------------------------------------------- manifest
MANIFEST_FIELDS = ["run_id", "resource", "key", "url", "local_path", "status", "http_status",
                   "bytes", "sha256", "attempts", "error", "collected_at_utc"]


class Manifest:
    """Append-only CSV (thread-safe). status: success | skipped_cached | not_found | failed | no_reference."""

    def __init__(self, path: Path, run_id: str):
        self.path, self.run_id = path, run_id
        path.parent.mkdir(parents=True, exist_ok=True)
        new = not path.exists()
        self._f = path.open("a", newline="", encoding="utf-8")
        self._w = csv.DictWriter(self._f, fieldnames=MANIFEST_FIELDS)
        if new:
            self._w.writeheader()
        self._lock = threading.Lock()
        self.rows: list[dict] = []

    def add(self, resource, key, url, local_path, status, http_status=None, nbytes=0, sha="",
            attempts=0, error=""):
        row = {"run_id": self.run_id, "resource": resource, "key": key, "url": url,
               "local_path": str(local_path) if local_path else "", "status": status,
               "http_status": http_status if http_status is not None else "", "bytes": nbytes,
               "sha256": sha, "attempts": attempts, "error": error, "collected_at_utc": utc_now()}
        with self._lock:
            self._w.writerow(row)
            self._f.flush()
            self.rows.append(row)

    def close(self):
        self._f.close()


# --------------------------------------------------------------------------- generic fetch+store
def fetch_and_store(client: SecClient, mf: Manifest, resource: str, key: str, url: str, dest: Path,
                    validator=None) -> Optional[bytes]:
    """Download `url` to `dest` unless a valid copy exists. Returns the content or None."""
    if dest.exists() and dest.stat().st_size > 0:
        data = dest.read_bytes()
        ok, why = (True, "") if validator is None else validator(data)
        if ok:
            mf.add(resource, key, url, dest, "skipped_cached", nbytes=len(data), sha=sha256_bytes(data))
            return data
        LOG.warning("cached %s invalid (%s) - re-downloading", dest.name, why)
    r = client.get(url)
    if r.status == 404:
        mf.add(resource, key, url, None, "not_found", 404, attempts=r.attempts, error=r.error)
        return None
    if r.status != 200:
        mf.add(resource, key, url, None, "failed", r.status, attempts=r.attempts, error=r.error or "no response")
        return None
    data = r.content
    problem = ""
    if len(data) == 0:
        problem = "empty body"
    elif r.content_length is not None and not r.content_encoding and len(data) != r.content_length:
        problem = f"truncated {len(data)}/{r.content_length} bytes"
    elif validator is not None:
        ok, why = validator(data)
        if not ok:
            problem = why
    if problem:
        mf.add(resource, key, url, None, "failed", 200, nbytes=len(data), attempts=r.attempts, error=problem)
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    tmp.write_bytes(data)
    os.replace(tmp, dest)
    mf.add(resource, key, url, dest, "success", 200, len(data), sha256_bytes(data), r.attempts)
    return data


def v_json(data: bytes):
    try:
        obj = json.loads(data.decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        return False, f"invalid JSON: {e}"
    return (True, "") if isinstance(obj, dict) else (False, "JSON is not an object")


def v_html(data: bytes):
    return (True, "") if b"<html" in data[:4096].lower() or b"<!doctype" in data[:4096].lower() \
        else (False, "response does not look like HTML")


def v_header(data: bytes):
    t = data[:8192].upper()
    return (True, "") if b"ACCESSION NUMBER" in t or b"<ACCEPTANCE-DATETIME>" in t \
        else (False, "response does not look like an SGML header")


# --------------------------------------------------------------------------- index parsing
def parse_master_idx(text: str) -> list[dict]:
    """Parse master.YYYYMMDD.idx: pipe-delimited CIK|Company Name|Form Type|Date Filed|Filename."""
    rows, in_data = [], False
    for line in text.splitlines():
        if not in_data:
            if line.startswith("CIK|Company Name"):
                in_data = True
            continue
        if not line.strip() or set(line.strip()) == {"-"}:
            continue
        parts = line.split("|")
        if len(parts) != 5:
            continue
        cik, name, form, filed, fname = (p.strip() for p in parts)
        rows.append({"cik": cik, "company_name": name, "form_type": form, "date_filed_raw": filed,
                     "filename": fname,
                     "accession": Path(fname).stem if fname.endswith(".txt") else ""})
    return rows


def norm_date(s: str) -> str:
    s = s.strip().replace("-", "")
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}" if re.fullmatch(r"\d{8}", s) else s


# --------------------------------------------------------------------------- collection
def preflight_ua(ua: Optional[str]) -> str:
    if not ua or not EMAIL_RE.search(ua):
        raise SystemExit(
            "ERROR: SEC requires a descriptive User-Agent that includes a contact e-mail.\n"
            "Provide --user-agent \"AppName contact@yourdomain.com\" or set SEC_EDGAR_USER_AGENT.\n"
            "No default is supplied on purpose (a contact address must be real and yours).")
    return ua.strip()


def make_client(a: argparse.Namespace) -> SecClient:
    rate = min(a.rate, HARD_MAX_RATE)
    if a.rate > HARD_MAX_RATE:
        LOG.warning("--rate %.1f exceeds the SEC maximum; clamped to %.1f", a.rate, HARD_MAX_RATE)
    return SecClient(preflight_ua(a.user_agent or os.environ.get("SEC_EDGAR_USER_AGENT")), rate,
                     a.retries, a.backoff, a.pause_on_block, a.max_blocks, a.timeout)


def run_collect(a: argparse.Namespace) -> int:
    start, end = parse_date(a.start), parse_date(a.end)
    if end < start:
        LOG.error("--end before --start")
        return 2
    forms = {f.strip().upper() for f in a.forms.split(",") if f.strip()}
    closed = {parse_date(x) for x in a.closed_dates.split(",") if x.strip()}
    client = make_client(a)
    root = Path(a.out)
    meta, filings_dir, man_dir = root / "raw/metadata", root / "raw/filings", root / "raw/manifests"
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    mf = Manifest(man_dir / "manifest.csv", run_id)
    www, data_base = a.www_base.rstrip("/"), a.data_base.rstrip("/")
    summary: dict = {"run_id": run_id, "period": [a.start, a.end], "forms": sorted(forms),
                     "margin_days_after_end": a.margin_days, "aborted": None}

    try:
        # ---------------- phase 1: daily indexes (completeness backbone)
        days, d = [], start
        while d <= end + timedelta(days=a.margin_days):
            days.append(d)
            d += timedelta(days=1)
        selected: dict[str, dict] = {}        # accession -> row
        index_form_counts: dict[str, dict] = {}
        idx_status: dict[str, str] = {}

        quarters_seen = set()
        available_by_quarter = {}
        summary["directory_listing_status"] = {}

        for day in days:
            q = quarter(day)
            quarter_key = (day.year, q)
            quarter_label = f"{day.year}Q{q}"

            if quarter_key not in quarters_seen:
                quarters_seen.add(quarter_key)

                listing_url = (
                    f"{www}/Archives/edgar/daily-index/"
                    f"{day.year}/QTR{q}/index.json"
                )
                listing_dest = (
                    meta / f"daily-index/{day.year}/QTR{q}/index.json"
                )

                listing_data = fetch_and_store(
                    client, mf, "daily_index_listing",
                    quarter_label, listing_url, listing_dest, v_json
                )

                if listing_data is None:
                    available_by_quarter[quarter_key] = None
                    summary["directory_listing_status"][quarter_label] = "unavailable"
                else:
                    try:
                        listing_obj = json.loads(
                            listing_data.decode("utf-8")
                        )
                        directory = listing_obj.get("directory")

                        if not isinstance(directory, dict) or not isinstance(
                            directory.get("item"), list
                        ):
                            raise ValueError("Missing directory.item in SEC listing")

                        listing_items = directory["item"]

                        available_names = {
                            item["name"]
                            for item in listing_items
                            if isinstance(item, dict)
                            and item.get("type") == "file"
                            and re.fullmatch(
                                r"master\.\d{8}\.idx",
                                str(item.get("name", ""))
                            )
                        }

                        available_by_quarter[quarter_key] = available_names
                        summary["directory_listing_status"][quarter_label] = "success"

                    except (ValueError, TypeError, AttributeError,
                            json.JSONDecodeError) as exc:
                        available_by_quarter[quarter_key] = None
                        summary["directory_listing_status"][quarter_label] = "invalid"
                        LOG.error("Invalid SEC directory listing: %s", exc)

            ds = day.strftime("%Y%m%d")
            index_name = f"master.{ds}.idx"

            if available_by_quarter[quarter_key] is None:
                idx_status[ds] = "listing_unavailable"
                continue

            if index_name not in available_by_quarter[quarter_key]:
                idx_status[ds] = "not_listed"
                LOG.info("Skipping %s: index absent from official SEC listing", ds)
                continue

            url = (
                f"{www}/Archives/edgar/daily-index/"
                f"{day.year}/QTR{q}/{index_name}"
            )
            dest = meta / f"daily-index/{day.year}/QTR{q}/{index_name}"

            before = len(mf.rows)

            data = fetch_and_store(
                client, mf, "daily_index", ds, url, dest,
                lambda b: (True, "") if
                b"CIK|Company Name" in b[:4096] or b"CIK|" in b[:4096]
                else (False, "unexpected index content")
            )

            idx_status[ds] = (
                mf.rows[-1]["status"]
                if len(mf.rows) > before else "unknown"
            )

            if data is None:
                continue
            rows = parse_master_idx(data.decode("utf-8", errors="replace"))
            counts: dict[str, int] = {}
            for r in rows:
                counts[r["form_type"]] = counts.get(r["form_type"], 0) + 1
                if r["form_type"].upper() in forms:
                    filed = norm_date(r["date_filed_raw"])
                    acc = r["accession"]
                    if not acc:
                        continue
                    row = {**r, "idx_file_date": day.isoformat(), "date_filed": filed,
                           "in_filing_date_window": start.isoformat() <= filed <= end.isoformat()}
                    if acc in selected:
                        selected[acc].setdefault("co_filer_ciks", []).append(r["cik"])
                        selected[acc]["index_rows"] += 1
                    else:
                        row["co_filer_ciks"] = []
                        row["index_rows"] = 1
                        selected[acc] = row
            index_form_counts[ds] = counts
        man_dir.mkdir(parents=True, exist_ok=True)
        (man_dir / "index_form_counts.json").write_text(json.dumps(index_form_counts, indent=1))

        in_window = {k: v for k, v in selected.items() if v["in_filing_date_window"]}
        margin = {k: v for k, v in selected.items() if not v["in_filing_date_window"]}
        with (man_dir / "filings_selected.csv").open("w", newline="", encoding="utf-8") as f:
            cols = ["accession", "cik", "company_name", "form_type", "date_filed_raw", "date_filed", "filename",
                    "idx_file_date", "in_filing_date_window", "index_rows", "co_filer_ciks"]
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for v in selected.values():
                w.writerow({**v, "co_filer_ciks": ";".join(v.get("co_filer_ciks", []))})
        expected_days = [x for x in days if x <= end and x.weekday() < 5 and x not in closed]
        summary["index"] = {
            "filing_dates_in_window_expected_business_days": len(expected_days),
            "daily_index_status": idx_status,
            "expected_business_days_without_index": [x.isoformat() for x in expected_days
                                                     if idx_status.get(x.strftime("%Y%m%d")) in ("not_found", "failed", "not_listed", "listing_unavailable")],
            "index_present_on_weekend_or_holiday": [x.isoformat() for x in days if x <= end and
                                                    (x.weekday() >= 5 or x in closed) and
                                                    idx_status.get(x.strftime("%Y%m%d")) in ("success", "skipped_cached")],
            "unique_accessions_in_window": len(in_window),
            "unique_accessions_margin_after_end": len(margin),
        }
        LOG.info("index: %d unique %s accessions in window, %d in margin", len(in_window), sorted(forms), len(margin))
        if a.max_filings:
            keep = list(in_window)[: a.max_filings]
            in_window = {k: in_window[k] for k in keep}

        # ---------------- phase 2: submissions per CIK (in-window filings only)
        sub_records: dict[str, dict] = {}     # accession -> {primaryDocument,...}
        ciks = sorted({cik_int(v["cik"]) for v in in_window.values()})
        summary["unique_ciks_in_window"] = len(ciks)

        def do_sub(cik: int):
            name = f"CIK{cik:010d}.json"
            data = fetch_and_store(client, mf, "submissions", f"{cik:010d}", f"{data_base}/submissions/{name}",
                                   meta / f"submissions/{name}", v_json)
            return cik, data

        with ThreadPoolExecutor(max_workers=a.workers) as ex:
            futs = [ex.submit(do_sub, c) for c in ciks]
            done = 0
            for fu in as_completed(futs):
                cik, data = fu.result()
                done += 1
                if done % 200 == 0:
                    LOG.info("submissions %d/%d", done, len(ciks))
                if data is None:
                    continue
                obj = json.loads(data.decode("utf-8"))
                _index_submission(obj, sub_records)
                # older pages: only fetch those whose range could contain missing accessions
                missing = [k for k, v in in_window.items() if cik_int(v["cik"]) == cik and k not in sub_records]
                for pg in (obj.get("filings", {}) or {}).get("files", []) or []:
                    if not missing:
                        break
                    nm = pg.get("name")
                    if not nm:
                        continue
                    dts = [in_window[k]["date_filed"] for k in missing]
                    if pg.get("filingFrom") and pg.get("filingTo") and not any(
                            pg["filingFrom"] <= x <= pg["filingTo"] for x in dts):
                        continue
                    pdata = fetch_and_store(client, mf, "submissions_page", nm, f"{data_base}/submissions/{nm}",
                                            meta / f"submissions/{nm}", v_json)
                    if pdata:
                        _index_submission(json.loads(pdata.decode("utf-8")), sub_records)
                        missing = [k for k in missing if k not in sub_records]
        summary["submissions_cross_check"] = {
            "accessions_in_index": len(in_window),
            "found_in_submissions": sum(1 for k in in_window if k in sub_records),
            "missing_from_submissions": sorted(k for k in in_window if k not in sub_records)[:200],
        }

        # ---------------- phase 3: SGML headers (in-window + margin; acceptance datetime source)
        todo = list(in_window.items()) + list(margin.items())

        def do_hdr(item):
            acc, v = item
            url = f"{www}/Archives/edgar/data/{cik_int(v['cik'])}/{acc_nodash(acc)}/{acc}.hdr.sgml"
            return fetch_and_store(client, mf, "header", acc, url, meta / f"headers/{acc}.hdr.sgml", v_header)

        _run_pool(a.workers, do_hdr, todo, "headers")

        # ---------------- phase 4: index pages (in-window only)
        def do_page(item):
            acc, v = item
            url = f"{www}/Archives/edgar/data/{cik_int(v['cik'])}/{acc}-index.html"
            return fetch_and_store(client, mf, "index_page", acc, url, meta / f"index_pages/{acc}-index.html", v_html)

        pages = dict(zip([k for k, _ in in_window.items()],
                         _run_pool(a.workers, do_page, list(in_window.items()), "index pages")))

        # ---------------- phase 5: primary documents (in-window only)
        if not a.skip_documents:
            def do_doc(item):
                acc, v = item
                prim = (sub_records.get(acc) or {}).get("primaryDocument") or ""
                if not prim and pages.get(acc):
                    prim = _primary_from_index_page(pages[acc].decode("utf-8", errors="replace"), v["form_type"])
                if not prim:
                    mf.add("primary_doc", acc, "", None, "no_reference",
                           error="no primaryDocument in submissions JSON or index page")
                    return None
                url = f"{www}/Archives/edgar/data/{cik_int(v['cik'])}/{acc_nodash(acc)}/{prim}"
                dest = filings_dir / str(cik_int(v["cik"])) / acc_nodash(acc) / safe_name(prim)
                return fetch_and_store(client, mf, "primary_doc", acc, url, dest, None)

            _run_pool(a.workers, do_doc, list(in_window.items()), "documents")
    except BlockedError as e:
        summary["aborted"] = f"blocked: {e}"
        LOG.error("%s", e)

    mf.close()
    # ---- summary from this run's manifest rows
    by: dict[str, dict[str, int]] = {}
    for r in mf.rows:
        by.setdefault(r["resource"], {}).setdefault(r["status"], 0)
        by[r["resource"]][r["status"]] += 1
    summary["manifest_status_by_resource"] = by
    summary["http_requests_sent"] = client.total_requests
    (man_dir / f"collection_summary_{run_id}.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    failed = sum(v.get("failed", 0) for v in by.values())
    if summary["aborted"]:
        return 3
    return 1 if failed else 0


def _run_pool(workers: int, fn, items: list, label: str) -> list:
    out = [None] * len(items)
    if not items:
        return out
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fn, it): i for i, it in enumerate(items)}
        done = 0
        for fu in as_completed(futs):
            out[futs[fu]] = fu.result()
            done += 1
            if done % 200 == 0 or done == len(items):
                LOG.info("%s %d/%d", label, done, len(items))
    return out


def _index_submission(obj: dict, sink: dict) -> None:
    """Flatten the parallel arrays of filings.recent (or an older page) into {accession: {...}}."""
    f = obj.get("filings", obj)
    rec = f.get("recent", f) if isinstance(f, dict) else {}
    accs = rec.get("accessionNumber") or []
    for i, acc in enumerate(accs):
        sink[acc] = {k: (rec[k][i] if k in rec and i < len(rec[k]) else None)
                     for k in ("primaryDocument", "form", "filingDate", "acceptanceDateTime")}


def _primary_from_index_page(html: str, form: str) -> str:
    """Fallback: first document-table link whose Type cell equals the form type."""
    for m in re.finditer(r"<tr[^>]*>(.*?)</tr>", html, flags=re.S | re.I):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", m.group(1), flags=re.S | re.I)
        if len(cells) >= 4 and re.sub(r"<[^>]+>", "", cells[3]).strip().upper() == form.upper():
            link = re.search(r'href="([^"]+)"', cells[2])
            if link:
                return link.group(1).split("/")[-1].split("?")[0]
    return ""


# --------------------------------------------------------------------------- endpoint check
def run_check(a: argparse.Namespace) -> int:
    client = make_client(a)
    start = parse_date(a.start)
    q, www, dbase = quarter(start), a.www_base.rstrip("/"), a.data_base.rstrip("/")
    rep: dict = {"checked_at_utc": utc_now(), "probes": []}

    def probe(name, url, check=None, binary_ok=False):
        r = client.get(url)
        item = {"name": name, "url": url, "http_status": r.status, "bytes": len(r.content), "error": r.error}
        if r.status == 200 and check:
            try:
                item.update(check(r.content))
            except Exception as e:  # noqa: BLE001
                item["check_error"] = f"{type(e).__name__}: {e}"
        rep["probes"].append(item)
        return r

    probe("daily_index_directory_listing", f"{www}/Archives/edgar/daily-index/{start.year}/QTR{q}/index.json",
          lambda b: {"top_level_keys": list(json.loads(b).keys())})
    r = probe("daily_master_index_first_day", f"{www}/Archives/edgar/daily-index/{start.year}/QTR{q}/master.{start:%Y%m%d}.idx",
              lambda b: {"first_lines": b.decode("utf-8", "replace").splitlines()[:12]})
    sample = None
    if r.status == 200:
        rows = parse_master_idx(r.content.decode("utf-8", "replace"))
        eight = [x for x in rows if x["form_type"].upper() == "8-K"]
        rep["first_day_rows"] = len(rows)
        rep["first_day_8k_rows"] = len(eight)
        sample = eight[0] if eight else None
    cik = int(a.probe_cik)
    probe("submissions", f"{dbase}/submissions/CIK{cik:010d}.json", lambda b: _sub_check(json.loads(b)))
    if sample:
        acc, c = sample["accession"], cik_int(sample["cik"])
        probe("header", f"{www}/Archives/edgar/data/{c}/{acc_nodash(acc)}/{acc}.hdr.sgml",
              lambda b: {"head": b.decode("utf-8", "replace")[:600]})
        probe("index_page", f"{www}/Archives/edgar/data/{c}/{acc}-index.html",
              lambda b: {"has_document_table": b"Document Format Files" in b})
    rep["total_requests"] = client.total_requests
    Path(a.out_file).write_text(json.dumps(rep, indent=2))
    print(json.dumps(rep, indent=2))
    return 0 if all(p["http_status"] == 200 for p in rep["probes"]) else 1


def _sub_check(obj: dict) -> dict:
    rec = obj.get("filings", {}).get("recent", {})
    acc = (rec.get("acceptanceDateTime") or [None])[0]
    return {"top_level_keys": sorted(obj.keys()), "recent_columns": sorted(rec.keys()),
            "recent_rows": len(rec.get("accessionNumber", [])),
            "extra_pages": len(obj.get("filings", {}).get("files", []) or []),
            "acceptanceDateTime_example": acc}


# --------------------------------------------------------------------------- CLI
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-v", "--verbose", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--user-agent", help='"AppName contact@yourdomain.com" (or env SEC_EDGAR_USER_AGENT)')
        p.add_argument("--rate", type=float, default=6.0, help="max requests/second overall (default 6, cap 10)")
        p.add_argument("--retries", type=int, default=5)
        p.add_argument("--backoff", type=float, default=2.0)
        p.add_argument("--pause-on-block", type=float, default=60.0,
                       help="seconds ALL requests pause after HTTP 403/429 (doubles per consecutive block)")
        p.add_argument("--max-blocks", type=int, default=5, help="abort after this many consecutive 403/429")
        p.add_argument("--timeout", type=int, default=60)
        p.add_argument("--start", default="2026-10-01")
        p.add_argument("--www-base", default=WWW_BASE, help=argparse.SUPPRESS)
        p.add_argument("--data-base", default=DATA_BASE, help=argparse.SUPPRESS)

    c = sub.add_parser("check-endpoints", help="probe the endpoints once")
    common(c)
    c.add_argument("--probe-cik", default="320193", help="CIK used to probe the submissions API (default Apple)")
    c.add_argument("--out-file", default="endpoint_check.json")
    c.set_defaults(func=run_check)

    d = sub.add_parser("collect", help="collect filings")
    common(d)
    d.add_argument("--end", default="2026-10-31")
    d.add_argument("--forms", default="8-K,8-K/A", help="comma-separated form types to collect (exact match)")
    d.add_argument("--out", default="data", help="data root (raw/ lives below it)")
    d.add_argument("--workers", type=int, default=3, help="threads; the global rate limit still applies")
    d.add_argument("--margin-days", type=int, default=4,
                   help="extra days AFTER --end whose index+headers are fetched so filings accepted late on "
                        "the last day (filed next business day) can be identified; documents not downloaded")
    d.add_argument("--closed-dates", default=DEFAULT_CLOSED, help="assumed EDGAR closed dates (YYYY-MM-DD,...)")
    d.add_argument("--skip-documents", action="store_true", help="metadata only")
    d.add_argument("--max-filings", type=int, default=0, help="limit (testing only)")
    d.set_defaults(func=run_collect)

    a = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
