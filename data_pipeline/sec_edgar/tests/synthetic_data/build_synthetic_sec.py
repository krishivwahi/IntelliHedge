#!/usr/bin/env python3
"""
Builds a SYNTHETIC mini-EDGAR file tree (paths mirror the real URL layout) for testing only.
All companies, CIKs, accession numbers and texts are INVENTED ("SYNTHETIC ... CORP").
Nothing computed from this tree may be reported as a property of real SEC data.

Planted cases (window 2026-10-01..2026-10-05, margin to 2026-10-07):
  ACME   8-K    filed 10-01, accepted 10:15 ET, API = true UTC           -> normal, has EX-99.1, items 2.02/9.01
  BETA   8-K    accepted 10-01 18:00 ET (after 17:30) filed 10-02, API wall-clock == Eastern ('Z' mislabel)
  GAMMA  8-K/A  filed 10-02, listed only on an OLDER submissions page    -> pagination + amendment
  DELTA  8-K    filed 10-05, also listed under EPSILON's CIK (multi-filer), primary document 404
  ETA    8-K    filed 10-05, no submissions record, primary doc found via index page, SAME bytes as ACME
  IOTA   8-K    filed 10-02, primary document is an EMPTY file (HTTP 200, 0 bytes)
  ZETA   10-Q   filed 10-05 -> not selected (other form)
  THETA  8-K    filed 10-06 (after window) but accepted 10-05 18:30 ET   -> margin / acceptance-window test
  10-03, 10-04 (weekend) and 10-07: no daily index (404)
"""
from __future__ import annotations

import json
from pathlib import Path

DAYS = {
    "20261001": [(1, "SYNTHETIC ACME CORP", "8-K")],
    "20261002": [(2, "SYNTHETIC BETA CORP", "8-K"), (3, "SYNTHETIC GAMMA CORP", "8-K/A"), (9, "SYNTHETIC IOTA CORP", "8-K")],
    "20261005": [(4, "SYNTHETIC DELTA CORP", "8-K"), (5, "SYNTHETIC EPSILON CORP", "8-K"),
                 (6, "SYNTHETIC ZETA CORP", "10-Q"), (7, "SYNTHETIC ETA CORP", "8-K")],
    "20261006": [(8, "SYNTHETIC THETA CORP", "8-K")],
}
# cik -> (accession suffix, filing date, accepted ET wall clock yyyymmddhhmmss, api string or None, items, primary doc, text item)
F = {
    1: ("2026-10-01", "20261001101500", "2026-10-01T14:15:00.000Z", "2.02,9.01", "acme8k.htm"),
    2: ("2026-10-02", "20261001180000", "2026-10-01T18:00:00.000Z", "5.02", "beta8k.htm"),
    3: ("2026-10-02", "20261002090500", "2026-10-02T13:05:00.000Z", "1.01", "gamma8ka.htm"),
    4: ("2026-10-05", "20261005110000", "2026-10-05T15:00:00.000Z", "8.01", "delta8k.htm"),
    7: ("2026-10-05", "20261005120000", None, "2.02,9.01", "eta8k.htm"),
    8: ("2026-10-06", "20261005183000", "2026-10-05T22:30:00.000Z", "7.01", "theta8k.htm"),
    9: ("2026-10-02", "20261002140000", "2026-10-02T18:00:00.000Z", "8.01", "iota8k.htm"),
}
FORM = {1: "8-K", 2: "8-K", 3: "8-K/A", 4: "8-K", 7: "8-K", 8: "8-K", 9: "8-K"}
ITEM_TITLE = {"2.02": "Results of Operations and Financial Condition", "9.01": "Financial Statements and Exhibits",
              "5.02": "Departure of Directors or Certain Officers", "1.01": "Entry into a Material Definitive Agreement",
              "8.01": "Other Events", "7.01": "Regulation FD Disclosure"}


def acc(cik: int) -> str:
    return f"{cik:010d}-26-000001"


def nd(a: str) -> str:
    return a.replace("-", "")


