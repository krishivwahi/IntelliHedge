#!/usr/bin/env python3
"""
gdelt_quality_analysis.py - data-quality metrics for processed GDELT GKG data (IntelliHedge V2).

Reads data/processed/gkg_YYYYMMDD.parquet|csv.gz (written by gdelt_parser.py) and computes, on the
ACTUAL records only:

  Timestamp : format, precision, missing %, invalid %, timezone, record-time vs file-slot,
              page publication timestamp (V2EXTRASXML PAGE_PRECISEPUBTIMESTAMP) coverage and
              its delay relative to the record timestamp.
  Duplicates: exact duplicate rows, duplicate URLs (raw + normalised), duplicate headlines.
  Coverage  : totals, records/day, missing dates + missing 15-min slots, unique domains,
              language, theme / person / organisation / country distributions.

Outputs (in --out-dir): quality_metrics.json, quality_report.md and several CSV tables.
Nothing is estimated: if a quantity cannot be computed from the data it is reported as null.

Usage
  python gdelt_quality_analysis.py --processed-dir data/processed --raw-dir data/raw \
      --start 2026-10-01 --end 2026-10-31 --out-dir reports
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit, parse_qsl, urlencode

import numpy as np
import pandas as pd

LOG = logging.getLogger("gdelt_quality")
RE_14 = re.compile(r"^\d{14}$")
TRACKING = ("utm_", "fbclid", "gclid", "mc_", "ref", "cmpid", "ocid", "ito")


# --------------------------------------------------------------------------- helpers
def normalise_url(u):
    if not isinstance(u, str):
        return None
    try:
        s = urlsplit(u.strip())
    except ValueError:
        return u.strip().lower()
    host = (s.hostname or "").lower()
    host = host[4:] if host.startswith("www.") else host
    q = [(k, v) for k, v in parse_qsl(s.query, keep_blank_values=True)
         if not k.lower().startswith(TRACKING)]
    path = s.path.rstrip("/") or "/"
    return f"{host}{path}" + (f"?{urlencode(sorted(q))}" if q else "")


def h64(series: pd.Series) -> np.ndarray:
    return pd.util.hash_pandas_object(series, index=False).to_numpy(dtype="uint64")


def dup_stats(hashes: list[np.ndarray], label: str, denominator_note: str) -> dict:
    if not hashes:
        return {"label": label, "n": 0}
    allh = np.concatenate(hashes)
    n = int(len(allh))
    if n == 0:
        return {"label": label, "n": 0}
    uniq, counts = np.unique(allh, return_counts=True)
    redundant = n - len(uniq)
    involved = int(counts[counts > 1].sum())
    return {"label": label, "records_with_key": n, "unique_keys": int(len(uniq)),
            "redundant_records": int(redundant),
            "duplicate_pct_redundant": round(100 * redundant / n, 4),
            "records_in_duplicate_groups": involved,
            "duplicate_pct_in_groups": round(100 * involved / n, 4),
            "largest_group": int(counts.max()), "note": denominator_note}


def load_day(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path, dtype=str, low_memory=False)


def find_day_files(processed: Path, start: datetime, end: datetime) -> list[tuple[str, Path]]:
    out = []
    for i in range((end - start).days + 1):
        day = (start + timedelta(days=i)).strftime("%Y%m%d")
        for ext in ("parquet", "csv.gz"):
            p = processed / f"gkg_{day}.{ext}"
            if p.exists():
                out.append((day, p))
                break
    return out


# --------------------------------------------------------------------------- analysis
def analyse(args: argparse.Namespace) -> dict:
    start = datetime.strptime(args.start, "%Y-%m-%d")
    end = datetime.strptime(args.end, "%Y-%m-%d")
    processed = Path(args.processed_dir)
    files = find_day_files(processed, start, end)
    if not files:
        raise SystemExit(f"No processed files found in {processed} for {args.start}..{args.end}")

    total = 0
    per_day_files, per_day_ts = Counter(), Counter()
    slots_present: set[str] = set()
    # timestamp accumulators
    ts = Counter()
    deltas_hours: list[np.ndarray] = []
    slot_diff_sec: list[np.ndarray] = []
    pub_vs_slot: list[np.ndarray] = []
    # dup accumulators
    h_row_noid, h_row_withid, h_recid, h_url, h_nurl, h_head_dom, h_head, = [], [], [], [], [], [], []
    # coverage accumulators
    domains, langs, lang_basis, collections = Counter(), Counter(), Counter(), Counter()
    themes, persons, orgs, countries = Counter(), Counter(), Counter(), Counter()
    presence = Counter()
    tone_vals, wc_vals = [], []

    for day, path in files:
        df = load_day(path)
        n = len(df)
        total += n
        per_day_files[day] = n
        raw_cols = [c for c in df.columns if c.startswith("V") or c == "GKGRECORDID"]
        raw_noid = [c for c in raw_cols if c != "GKGRECORDID"]

        # ---------- timestamps: record time (V2.1DATE)
        s = df["V2.1DATE"]
        missing = s.isna() | (s.astype(str).str.strip() == "")
        fmt_ok = s.astype(str).str.match(RE_14) & ~missing
        parsed = pd.to_datetime(s.where(fmt_ok), format="%Y%m%d%H%M%S", errors="coerce", utc=True)
        valid = parsed.notna()
        ts["records"] += n
        ts["record_missing"] += int(missing.sum())
        ts["record_bad_format"] += int((~fmt_ok & ~missing).sum())
        ts["record_unparseable"] += int((fmt_ok & ~valid).sum())
        ts["record_valid"] += int(valid.sum())
        ts["record_seconds_nonzero"] += int((parsed.dt.second.fillna(0) != 0).sum())
        ts["record_minute_not_quarter"] += int((parsed.dt.minute.fillna(0) % 15 != 0).sum())
        for d, c in parsed.dropna().dt.strftime("%Y%m%d").value_counts().items():
            per_day_ts[d] += int(c)

        if "file_slot" in df.columns:
            slots_present |= set(df["file_slot"].dropna().unique())
            slot = pd.to_datetime(df["file_slot"], format="%Y%m%d%H%M%S", errors="coerce", utc=True)
            diff = (slot - parsed).dt.total_seconds().dropna().to_numpy()
            slot_diff_sec.append(diff)
            ts["record_eq_file_slot"] += int((diff == 0).sum())
            ts["record_vs_slot_compared"] += int(len(diff))

        # ---------- timestamps: page publication time (extras)
        if "page_pub_ts_raw" in df.columns:
            raw_pub = df["page_pub_ts_raw"]
            has_pub = raw_pub.notna()
            ts["pub_present"] += int(has_pub.sum())
            pub_fmt_ok = raw_pub.astype(str).str.match(RE_14) & has_pub
            ts["pub_bad_format"] += int((has_pub & ~pub_fmt_ok).sum())
            pub = pd.to_datetime(raw_pub.where(pub_fmt_ok), format="%Y%m%d%H%M%S", errors="coerce", utc=True)
            ts["pub_unparseable"] += int((pub_fmt_ok & pub.isna()).sum())
            ts["pub_valid"] += int(pub.notna().sum())
            ts["pub_seconds_nonzero"] += int((pub.dt.second.fillna(0) != 0).sum())
            both = pub.notna() & valid
            dh = ((parsed[both] - pub[both]).dt.total_seconds() / 3600).to_numpy()
            deltas_hours.append(dh)

        # ---------- duplicates
        if raw_noid:
            h_row_noid.append(h64(df[raw_noid].fillna("").astype(str).agg("\x1f".join, axis=1)))
        if raw_cols:
            h_row_withid.append(h64(df[raw_cols].fillna("").astype(str).agg("\x1f".join, axis=1)))
        h_recid.append(h64(df["GKGRECORDID"].dropna()))
        url = df["url"] if "url" in df.columns else df["V2DOCUMENTIDENTIFIER"]
        h_url.append(h64(url.dropna()))
        h_nurl.append(h64(url.dropna().map(normalise_url).dropna()))
        if "headline" in df.columns:
            hl = df["headline"].dropna().str.strip().str.lower()
            hl = hl[hl != ""]
            h_head.append(h64(hl))
            dom = df.loc[hl.index, "source_domain"].fillna("")
            h_head_dom.append(h64(dom + "|" + hl))

        # ---------- coverage
        if "source_domain" in df.columns:
            domains.update(df["source_domain"].dropna().tolist())
        if "language" in df.columns:
            langs.update(df["language"].fillna("unknown").tolist())
            lang_basis.update(df["language_basis"].fillna("unknown").tolist())
        if "source_collection" in df.columns:
            collections.update(df["source_collection"].fillna("unknown").tolist())
        for col, cnt in [("themes", themes), ("persons", persons), ("organizations", orgs),
                         ("location_countries", countries)]:
            if col in df.columns:
                cnt.update(df[col].dropna().str.split(";").explode().tolist())
                presence[f"has_{col}"] += int(df[col].notna().sum())
        for col in ("headline", "url", "page_pub_ts_raw", "tone", "V2.1TRANSLATIONINFO"):
            if col in df.columns:
                presence[f"has_{col}"] += int(df[col].notna().sum())
        if "tone" in df.columns:
            tone_vals.append(df["tone"].dropna().to_numpy(dtype="float64"))
            wc_vals.append(df["word_count"].dropna().to_numpy(dtype="float64"))
        LOG.info("%s: %d records analysed", day, n)

    # ------------------------------------------------------------------ assemble
    all_days = [(start + timedelta(days=i)).strftime("%Y%m%d") for i in range((end - start).days + 1)]
    missing_days = [d for d in all_days if per_day_files.get(d, 0) == 0]

    expected_slots = {(start + timedelta(minutes=15 * i)).strftime("%Y%m%d%H%M%S")
                      for i in range(((end - start).days + 1) * 96)}
    missing_slots = sorted(expected_slots - slots_present) if slots_present else None
    manifest_info = None
    mp = Path(args.raw_dir) / "manifest.csv"
    if mp.exists():
        m = pd.read_csv(mp, dtype=str)
        manifest_info = {"status_counts": m["status"].value_counts().to_dict(),
                         "slots_404": m.loc[m.status == "missing_404", "slot"].tolist()[:200],
                         "slots_failed": m.loc[m.status == "failed", "slot"].tolist()[:200]}

    def pct(x, d):
        return None if not d else round(100 * x / d, 4)

    metrics: dict = {
        "period": [args.start, args.end],
        "total_records": total,
        "timestamp_analysis": {
            "format": "V2.1DATE = 14-digit YYYYMMDDHHMMSS (documented as UTC); GKGRECORDID prefix uses the same stamp",
            "timezone": "UTC (per GDELT documentation; not verifiable from the data itself)",
            "record_timestamp": {
                "missing_pct": pct(ts["record_missing"], ts["records"]),
                "bad_format_pct": pct(ts["record_bad_format"], ts["records"]),
                "unparseable_pct": pct(ts["record_unparseable"], ts["records"]),
                "invalid_total_pct": pct(ts["record_bad_format"] + ts["record_unparseable"], ts["records"]),
                "pct_with_nonzero_seconds": pct(ts["record_seconds_nonzero"], ts["record_valid"]),
                "pct_minute_not_on_15min_boundary": pct(ts["record_minute_not_quarter"], ts["record_valid"]),
                "pct_equal_to_file_slot": pct(ts.get("record_eq_file_slot", 0), ts.get("record_vs_slot_compared", 0)),
                "interpretation": ("If ~100% equal the file slot and 0% have non-zero seconds/off-boundary minutes, "
                                   "V2.1DATE is a 15-minute batch stamp (collection/processing time), NOT an "
                                   "article publication time: precision = 15 minutes, not seconds."),
            },
            "page_publication_timestamp": {
                "source_field": "V2EXTRASXML <PAGE_PRECISEPUBTIMESTAMP> (extracted by GDELT from page metadata)",
                "present_pct": pct(ts.get("pub_present", 0), ts["records"]),
                "missing_pct": pct(ts["records"] - ts.get("pub_present", 0), ts["records"]),
                "bad_format_pct_of_present": pct(ts.get("pub_bad_format", 0), ts.get("pub_present", 0)),
                "unparseable_pct_of_present": pct(ts.get("pub_unparseable", 0), ts.get("pub_present", 0)),
                "pct_with_nonzero_seconds_of_valid": pct(ts.get("pub_seconds_nonzero", 0), ts.get("pub_valid", 0)),
            },
        },
        "duplicate_analysis": {
            "gkg_record_id_uniqueness": dup_stats(h_recid, "GKGRECORDID", "should be 0 duplicates"),
            "exact_duplicate_rows_incl_record_id": dup_stats(h_row_withid, "all original fields", "expected 0 because ids are unique"),
            "exact_duplicate_rows_excl_record_id": dup_stats(h_row_noid, "all original fields except GKGRECORDID", "same document re-emitted with new id"),
            "duplicate_urls_raw": dup_stats(h_url, "V2DOCUMENTIDENTIFIER (URL)", "records with a URL only"),
            "duplicate_urls_normalised": dup_stats(h_nurl, "URL minus scheme/www/tracking params/trailing slash", "records with a URL only"),
            "duplicate_headline_same_domain": dup_stats(h_head_dom, "domain + lower-cased PAGE_TITLE", "records with a title only; titles exist only if extras carry PAGE_TITLE"),
            "duplicate_headline_any_domain": dup_stats(h_head, "lower-cased PAGE_TITLE", "includes legitimate syndication / wire copy"),
        },
        "coverage_analysis": {
            "date_range_observed": [min(per_day_files), max(per_day_files)],
            "missing_dates": missing_days,
            "records_per_day": dict(sorted(per_day_files.items())),
            "records_per_day_by_record_timestamp": dict(sorted(per_day_ts.items())),
            "expected_15min_slots": len(expected_slots),
            "slots_with_data": len(slots_present),
            "missing_15min_slots_count": None if missing_slots is None else len(missing_slots),
            "missing_15min_slots_sample": None if missing_slots is None else missing_slots[:100],
            "download_manifest": manifest_info,
            "unique_source_domains": len(domains),
            "top10_domain_share_pct": pct(sum(c for _, c in domains.most_common(10)), sum(domains.values())),
            "source_collection_distribution": dict(collections.most_common()),
            "language_distribution": dict(langs.most_common(30)),
            "language_basis": dict(lang_basis.most_common()),
            "field_presence_pct": {k: pct(v, total) for k, v in sorted(presence.items())},
            "unique_themes": len(themes), "unique_persons": len(persons),
            "unique_organizations": len(orgs), "unique_countries": len(countries),
            "econ_theme_records_note": "see top_themes.csv; ECON_/WB_/TAX_FNCACT themes are the finance-relevant subset",
        },
    }
    if deltas_hours and sum(len(x) for x in deltas_hours):
        dh = np.concatenate(deltas_hours)
        metrics["timestamp_analysis"]["record_minus_publication_hours"] = {
            "n_pairs": int(len(dh)),
            "pct_negative_(publication_after_record_time)": pct(int((dh < 0).sum()), len(dh)),
            "percentiles": {f"p{q}": round(float(np.percentile(dh, q)), 3) for q in (1, 5, 25, 50, 75, 95, 99)},
            "pct_over_24h": pct(int((dh > 24).sum()), len(dh)),
            "pct_over_7d": pct(int((dh > 168).sum()), len(dh)),
        }
    if tone_vals and sum(len(x) for x in tone_vals):
        tv = np.concatenate(tone_vals)
        metrics["coverage_analysis"]["tone_summary"] = {
            "n": int(len(tv)), "mean": round(float(tv.mean()), 4), "std": round(float(tv.std()), 4),
            "min": round(float(tv.min()), 3), "max": round(float(tv.max()), 3)}

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "quality_metrics.json").write_text(json.dumps(metrics, indent=2, default=str))
    pd.DataFrame(sorted(per_day_files.items()), columns=["date", "records"]).to_csv(out / "records_per_day.csv", index=False)
    for name, cnt in [("top_themes", themes), ("top_persons", persons), ("top_organizations", orgs),
                      ("top_countries", countries), ("top_domains", domains), ("languages", langs)]:
        pd.DataFrame(cnt.most_common(args.top_n), columns=["value", "records"]).to_csv(out / f"{name}.csv", index=False)
    if missing_slots:
        pd.Series(missing_slots, name="missing_slot").to_csv(out / "missing_slots.csv", index=False)
    write_markdown(metrics, out / "quality_report.md")
    return metrics


def write_markdown(m: dict, path: Path) -> None:
    t, d, c = m["timestamp_analysis"], m["duplicate_analysis"], m["coverage_analysis"]
    rt, pp = t["record_timestamp"], t["page_publication_timestamp"]
    L = [f"# GDELT GKG data-quality report ({m['period'][0]} to {m['period'][1]})", "",
         "_Generated by gdelt_quality_analysis.py from the processed records. All numbers below are computed, not estimated._", "",
         f"**Total records analysed:** {m['total_records']:,}", "", "## 1. Timestamps", "",
         f"- Format: {t['format']}", f"- Timezone: {t['timezone']}", "",
         "| Metric (record timestamp V2.1DATE) | Value |", "|---|---|"]
    for k, v in rt.items():
        if k != "interpretation":
            L.append(f"| {k} | {v} |")
    L += ["", f"> {rt['interpretation']}", "", "| Metric (page publication timestamp from V2EXTRASXML) | Value |", "|---|---|"]
    for k, v in pp.items():
        L.append(f"| {k} | {v} |")
    if "record_minus_publication_hours" in t:
        r = t["record_minus_publication_hours"]
        L += ["", "**Record time minus page publication time (hours):**", "", f"```\n{json.dumps(r, indent=2)}\n```"]
    L += ["", "## 2. Duplicates", "",
          "| Test | Records with key | Redundant | Dup % (redundant) | Dup % (all in groups) | Largest group |", "|---|---|---|---|---|---|"]
    for k, v in d.items():
        if v.get("n", 1) == 0:
            continue
        L.append(f"| {v['label']} | {v.get('records_with_key', 0):,} | {v.get('redundant_records', 0):,} | "
                 f"{v.get('duplicate_pct_redundant')} | {v.get('duplicate_pct_in_groups')} | {v.get('largest_group')} |")
    L += ["", "## 3. Coverage", "",
          f"- Observed range: {c['date_range_observed'][0]} .. {c['date_range_observed'][1]}",
          f"- Missing dates: {c['missing_dates'] or 'none'}",
          f"- 15-minute slots with data: {c['slots_with_data']} / {c['expected_15min_slots']} "
          f"(missing: {c['missing_15min_slots_count']})",
          f"- Unique source domains: {c['unique_source_domains']:,} (top-10 share {c['top10_domain_share_pct']}%)",
          f"- Unique themes / persons / organisations / countries: {c['unique_themes']:,} / {c['unique_persons']:,} / "
          f"{c['unique_organizations']:,} / {c['unique_countries']:,}", "",
          "**Records per day**", "", "| Date | Records |", "|---|---|"]
    L += [f"| {k} | {v:,} |" for k, v in c["records_per_day"].items()]
    L += ["", "**Language distribution (top 30)**", "", f"```\n{json.dumps(c['language_distribution'], indent=2)}\n```",
          f"Language basis: {c['language_basis']}", "",
          "**Field presence (% of records)**", "", f"```\n{json.dumps(c['field_presence_pct'], indent=2)}\n```", "",
          "Top themes / persons / organisations / countries / domains: see the top_*.csv files in this folder."]
    path.write_text("\n".join(L) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--processed-dir", default="data/processed")
    ap.add_argument("--raw-dir", default="data/raw", help="only used to read manifest.csv")
    ap.add_argument("--out-dir", default="reports")
    ap.add_argument("--start", default="2026-10-01")
    ap.add_argument("--end", default="2026-10-31")
    ap.add_argument("--top-n", type=int, default=100)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    analyse(args)
    LOG.info("reports written to %s", args.out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
