#!/usr/bin/env python3
"""
sec_edgar_parser.py - turn raw SEC EDGAR files (from sec_edgar_collector.py) into analysis-ready tables.

Inputs  (data/raw): manifests/filings_selected.csv, manifests/manifest.csv, metadata/submissions/*.json,
                    metadata/headers/*.hdr.sgml, metadata/index_pages/*-index.html, filings/<cik>/<acc>/<doc>
Outputs (data/processed):
    filings_primary.parquet|csv   one row per filing, forms 8-K / 8-K/A, filed inside the window
    filings_margin.parquet|csv    filings filed just after the window (header only) - for acceptance-date windowing
    filings_other.parquet|csv     any other configured form types (never mixed into the primary file)
    exhibits.parquet|csv          one row per document listed on each filing's index page (primary + exhibits)
    text/<accession>.txt          text extracted from the primary document (only when extraction succeeded)

Column prefixes keep sources separate and original values verbatim:
    idx_*  daily master index     sub_*  submissions API     hdr_*  SGML header     page_*  filing index page
Everything else is DERIVED and says so in its name/docs. Nothing that SEC does not provide is invented.

TIMESTAMPS - three different "times", never merged silently
    filing date          date SEC assigns (idx_date_filed / sub_filingDate / hdr_filed_as_of_date)
    acceptance datetime  moment EDGAR accepted the submission
                           hdr_acceptance_raw   SGML header <ACCEPTANCE-DATETIME> (YYYYMMDDHHMMSS)
                           sub_acceptanceDateTime  submissions API string, e.g. 2026-10-14T16:31:36.000Z
                         The API suffix 'Z' is NOT trusted: third-party reports (Oct 2026) say some JSON files
                         carry Eastern wall-clock time behind a 'Z' and that SEC began changing this around
                         2026-10-14. The parser therefore compares API vs header per filing and records the
                         inferred convention (acceptance_convention). The header is ASSUMED to be US Eastern
                         wall-clock time (unverified in official documentation; tested in the quality analysis
                         via the 5:30 p.m. ET rule).
    report date          period of report (sub_reportDate / hdr_period_of_report) - event date, not a publication time
    collection time      collected_at_utc from the download manifest

Usage
  python sec_edgar_parser.py --data-root data
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import sys
from datetime import date, datetime, time as dtime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional

import pandas as pd

try:
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")
except Exception as e:  # noqa: BLE001  (Windows without tzdata)
    raise SystemExit("zoneinfo data missing - run: pip install tzdata   (" + str(e) + ")")

LOG = logging.getLogger("sec_edgar_parser")
UTC = timezone.utc

# 8-K item titles. Source: third-party reference (edgar.tools 8-K item index) cross-checked with the form
# structure; the official Form 8-K PDF (sec.gov/files/form8-k.pdf) could not be fetched here - verify before
# publishing. Used only to LABEL item numbers; the item numbers themselves come from SEC metadata.
ITEM_TITLES = {
    "1.01": "Entry into a Material Definitive Agreement", "1.02": "Termination of a Material Definitive Agreement",
    "1.03": "Bankruptcy or Receivership", "1.04": "Mine Safety - Reporting of Shutdowns and Patterns of Violations",
    "1.05": "Material Cybersecurity Incidents",
    "2.01": "Completion of Acquisition or Disposition of Assets", "2.02": "Results of Operations and Financial Condition",
    "2.03": "Creation of a Direct Financial Obligation or an Obligation under an Off-Balance Sheet Arrangement",
    "2.04": "Triggering Events That Accelerate or Increase a Direct Financial Obligation",
    "2.05": "Costs Associated with Exit or Disposal Activities", "2.06": "Material Impairments",
    "3.01": "Notice of Delisting or Failure to Satisfy a Continued Listing Rule or Standard; Transfer of Listing",
    "3.02": "Unregistered Sales of Equity Securities", "3.03": "Material Modification to Rights of Security Holders",
    "4.01": "Changes in Registrant's Certifying Accountant",
    "4.02": "Non-Reliance on Previously Issued Financial Statements or a Related Audit Report",
    "5.01": "Changes in Control of Registrant",
    "5.02": "Departure of Directors or Certain Officers; Election of Directors; Appointment of Certain Officers; Compensatory Arrangements",
    "5.03": "Amendments to Articles of Incorporation or Bylaws; Change in Fiscal Year",
    "5.04": "Temporary Suspension of Trading Under Registrant's Employee Benefit Plans",
    "5.05": "Amendments to the Registrant's Code of Ethics, or Waiver of a Provision of the Code of Ethics",
    "5.06": "Change in Shell Company Status", "5.07": "Submission of Matters to a Vote of Security Holders",
    "5.08": "Shareholder Director Nominations",
    "6.01": "ABS Informational and Computational Material", "6.02": "Change of Servicer or Trustee",
    "6.03": "Change in Credit Enhancement or Other External Support", "6.04": "Failure to Make a Required Distribution",
    "6.05": "Securities Act Updating Disclosure", "7.01": "Regulation FD Disclosure", "8.01": "Other Events",
    "9.01": "Financial Statements and Exhibits",
}
PRIMARY_FORMS = {"8-K", "8-K/A"}


# --------------------------------------------------------------------------- master index (also used by tests)
def parse_master_idx(text: str) -> list[dict]:
    rows, in_data = [], False
    for line in text.splitlines():
        if not in_data:
            in_data = line.startswith("CIK|Company Name")
            continue
        parts = line.split("|")
        if len(parts) == 5:
            rows.append(dict(zip(["cik", "company_name", "form_type", "date_filed_raw", "filename"],
                                 (p.strip() for p in parts))))
    return rows


# --------------------------------------------------------------------------- SGML header
def parse_header(text: str) -> dict:
    out: dict = {"acceptance_raw": None, "items_desc": [], "filers": []}
    m = re.search(r"<ACCEPTANCE-DATETIME>\s*(\d+)", text)
    if m:
        out["acceptance_raw"] = m.group(1)
    cur: Optional[dict] = None
    for ln in text.splitlines():
        s = ln.strip()
        if not s or s.startswith("<"):
            continue
        if s.endswith(":") and s.upper() in ("FILER:", "SUBJECT COMPANY:", "FILED BY:", "REPORTING-OWNER:", "ISSUER:"):
            cur = {"role": s[:-1]}
            out["filers"].append(cur)
            continue
        if ":" not in s:
            continue
        k, v = s.split(":", 1)
        k, v = k.strip().upper(), v.strip()
        if k == "ITEM INFORMATION":
            out["items_desc"].append(v)
        elif k in ("ACCESSION NUMBER", "CONFORMED SUBMISSION TYPE", "PUBLIC DOCUMENT COUNT",
                   "CONFORMED PERIOD OF REPORT", "FILED AS OF DATE", "DATE AS OF CHANGE"):
            out[k] = v
        elif cur is not None and v:
            if k == "STANDARD INDUSTRIAL CLASSIFICATION":
                mm = re.search(r"\[(\d+)\]", v)
                cur["sic_code"] = mm.group(1) if mm else None
                cur["sic_desc"] = re.sub(r"\s*\[\d+\]\s*", "", v).strip()
            elif k in ("COMPANY CONFORMED NAME", "CENTRAL INDEX KEY", "STATE OF INCORPORATION",
                       "FISCAL YEAR END", "FORM TYPE", "SEC ACT", "SEC FILE NUMBER", "FILM NUMBER"):
                cur.setdefault(k, v)
    return out


# --------------------------------------------------------------------------- filing index page
class IndexPageParser(HTMLParser):
    """Extracts the 'infoHead/info' pairs and every row of the document tables."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.info: dict[str, str] = {}
        self.docs: list[dict] = []
        self._divs: list[str] = []
        self._cap: Optional[str] = None
        self._buf: list[str] = []
        self._head: Optional[str] = None
        self._table: Optional[str] = None
        self._row: Optional[list] = None
        self._cell: Optional[list] = None
        self._href: Optional[str] = None
        self._cells: list[tuple[str, Optional[str]]] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "div":
            cls = (a.get("class") or "").strip()
            self._divs.append(cls)
            if cls == "infoHead":
                self._cap, self._buf = "head", []
            elif cls == "info":
                self._cap, self._buf = "info", []
        elif tag == "table":
            self._table = a.get("summary") or a.get("class") or "table"
        elif tag == "tr":
            self._cells = []
        elif tag in ("td", "th"):
            self._cell, self._href = [], None
        elif tag == "a" and self._cell is not None and a.get("href") and self._href is None:
            self._href = a["href"]
        elif tag == "br" and self._cap:
            self._buf.append(" ")

    def handle_endtag(self, tag):
        if tag == "div" and self._divs:
            cls = self._divs.pop()
            if cls in ("infoHead", "info") and self._cap:
                text = re.sub(r"\s+", " ", " ".join(self._buf)).strip()
                if self._cap == "head":
                    self._head = text
                elif self._head is not None and self._head not in self.info:
                    self.info[self._head] = text
                self._cap = None
        elif tag in ("td", "th") and self._cell is not None:
            self._cells.append((re.sub(r"\s+", " ", " ".join(self._cell)).strip(), self._href))
            self._cell = None
        elif tag == "tr" and self._cells and self._table:
            self.docs.append({"table": self._table, "cells": self._cells})
            self._cells = []
        elif tag == "table":
            self._table = None

    def handle_data(self, data):
        if self._cap:
            self._buf.append(data)
        if self._cell is not None:
            self._cell.append(data)