def doc_html(name: str, items: str, extra: str = "") -> str:
    body = "".join(f"<p>Item {i} {ITEM_TITLE[i]}.</p><p>SYNTHETIC TEXT: {name} reports an invented event for software "
                   f"testing only. No real company or filing is described. {extra}</p>" for i in items.split(","))
    return (f"<html><head><title>8-K</title><style>.x{{color:red}}</style></head><body><p>UNITED STATES SECURITIES AND "
            f"EXCHANGE COMMISSION</p><p>FORM 8-K</p><p>CURRENT REPORT</p>{body}<p>SIGNATURE: Synthetic Officer</p></body></html>")


def master_idx(day: str) -> str:
    lines = ["Description:           Master Index of EDGAR Dissemination Feed by Form Type (SYNTHETIC)",
             f"Last Data Received:    {day}", "Comments:              synthetic test file", "", "CIK|Company Name|Form Type|Date Filed|Filename",
             "-" * 80]
    for cik, name, form in DAYS[day]:
        filed = f"{day[:4]}-{day[4:6]}-{day[6:]}" if day != "20261002" else day   # one file uses YYYYMMDD
        if cik == 8:
            filed = "2026-10-06"
        lines.append(f"{cik}|{name}|{form}|{filed}|edgar/data/{(4 if cik == 5 else cik)}/{acc(4 if cik == 5 else cik)}.txt")
    return "\n".join(lines) + "\n"


def header(cik: int, name: str) -> str:
    filed, accepted, _, items, _ = F[cik]
    a = acc(cik)
    item_lines = "".join(f"ITEM INFORMATION:\t\t{ITEM_TITLE[i]}\n" for i in items.split(","))
    return (f"<SEC-HEADER>{a}.hdr.sgml : {nd(filed)}\n<ACCEPTANCE-DATETIME>{accepted}\nACCESSION NUMBER:\t\t{a}\n"
            f"CONFORMED SUBMISSION TYPE:\t{FORM[cik]}\nPUBLIC DOCUMENT COUNT:\t\t2\nCONFORMED PERIOD OF REPORT:\t20260930\n"
            f"{item_lines}FILED AS OF DATE:\t\t{nd(filed)}\nDATE AS OF CHANGE:\t\t{nd(filed)}\n\nFILER:\n\n\tCOMPANY DATA:\t\n"
            f"\t\tCOMPANY CONFORMED NAME:\t\t\t{name}\n\t\tCENTRAL INDEX KEY:\t\t\t{cik:010d}\n"
            f"\t\tSTANDARD INDUSTRIAL CLASSIFICATION:\tSERVICES-PREPACKAGED SOFTWARE [7372]\n\t\tSTATE OF INCORPORATION:\t\t\tDE\n\n"
            f"\tFILING VALUES:\n\t\tFORM TYPE:\t\t{FORM[cik]}\n\t\tSEC ACT:\t\t34 Act\n\t\tSEC FILE NUMBER:\t001-{cik:05d}\n"
            f"\t\tFILM NUMBER:\t\t26{cik:07d}\n</SEC-HEADER>\n")


def index_page(cik: int) -> str:
    filed, accepted, _, items, prim = F[cik]
    acc_t = f"{accepted[:4]}-{accepted[4:6]}-{accepted[6:8]} {accepted[8:10]}:{accepted[10:12]}:{accepted[12:14]}"
    base = f"/Archives/edgar/data/{cik}/{nd(acc(cik))}"
    rows = f'<tr><td scope="row">1</td><td scope="row">{FORM[cik]}</td><td scope="row"><a href="{base}/{prim}">{prim}</a></td><td scope="row">{FORM[cik]}</td><td scope="row">1234</td></tr>'
    if cik == 1:
        rows += f'<tr><td scope="row">2</td><td scope="row">PRESS RELEASE</td><td scope="row"><a href="{base}/ex99.htm">ex99.htm</a></td><td scope="row">EX-99.1</td><td scope="row">900</td></tr>'
    item_txt = "<br/>".join(f"Item {i}: {ITEM_TITLE[i]}" for i in items.split(","))
    return (f'<html><body><div class="formGrouping"><div class="infoHead">Filing Date</div><div class="info">{filed}</div>'
            f'<div class="infoHead">Accepted</div><div class="info">{acc_t}</div><div class="infoHead">Period of Report</div>'
            f'<div class="info">2026-09-30</div><div class="infoHead">Items</div><div class="info">{item_txt}</div></div>'
            f'<table class="tableFile" summary="Document Format Files"><tr><th>Seq</th><th>Description</th><th>Document</th>'
            f'<th>Type</th><th>Size</th></tr>{rows}</table></body></html>')


