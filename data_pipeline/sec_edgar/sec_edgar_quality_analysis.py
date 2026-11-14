#!/usr/bin/env python3
"""
sec_edgar_quality_analysis.py - data-quality metrics for the SEC EDGAR 8-K collection (IntelliHedge V2).

Computes ONLY from the collected records (processed tables + download manifest + raw daily indexes):

  Timestamps : formats/precision/missing/invalid per source (API, SGML header, index page); filing date vs
               acceptance date; duplicate acceptance seconds; cross-source disagreements; and a TEST OF THE
               TIMEZONE CONVENTION - three hypotheses (header=Eastern, API=true UTC, API=Eastern-labelled-Z)
               are scored against two documented SEC facts: EDGAR accepts filings 06:00-22:00 ET on business
               days, and filings accepted after 17:30 ET receive the next business day's filing date.
  Duplicates : raw index rows, unique accessions, multi-filer filings, exact duplicate rows, duplicate URLs,
               duplicate primary documents (content hash), originals vs amendments.
  Coverage   : filings per day, missing business days, companies/CIKs/tickers, form + item + SIC distribution,
               retrieval success rates, text-extraction success, document sizes, exhibits.
  Alignment  : acceptance time vs US equity trading sessions.

Outputs (--out-dir): quality_metrics.json, quality_report.md, and CSV tables. Nothing is estimated; values that
cannot be computed are null. Synthetic test data must never be reported as SEC results.

Usage
  python sec_edgar_quality_analysis.py --data-root data --out-dir reports --start 2026-10-01 --end 2026-10-31
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import sys
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")
except Exception as e:  # noqa: BLE001
    raise SystemExit("zoneinfo data missing - run: pip install tzdata   (" + str(e) + ")")

LOG = logging.getLogger("sec_edgar_quality")
DEFAULT_CLOSED = ("2026-01-01,2026-01-19,2026-02-16,2026-05-25,2026-06-19,2026-07-03,"
                  "2026-09-07,2026-10-12,2026-11-11,2026-11-26,2026-12-25")
OK_STATUS = ("success", "skipped_cached")


def pct(n, d):
    return None if not d else round(100.0 * n / d, 4)


def load(proc: Path, name: str):
    for ext, fn in (("parquet", pd.read_parquet), ("csv", pd.read_csv)):
        p = proc / f"{name}.{ext}"
        if p.exists():
            return fn(p)
    return None


def col(df, name):
    return df[name] if name in df.columns else pd.Series([None] * len(df), index=df.index, dtype="object")


# --------------------------------------------------------------------------- timestamp tests
def to_et(wall: pd.Series, assume: str) -> pd.Series:
    """naive wall-clock series -> tz-aware ET, assuming the wall clock is 'ET' or 'UTC'."""
    if assume == "ET":
        return wall.dt.tz_localize(ET, ambiguous="NaT", nonexistent="NaT")
    return wall.dt.tz_localize("UTC").dt.tz_convert(ET)


def hypothesis_scores(wall: pd.Series, assume: str, filing_date: pd.Series) -> dict:
    ok = wall.notna()
    n = int(ok.sum())
    if n == 0:
        return {"n": 0}
    et = to_et(wall[ok], assume)
    et = et[et.notna()]
    if len(et) == 0:
        return {"n": 0}
    secs = et.dt.hour * 3600 + et.dt.minute * 60 + et.dt.second
    weekday = et.dt.weekday < 5
    in_hours = (secs >= 6 * 3600) & (secs < 22 * 3600) & weekday
    fd = pd.to_datetime(filing_date.reindex(et.index), errors="coerce")
    gap = (fd - et.dt.tz_localize(None).dt.normalize()).dt.days
    after = secs >= 17 * 3600 + 1800
    have = gap.notna()
    consistent = np.where(after[have], gap[have] >= 1, gap[have] == 0)
    return {"n": int(len(et)),
            "pct_outside_edgar_hours_or_weekend": pct(int((~in_hours).sum()), len(et)),
            "filing_date_rule_evaluated": int(have.sum()),
            "filing_date_rule_violation_pct": pct(int((~consistent).sum()), int(have.sum())),
            "weekend_acceptances": int((~weekday).sum())}


# --------------------------------------------------------------------------- main analysis
def analyse(a: argparse.Namespace) -> dict:
    root = Path(a.data_root)
    proc, raw = root / "processed", root / "raw"
    fp = load(proc, "filings_primary")
    if fp is None or fp.empty:
        raise SystemExit(f"No processed primary filings in {proc}. Run collector then parser first.")
    fm, fo, ex = load(proc, "filings_margin"), load(proc, "filings_other"), load(proc, "exhibits")
    n = len(fp)
    start, end = date.fromisoformat(a.start), date.fromisoformat(a.end)
    closed = {date.fromisoformat(x) for x in a.closed_dates.split(",") if x.strip()}
    M: dict = {"period": [a.start, a.end], "primary_dataset": "forms 8-K and 8-K/A, filed (EDGAR filing date) inside the period",
               "total_filings_primary": n}

    # ---------------- timestamps
    api = col(fp, "sub_acceptanceDateTime").astype("string")
    hdr = col(fp, "hdr_acceptance_raw").astype("string")
    pag = col(fp, "page_accepted_raw").astype("string")
    api_ok = api.str.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z?$", na=False)
    hdr_ok = hdr.str.fullmatch(r"\d{14}", na=False)
    pag_ok = pag.str.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", na=False)
    api_wall = pd.to_datetime(api.where(api_ok).str[:19], format="%Y-%m-%dT%H:%M:%S", errors="coerce")
    hdr_wall = pd.to_datetime(hdr.where(hdr_ok), format="%Y%m%d%H%M%S", errors="coerce")
    pag_wall = pd.to_datetime(pag.where(pag_ok).str[:19], format="%Y-%m-%d %H:%M:%S", errors="coerce")

    def src(name, raw_s, ok, wall, fmt):
        present = raw_s.notna() & (raw_s.str.strip() != "")
        return {"format": fmt, "present_pct": pct(int(present.sum()), n), "missing_pct": pct(int((~present).sum()), n),
                "invalid_pct_of_present": pct(int((present & wall.isna()).sum()), int(present.sum())),
                "pct_nonzero_seconds_of_valid": pct(int((wall.dt.second.fillna(0) != 0).sum()), int(wall.notna().sum())),
                "precision": "seconds" if (wall.dt.second.fillna(0) != 0).any() else "no evidence of seconds precision"}

    gap_days = col(fp, "filing_date_minus_accepted_date_days")
    sess = col(fp, "session_bucket")
    conv = col(fp, "acceptance_convention").fillna("unverifiable")
    fd = pd.to_datetime(col(fp, "filing_date"), errors="coerce")
    acc_et_date = pd.to_datetime(col(fp, "accepted_date_et"), errors="coerce")
    best = pd.to_datetime(col(fp, "acceptance_utc_best"), errors="coerce", utc=True)
    dup_sec = best.dropna().value_counts()
    cross = {}
    for fa, fb, nm in (("idx_date_filed", "sub_filingDate", "idx_vs_submissions"),
                       ("idx_date_filed", "hdr_filed_as_of_date", "idx_vs_header"),
                       ("idx_date_filed", "page_filing_date", "idx_vs_index_page")):
        x = col(fp, fa).astype("string").str.replace("-", "", regex=False)
        y = col(fp, fb).astype("string").str.replace("-", "", regex=False)
        both = x.notna() & y.notna()
        cross[nm] = {"compared": int(both.sum()), "disagree": int((x[both] != y[both]).sum())}
    pw = pag_wall
    both = pw.notna() & hdr_wall.notna()
    cross["header_vs_index_page_accepted"] = {"compared": int(both.sum()),
                                              "disagree": int((pw[both] != hdr_wall[both]).sum())}
    M["timestamp_analysis"] = {
        "sources": {"submissions_api_acceptanceDateTime": src("api", api, api_ok, api_wall, "ISO-8601 'YYYY-MM-DDTHH:MM:SS.mmmZ'"),
                    "sgml_header_ACCEPTANCE-DATETIME": src("hdr", hdr, hdr_ok, hdr_wall, "YYYYMMDDHHMMSS, no zone"),
                    "index_page_Accepted": src("page", pag, pag_ok, pag_wall, "'YYYY-MM-DD HH:MM:SS' (page labels it Eastern)")},
        "timezone_note": ("Zone is NOT stated in the data. Header assumed US Eastern wall-clock (unverified in official docs); "
                          "API suffix 'Z' is contested by third-party reports. See hypothesis test below."),
        "acceptance_convention_counts": conv.value_counts().to_dict(),
        "timezone_hypothesis_test": {
            "H1_header_is_eastern": hypothesis_scores(hdr_wall, "ET", fd),
            "H2_api_is_true_utc": hypothesis_scores(api_wall, "UTC", fd),
            "H3_api_wallclock_is_eastern": hypothesis_scores(api_wall, "ET", fd),
            "how_to_read": ("Lowest rule-violation % and lowest out-of-hours % indicates the correct interpretation. "
                            "If H2 and H3 differ across days, the API convention is mixed (see convention_by_day.csv)."),
        },
        "filing_date_minus_accepted_date_days": col(fp, "filing_date_minus_accepted_date_days").value_counts(dropna=False).sort_index().to_dict()
        if "filing_date_minus_accepted_date_days" in fp.columns else None,
        "filing_date_rule_consistent_pct_header_basis": pct(int((col(fp, "filing_date_rule_consistent") == True).sum()),  # noqa: E712
                                                           int(col(fp, "filing_date_rule_consistent").notna().sum())),
        "filings_sharing_identical_acceptance_second": {"seconds_with_multiple_filings": int((dup_sec > 1).sum()),
                                                        "filings_involved": int(dup_sec[dup_sec > 1].sum()),
                                                        "max_in_one_second": int(dup_sec.max()) if len(dup_sec) else None},
        "cross_source_disagreements": cross,
        "missing_acceptance_any_source_pct": pct(int((~(api_ok | hdr_ok | pag_ok)).sum()), n),
        "missing_header_acceptance_pct": pct(int((~hdr_ok).sum()), n),
    }

    # ---------------- duplicates
    idx_rows = int(col(fp, "idx_row_count").fillna(1).astype(int).sum()) + (
        int(col(fm, "idx_row_count").fillna(1).astype(int).sum()) if fm is not None else 0)
    exact_dup_lines, total_lines = 0, 0
    for p in sorted((raw / "metadata/daily-index").glob("*/QTR*/master.*.idx")) if (raw / "metadata/daily-index").is_dir() else []:
        seen: Counter = Counter()
        in_data = False
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            if not in_data:
                in_data = line.startswith("CIK|Company Name")
                continue
            if line.count("|") == 4:
                seen[line] += 1
        total_lines += sum(seen.values())
        exact_dup_lines += sum(c - 1 for c in seen.values() if c > 1)
    urls = col(fp, "primary_doc_url").dropna()
    sha = col(fp, "primary_doc_sha256").dropna()
    sha_counts = sha.value_counts()
    fa = col(fp, "accession")
    amend = col(fp, "is_amendment").fillna(False).astype(bool)
    key = col(fp, "idx_cik").astype(str) + "|" + col(fp, "idx_date_filed").astype(str)
    orig_days = set(key[~amend]); am_days = set(key[amend])
    M["duplicate_analysis"] = {
        "index_rows_for_selected_forms_incl_margin": idx_rows,
        "unique_accessions_primary": int(fa.nunique()),
        "duplicate_accession_rows_in_processed": int(len(fa) - fa.nunique()),
        "multi_filer_accessions(listed under several CIKs in index)": int((col(fp, "idx_row_count").fillna(1).astype(int) > 1).sum()),
        "exact_duplicate_index_lines_all_forms": {"total_lines": total_lines, "duplicates": exact_dup_lines,
                                                 "duplicate_pct": pct(exact_dup_lines, total_lines)},
        "duplicate_primary_doc_urls": {"with_url": int(len(urls)), "redundant": int(len(urls) - urls.nunique()),
                                       "duplicate_pct": pct(int(len(urls) - urls.nunique()), int(len(urls)))},
        "duplicate_primary_documents_by_sha256": {"with_hash": int(len(sha)), "redundant": int(len(sha) - sha.nunique()),
                                                  "duplicate_pct": pct(int(len(sha) - sha.nunique()), int(len(sha))),
                                                  "largest_identical_group": int(sha_counts.max()) if len(sha_counts) else None,
                                                  "note": "identical content under different accessions is legitimate (e.g. templated filings); "
                                                          "treat as 'near-duplicate event' candidates, not errors"},
        "originals_8k": int((~amend).sum()), "amendments_8k_a": int(amend.sum()),
        "amendment_pct": pct(int(amend.sum()), n),
        "cik_days_with_both_original_and_amendment": len(orig_days & am_days),
        "duplicate_pct_definition": "redundant records / records with the key; accession duplicates are expected to be 0",
    }

    # ---------------- coverage
    per_day = col(fp, "idx_date_filed").value_counts().sort_index()
    all_days, d = [], start
    while d <= end:
        all_days.append(d); d += timedelta(days=1)
    expected = [x for x in all_days if x.weekday() < 5 and x not in closed]
    have_days = set(per_day.index)
    missing_bd = [x.isoformat() for x in expected if x.isoformat() not in have_days]
    odd_days = [k for k in per_day.index if date.fromisoformat(k).weekday() >= 5 or date.fromisoformat(k) in closed]
    names = col(fp, "sub_entity_name").fillna(col(fp, "idx_company_name"))
    tick = col(fp, "sub_tickers").dropna().str.split(";").explode()
    form_counts = {}
    fc = raw / "manifests/index_form_counts.json"
    if fc.exists():
        tot: Counter = Counter()
        for dd, cs in json.loads(fc.read_text()).items():
            if start.strftime("%Y%m%d") <= dd <= end.strftime("%Y%m%d"):
                tot.update(cs)
        form_counts = dict(tot.most_common(60))
    items = col(fp, "items_list").dropna().str.split(";").explode()
    item_df = items.value_counts().rename_axis("item").reset_index(name="filings")
    M["coverage_analysis"] = {
        "total_filings": n, "date_range_observed": [min(have_days), max(have_days)] if have_days else None,
        "expected_business_days(assumes closed dates list)": len(expected),
        "missing_business_days": missing_bd, "filings_on_assumed_closed_days": odd_days,
        "unique_companies(by name)": int(names.nunique()), "unique_ciks": int(col(fp, "idx_cik").nunique()),
        "unique_tickers": int(tick.nunique()), "filings_with_ticker_pct": pct(int(col(fp, "sub_tickers").notna().sum()), n),
        "form_type_distribution_selected": col(fp, "idx_form_type").value_counts().to_dict(),
        "all_form_types_in_daily_indexes_top60": form_counts,
        "eight_k_items": {"filings_with_item_metadata": int(col(fp, "items_list").notna().sum()),
                          "filings_without_item_metadata_pct": pct(int(col(fp, "items_list").isna().sum()), n),
                          "top_items": items.value_counts().head(15).to_dict(),
                          "unknown_item_numbers": col(fp, "unknown_item_numbers").dropna().value_counts().to_dict()},
        "sic_top15": col(fp, "sub_sic_description").dropna().value_counts().head(15).to_dict(),
        "exchange_distribution": col(fp, "sub_exchanges").dropna().str.split(";").explode().value_counts().to_dict(),
        "filings_with_sic_pct": pct(int(col(fp, "sub_sic").notna().sum()), n),
    }

    # ---------------- retrieval + content
    def rate(colname):
        s = col(fp, colname).fillna("not_attempted")
        c = s.value_counts().to_dict()
        ok = int(s.isin(OK_STATUS).sum())
        return {"status_counts": c, "success_incl_cached": ok, "success_pct": pct(ok, n)}

    sizes = pd.to_numeric(col(fp, "primary_doc_bytes"), errors="coerce").dropna()
    txt = col(fp, "text_status").fillna("not_attempted")
    attempted = int((txt != "not_attempted").sum())
    M["retrieval_and_content"] = {
        "submissions_record_found": {"found": int(col(fp, "has_submissions_record").fillna(False).astype(bool).sum()),
                                     "pct": pct(int(col(fp, "has_submissions_record").fillna(False).astype(bool).sum()), n)},
        "header_retrieval": rate("header_status"), "index_page_retrieval": rate("index_page_status"),
        "primary_document_retrieval": rate("primary_doc_status"),
        "text_extraction": {"status_counts": txt.value_counts().to_dict(),
                            "success_pct_of_all_filings": pct(int((txt == "success").sum()), n),
                            "success_pct_of_attempted": pct(int((txt == "success").sum()), attempted)},
        "document_size_bytes": ({"n": int(len(sizes)), "min": int(sizes.min()), "median": float(sizes.median()),
                                 "p95": float(sizes.quantile(0.95)), "max": int(sizes.max()),
                                 "empty_documents": int((sizes == 0).sum())} if len(sizes) else None),
        "items_in_text_vs_metadata": {"compared": int(col(fp, "items_text_matches_metadata").notna().sum()),
                                      "metadata_items_all_found_in_text_pct": pct(int((col(fp, "items_text_matches_metadata") == True).sum()),  # noqa: E712
                                                                                 int(col(fp, "items_text_matches_metadata").notna().sum()))},
        "exhibits": {"filings_with_index_page_parsed": int(col(fp, "page_document_count").notna().sum()),
                     "filings_with_1plus_exhibit_pct": pct(int((col(fp, "page_exhibit_count").fillna(0) > 0).sum()),
                                                           int(col(fp, "page_document_count").notna().sum())),
                     "exhibit_type_top15": (ex[ex["is_exhibit"] == True]["doc_type"].value_counts().head(15).to_dict()  # noqa: E712
                                            if ex is not None and not ex.empty else {})},
        "incomplete_or_inaccessible_filings": {
            "primary_doc_not_ok": sorted(col(fp, "accession")[~col(fp, "primary_doc_status").isin(OK_STATUS)].tolist())[:500]},
    }

    # ---------------- market-session alignment
    hours = col(fp, "accepted_et")
    hh = pd.to_datetime(hours, errors="coerce").dt.hour
    M["market_session_alignment"] = {
        "session_distribution": sess.value_counts().to_dict(),
        "pct_outside_regular_session": pct(int((sess.notna() & (sess != "regular_session")).sum()), int(sess.notna().sum())),
        "pct_accepted_after_1730_et(next-business-day filing date)": pct(int((col(fp, "accepted_after_1730_et") == True).sum()),  # noqa: E712
                                                                         int(col(fp, "accepted_after_1730_et").notna().sum())),
        "filings_by_hour_et": hh.value_counts().sort_index().to_dict(),
        "buckets": "pre_market 04:00-09:30, regular 09:30-16:00, after_hours 16:00-20:00, overnight 20:00-04:00 (ET)",
        "note": ("Alignment to an event's tradable timestamp needs a trading calendar and the acceptance time "
                 "(not the filing date). Filing date alone can be a full business day later than acceptance."),
    }
    if fm is not None and not fm.empty:
        M["acceptance_window_check"] = {
            "filed_in_window_but_accepted_before_start": int((pd.to_datetime(col(fp, "accepted_date_et"), errors="coerce").dt.date < start).sum()),
            "filed_after_end_but_accepted_inside_window": int((col(fm, "in_acceptance_window_et") == True).sum()),  # noqa: E712
            "margin_filings_with_header": int(col(fm, "has_header").fillna(False).astype(bool).sum()),
            "margin_filings_total": int(len(fm)),
        }
    if fo is not None and not fo.empty:
        M["other_forms_note"] = {"rows": int(len(fo)), "forms": col(fo, "idx_form_type").value_counts().to_dict(),
                                 "note": "kept in filings_other; excluded from every metric above"}

    # ---------------- outputs
    out = Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    (out / "quality_metrics.json").write_text(json.dumps(M, indent=2, default=str))
    per_day.rename_axis("filing_date").reset_index(name="filings").to_csv(out / "filings_per_day.csv", index=False)
    item_df.to_csv(out / "items_distribution.csv", index=False)
    col(fp, "idx_form_type").value_counts().rename_axis("form").reset_index(name="filings").to_csv(out / "form_distribution.csv", index=False)
    sess.value_counts().rename_axis("session").reset_index(name="filings").to_csv(out / "session_distribution.csv", index=False)
    pd.DataFrame({"accepted_date_et": acc_et_date.dt.date, "conv": conv}).dropna().groupby(["accepted_date_et", "conv"]).size() \
        .unstack(fill_value=0).to_csv(out / "convention_by_day.csv")
    col(fp, "sub_sic_description").value_counts().rename_axis("sic_description").reset_index(name="filings").to_csv(out / "sic_distribution.csv", index=False)
    names.value_counts().head(100).rename_axis("company").reset_index(name="filings").to_csv(out / "top_companies.csv", index=False)
    write_md(M, out / "quality_report.md")
    return M


def write_md(M: dict, path: Path) -> None:
    t, d, c, r, m = (M["timestamp_analysis"], M["duplicate_analysis"], M["coverage_analysis"],
                     M["retrieval_and_content"], M["market_session_alignment"])
    L = [f"# SEC EDGAR 8-K data-quality report ({M['period'][0]} to {M['period'][1]})", "",
         "_Generated by sec_edgar_quality_analysis.py from collected records. Values are computed, not estimated._", "",
         f"**Primary dataset:** {M['primary_dataset']}", f"**Total filings:** {M['total_filings_primary']:,}", "",
         "## 1. Timestamps", "", "| Source | Format | Missing % | Invalid % of present | Precision |", "|---|---|---|---|---|"]
    for k, v in t["sources"].items():
        L.append(f"| {k} | {v['format']} | {v['missing_pct']} | {v['invalid_pct_of_present']} | {v['precision']} |")
    L += ["", f"> {t['timezone_note']}", "", "**Timezone hypothesis test** (lower violation % = better)", "",
          "| Hypothesis | n | outside EDGAR hours % | filing-date rule violation % | weekend acceptances |", "|---|---|---|---|---|"]
    for k, v in t["timezone_hypothesis_test"].items():
        if isinstance(v, dict):
            L.append(f"| {k} | {v.get('n')} | {v.get('pct_outside_edgar_hours_or_weekend')} | "
                     f"{v.get('filing_date_rule_violation_pct')} | {v.get('weekend_acceptances')} |")
    L += ["", f"Per-filing API-vs-header convention: `{t['acceptance_convention_counts']}`  (daily breakdown: convention_by_day.csv)", "",
          f"Filing date minus acceptance date (days): `{t['filing_date_minus_accepted_date_days']}`", "",
          f"Cross-source date disagreements: `{t['cross_source_disagreements']}`", "",
          "## 2. Duplicates", "", f"```\n{json.dumps(d, indent=2)}\n```", "", "## 3. Coverage", "",
          f"```\n{json.dumps(c, indent=2, default=str)}\n```", "", "## 4. Retrieval and content", "",
          f"```\n{json.dumps(r, indent=2, default=str)}\n```", "", "## 5. Market-session alignment", "",
          f"```\n{json.dumps(m, indent=2, default=str)}\n```"]
    if "acceptance_window_check" in M:
        L += ["", "## 6. Filing-date vs acceptance-date window", "", f"```\n{json.dumps(M['acceptance_window_check'], indent=2)}\n```"]
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-root", default="data")
    ap.add_argument("--out-dir", default="reports")
    ap.add_argument("--start", default="2026-10-01")
    ap.add_argument("--end", default="2026-10-31")
    ap.add_argument("--closed-dates", default=DEFAULT_CLOSED)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    analyse(a)
    LOG.info("reports written to %s", a.out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