def parse_index_page(html: str) -> dict:
    p = IndexPageParser()
    p.feed(html)
    docs = []
    for r in p.docs:
        c = r["cells"]
        if len(c) >= 4 and re.fullmatch(r"\d+", c[0][0] or ""):
            docs.append({"table": r["table"], "seq": int(c[0][0]), "description": c[1][0],
                         "document": c[2][0], "href": c[2][1], "doc_type": c[3][0],
                         "size": c[4][0] if len(c) > 4 else ""})
    return {"info": p.info, "documents": docs}


# --------------------------------------------------------------------------- text extraction
class TextExtractor(HTMLParser):
    SKIP = {"script", "style", "head", "ix:header", "noscript"}
    BLOCK = {"p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6", "table", "ul", "ol", "hr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        elif tag in self.BLOCK:
            self.parts.append("\n")
        elif tag in ("td", "th"):
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    p = TextExtractor()
    p.feed(html)
    t = "".join(p.parts).replace("\xa0", " ")
    t = re.sub(r"[ \t\r\f\v]+", " ", t)
    t = "\n".join(line.strip() for line in t.split("\n"))
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def extract_text(path: Path, min_chars: int) -> tuple[str, str]:
    """Return (status, text). status: success | too_short | unsupported_format | read_error."""
    ext = path.suffix.lower()
    try:
        raw = path.read_bytes().decode("utf-8", errors="replace")
    except OSError:
        return "read_error", ""
    if ext in (".htm", ".html", ".xhtml"):
        text = html_to_text(raw)
    elif ext in (".txt", ""):
        text = re.sub(r"\n{3,}", "\n\n", raw).strip()
    else:
        return "unsupported_format", ""
    return ("success" if len(text) >= min_chars else "too_short"), text


ITEM_RE = re.compile(r"\bItem\s+(\d\.\d{2})\b", re.I)


def items_in_text(text: str) -> list[str]:
    seen: list[str] = []
    for m in ITEM_RE.finditer(text):
        if m.group(1) not in seen:
            seen.append(m.group(1))
    return seen


# --------------------------------------------------------------------------- timestamps
def parse_api_accept(s) -> Optional[datetime]:
    """'2026-10-14T16:31:36.000Z' -> NAIVE wall-clock datetime (the zone is decided separately)."""
    if not isinstance(s, str):
        return None
    m = re.match(r"^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})", s)
    if not m:
        return None
    try:
        return datetime.strptime(f"{m.group(1)} {m.group(2)}", "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def parse_hdr_accept(s) -> Optional[datetime]:
    if not isinstance(s, str) or not re.fullmatch(r"\d{14}", s):
        return None
    try:
        return datetime.strptime(s, "%Y%m%d%H%M%S")
    except ValueError:
        return None


def infer_convention(api_wall: Optional[datetime], hdr_wall: Optional[datetime]) -> str:
    """Compare the API timestamp to the header timestamp (header assumed Eastern wall-clock)."""
    if api_wall is None or hdr_wall is None:
        return "unverifiable"
    if abs((api_wall - hdr_wall).total_seconds()) < 1:
        return "api_wallclock_equals_header_wallclock"      # i.e. Eastern time labelled 'Z'
    api_utc = api_wall.replace(tzinfo=UTC)
    hdr_utc = hdr_wall.replace(tzinfo=ET).astimezone(UTC)
    if abs((api_utc - hdr_utc).total_seconds()) < 1:
        return "api_true_utc"
    return "inconsistent"


def session_bucket(t: dtime) -> str:
    if dtime(4, 0) <= t < dtime(9, 30):
        return "pre_market"
    if dtime(9, 30) <= t < dtime(16, 0):
        return "regular_session"
    if dtime(16, 0) <= t < dtime(20, 0):
        return "after_hours"
    return "overnight_closed"


# --------------------------------------------------------------------------- assembly
def load_manifest(path: Path) -> dict[tuple[str, str], dict]:
    last: dict[tuple[str, str], dict] = {}
    if not path.exists():
        return last
    with path.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            last[(r["resource"], r["key"])] = r        # later rows win
    return last


def load_submissions(sub_dir: Path) -> tuple[dict[str, dict], dict[str, dict]]:
    """accession -> flattened sub_* row ; cik(10-digit) -> company-level info."""
    acc_rows, comp = {}, {}
    if not sub_dir.is_dir():
        return acc_rows, comp
    for p in sorted(sub_dir.glob("CIK*.json")):
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        cik10 = (obj.get("cik") or p.name[3:13]).zfill(10)
        if "filings" in obj:
            comp[cik10] = {"sub_entity_name": obj.get("name"), "sub_entity_type": obj.get("entityType"),
                           "sub_sic": obj.get("sic"), "sub_sic_description": obj.get("sicDescription"),
                           "sub_tickers": ";".join(obj.get("tickers") or []) or None,
                           "sub_exchanges": ";".join(x for x in (obj.get("exchanges") or []) if x) or None,
                           "sub_fiscal_year_end": obj.get("fiscalYearEnd"),
                           "sub_state_of_incorporation": obj.get("stateOfIncorporation")}
            rec = obj["filings"].get("recent", {})
        else:
            rec = obj
        cols = [k for k in rec if isinstance(rec[k], list)]
        for i, acc in enumerate(rec.get("accessionNumber", [])):
            acc_rows[acc] = {"sub_cik": cik10, **{f"sub_{k}": (rec[k][i] if i < len(rec[k]) else None) for k in cols
                                                   if k != "accessionNumber"}}
    return acc_rows, comp


def build(args: argparse.Namespace) -> int:
    root = Path(args.data_root)
    raw, proc = root / "raw", root / "processed"
    sel_path = raw / "manifests/filings_selected.csv"
    if not sel_path.exists():
        LOG.error("%s not found - run the collector first", sel_path)
        return 2
    sel = pd.read_csv(sel_path, dtype=str, keep_default_na=False)
    mani = load_manifest(raw / "manifests/manifest.csv")
    sub_acc, sub_comp = load_submissions(raw / "metadata/submissions")
    (proc / "text").mkdir(parents=True, exist_ok=True)

    recs, ex_rows = [], []
    for _, s in sel.iterrows():
        acc = s["accession"]
        r: dict = {"accession": acc, "idx_cik": s["cik"], "idx_company_name": s["company_name"],
                   "idx_form_type": s["form_type"], "idx_date_filed_raw": s["date_filed_raw"],
                   "idx_date_filed": s["date_filed"], "idx_filename": s["filename"],
                   "idx_file_date": s["idx_file_date"], "idx_row_count": int(s["index_rows"] or 1),
                   "idx_co_filer_ciks": s["co_filer_ciks"] or None,
                   "in_filing_date_window": s["in_filing_date_window"] == "True"}
        cik10 = s["cik"].zfill(10)
        r.update(sub_acc.get(acc, {}))
        r["has_submissions_record"] = acc in sub_acc
        r.update(sub_comp.get(cik10, {}))

        hp = raw / f"metadata/headers/{acc}.hdr.sgml"
        h = parse_header(hp.read_text(encoding="utf-8", errors="replace")) if hp.exists() else None
        r["has_header"] = h is not None
        if h:
            f0 = h["filers"][0] if h["filers"] else {}
            r.update({"hdr_acceptance_raw": h["acceptance_raw"], "hdr_form_type": h.get("CONFORMED SUBMISSION TYPE"),
                      "hdr_public_document_count": h.get("PUBLIC DOCUMENT COUNT"),
                      "hdr_period_of_report": h.get("CONFORMED PERIOD OF REPORT"),
                      "hdr_filed_as_of_date": h.get("FILED AS OF DATE"),
                      "hdr_item_descriptions": " | ".join(h["items_desc"]) or None,
                      "hdr_filer_count": len(h["filers"]), "hdr_company_name": f0.get("COMPANY CONFORMED NAME"),
                      "hdr_sic_code": f0.get("sic_code"), "hdr_sic_description": f0.get("sic_desc"),
                      "hdr_state_of_incorporation": f0.get("STATE OF INCORPORATION"),
                      "hdr_sec_file_number": f0.get("SEC FILE NUMBER"), "hdr_film_number": f0.get("FILM NUMBER")})

        # ---- timestamps
        api_wall = parse_api_accept(r.get("sub_acceptanceDateTime"))
        hdr_wall = parse_hdr_accept(r.get("hdr_acceptance_raw"))
        r["acceptance_convention"] = infer_convention(api_wall, hdr_wall)
        r["hdr_acceptance_utc_assuming_eastern"] = (hdr_wall.replace(tzinfo=ET).astimezone(UTC) if hdr_wall else None)
        r["sub_acceptance_if_true_utc"] = api_wall.replace(tzinfo=UTC) if api_wall else None
        best, src = None, None
        if hdr_wall:
            best, src = r["hdr_acceptance_utc_assuming_eastern"], "header(Eastern assumed)"
        elif api_wall:
            best, src = r["sub_acceptance_if_true_utc"], "api(UTC assumed, UNVERIFIED)"
        r["acceptance_utc_best"], r["acceptance_best_source"] = best, src
        r["acceptance_best_confidence"] = "medium" if hdr_wall else ("low" if api_wall else None)
        fd = s["date_filed"] or None
        r["filing_date"] = fd
        if best is not None:
            et = best.astimezone(ET)
            r["accepted_et"] = et.replace(tzinfo=None)
            r["accepted_date_et"] = et.date().isoformat()
            r["session_bucket"] = session_bucket(et.time())
            after_cut = et.time() >= dtime(17, 30)
            r["accepted_after_1730_et"] = after_cut
            if fd:
                gap = (date.fromisoformat(fd) - et.date()).days
                r["filing_date_minus_accepted_date_days"] = gap
                r["filing_date_rule_consistent"] = (gap >= 1) if after_cut else (gap == 0)
            r["in_acceptance_window_et"] = bool(args.start <= et.date().isoformat() <= args.end)
        # ---- form grouping
        form = (s["form_type"] or "").upper()
        r["is_amendment"] = form.endswith("/A")
        r["form_group"] = form if form in PRIMARY_FORMS else "other"
        # ---- items
        items = [x.strip() for x in str(r.get("sub_items") or "").split(",") if x.strip()]
        r["items_list"] = ";".join(items) or None
        r["items_titles"] = " | ".join(f"{i}: {ITEM_TITLES.get(i, 'UNKNOWN ITEM')}" for i in items) or None
        r["unknown_item_numbers"] = ";".join(i for i in items if i not in ITEM_TITLES) or None

        # ---- manifest-derived status
        for res in ("header", "index_page", "primary_doc"):
            m = mani.get((res, acc))
            r[f"{res}_status"] = m["status"] if m else "not_attempted"
            r[f"{res}_collected_at_utc"] = m["collected_at_utc"] if m else None
        pm = mani.get(("primary_doc", acc))
        r["primary_doc_bytes"] = int(pm["bytes"]) if pm and pm["bytes"] else None
        r["primary_doc_sha256"] = pm["sha256"] if pm else None
        r["primary_doc_url"] = pm["url"] if pm and pm["url"] else None
        r["primary_doc_local_path"] = pm["local_path"] if pm and pm["local_path"] else None
        r["primary_doc_filename"] = Path(pm["url"]).name if pm and pm["url"] else r.get("sub_primaryDocument")
        r["filing_index_url"] = f"https://www.sec.gov/Archives/edgar/data/{int(s['cik'])}/{acc}-index.html"

        # ---- index page
        ip = raw / f"metadata/index_pages/{acc}-index.html"
        if ip.exists():
            page = parse_index_page(ip.read_text(encoding="utf-8", errors="replace"))
            r["page_accepted_raw"] = page["info"].get("Accepted")
            r["page_filing_date"] = page["info"].get("Filing Date")
            r["page_period_of_report"] = page["info"].get("Period of Report")
            r["page_items_text"] = page["info"].get("Items")
            fmt_docs = [d for d in page["documents"] if "Document Format" in d["table"]]
            r["page_document_count"] = len(fmt_docs)
            r["page_exhibit_count"] = sum(1 for d in fmt_docs if d["doc_type"].upper().startswith("EX-"))
            r["page_data_file_count"] = sum(1 for d in page["documents"] if "Data Files" in d["table"])
            for d in page["documents"]:
                ex_rows.append({"accession": acc, "table": d["table"], "seq": d["seq"], "description": d["description"],
                                "document": d["document"], "href": d["href"], "doc_type": d["doc_type"], "size": d["size"],
                                "is_exhibit": d["doc_type"].upper().startswith("EX-"),
                                "is_primary": d["doc_type"].upper() == (s["form_type"] or "").upper()})

        # ---- text extraction (primary window filings with a downloaded document)
        r["text_status"] = "not_attempted"
        lp = r.get("primary_doc_local_path")
        if lp and r["in_filing_date_window"]:
            p = Path(lp)
            if not p.is_absolute() and not p.exists():
                p = root.parent / lp
            if p.exists():
                st, txt = extract_text(p, args.min_chars)
                r["text_status"], r["text_chars"] = st, len(txt)
                if st == "success":
                    (proc / "text" / f"{acc}.txt").write_text(txt, encoding="utf-8")
                    r["text_path"] = f"text/{acc}.txt"
                    tl = items_in_text(txt)
                    r["items_in_text"] = ";".join(tl) or None
                    if items:
                        r["items_text_matches_metadata"] = set(items) <= set(tl)
            else:
                r["text_status"] = "document_file_missing"
        recs.append(r)

    df = pd.DataFrame(recs)
    ex = pd.DataFrame(ex_rows)
    ext = "parquet" if args.format == "parquet" else "csv"

    def save(frame: pd.DataFrame, name: str):
        p = proc / f"{name}.{ext}"
        if frame.empty:
            LOG.info("%s: no rows", name)
            return
        if ext == "parquet":
            frame.to_parquet(p, index=False)
        else:
            frame.to_csv(p, index=False)
        LOG.info("%s: %d rows -> %s", name, len(frame), p.name)

    save(df[(df["form_group"] != "other") & df["in_filing_date_window"]], "filings_primary")
    save(df[~df["in_filing_date_window"]], "filings_margin")
    save(df[(df["form_group"] == "other") & df["in_filing_date_window"]], "filings_other")
    save(ex, "exhibits")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-root", default="data")
    ap.add_argument("--start", default="2026-10-01", help="acceptance-window start (ET date) for in_acceptance_window_et")
    ap.add_argument("--end", default="2026-10-31")
    ap.add_argument("--format", choices=["parquet", "csv"], default="parquet")
    ap.add_argument("--min-chars", type=int, default=200, help="text shorter than this is 'too_short'")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    return build(args)


if __name__ == "__main__":
    sys.exit(main())