def sub_json(cik: int, name: str, ticker: str | None) -> dict:
    cols = ["accessionNumber", "filingDate", "reportDate", "acceptanceDateTime", "act", "form", "fileNumber", "filmNumber",
            "items", "size", "isXBRL", "isInlineXBRL", "primaryDocument", "primaryDocDescription"]
    filed, _, api, items, prim = F[cik]
    row = [acc(cik), filed, "2026-09-30", api, "34", FORM[cik], f"001-{cik:05d}", f"26{cik:07d}", items, 1234, 0, 0, prim, FORM[cik]]
    rec = {c: [v] for c, v in zip(cols, row)}
    files = []
    if cik == 3:                                   # older page holds the filing; "recent" is empty
        rec = {c: [] for c in cols}
        files = [{"name": "CIK0000000003-submissions-001.json", "filingCount": 1, "filingFrom": "2026-01-01", "filingTo": "2026-10-05"}]
    return {"cik": str(cik), "entityType": "operating", "sic": "7372", "sicDescription": "Services-Prepackaged Software",
            "name": name, "tickers": [ticker] if ticker else [], "exchanges": ["Nasdaq"] if ticker else [], "fiscalYearEnd": "1231",
            "stateOfIncorporation": "DE", "filings": {"recent": rec, "files": files}}


def build(root: Path) -> None:
    def w(rel: str, content, binary=False):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content if binary else content.encode("utf-8"))

    # The mock quarterly listing must enumerate only daily indexes that exist.
    # DAYS contains the synthetic filing dates; omitted dates simulate missing
    # weekend/non-business-day indexes for the collector tests.
    listing_items = [
        {"name": f"master.{day}.idx", "type": "file"}
        for day in DAYS
    ]
    w(
        "Archives/edgar/daily-index/2026/QTR4/index.json",
        json.dumps({"directory": {"item": listing_items}})
    )

    for day in DAYS:
        w(f"Archives/edgar/daily-index/2026/QTR4/master.{day}.idx", master_idx(day))
    names = {c: n for d in DAYS.values() for c, n, _ in d}
    for cik in F:
        base = f"Archives/edgar/data/{cik}/{nd(acc(cik))}"
        w(f"{base}/{acc(cik)}.hdr.sgml", header(cik, names[cik]))
        if cik == 8:
            continue
        w(f"Archives/edgar/data/{cik}/{acc(cik)}-index.html", index_page(cik))
        prim = F[cik][4]
        if cik == 4:
            continue                                                  # primary document missing -> 404
        if cik == 9:
            w(f"{base}/{prim}", b"", binary=True)                     # empty document
        elif cik in (1, 7):
            w(f"{base}/{prim}", doc_html("SYNTHETIC SHARED TEMPLATE", F[cik][3]))   # identical bytes for ACME and ETA
        else:
            w(f"{base}/{prim}", doc_html(names[cik], F[cik][3]))
        if cik != 7:
            sub = sub_json(cik, names[cik], {1: "SYNA", 2: "SYNB"}.get(cik))
            w(f"submissions/CIK{cik:010d}.json", json.dumps(sub))
    w("submissions/CIK0000000003-submissions-001.json", json.dumps(
        {c: [v] for c, v in zip(["accessionNumber", "filingDate", "reportDate", "acceptanceDateTime", "act", "form", "fileNumber",
                                 "filmNumber", "items", "size", "isXBRL", "isInlineXBRL", "primaryDocument", "primaryDocDescription"],
                                [acc(3), "2026-10-02", "2026-09-30", "2026-10-02T13:05:00.000Z", "34", "8-K/A", "001-00003",
                                 "260000003", "1.01", 1234, 0, 0, "gamma8ka.htm", "8-K/A"])}))


if __name__ == "__main__":
    import sys
    build(Path(sys.argv[1] if len(sys.argv) > 1 else "server_root"))
    print("synthetic tree written")
