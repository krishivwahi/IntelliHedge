#!/usr/bin/env python3
"""
Generate SYNTHETIC GKG-format files (27 tab-separated columns) to smoke-test the parser and
quality-analysis code when real GDELT data cannot be downloaded. These records are INVENTED:
no number computed from them may be reported as a GDELT result.

Deliberate features so every code path is exercised:
  * one missing slot, one slot with a malformed (short) line
  * a repeated URL under a new GKGRECORDID, an exact repeated row, a repeated headline
  * one record with a bad V2.1DATE, one with no page publication timestamp
  * one translingual-style record carrying TRANSLATIONINFO
"""
import sys
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

out = Path(sys.argv[1] if len(sys.argv) > 1 else "tests/synthetic_raw")
start = datetime(2026, 10, 1)


def rec(i, slot, url, title, pub, theme="ECON_STOCKMARKET", date=None, transl=""):
    stamp = slot.strftime("%Y%m%d%H%M%S")
    extras = f"<PAGE_TITLE>{title}</PAGE_TITLE>" + (f"<PAGE_PRECISEPUBTIMESTAMP>{pub}</PAGE_PRECISEPUBTIMESTAMP>" if pub else "")
    cols = [f"{stamp}-{i}", date or stamp, "1", url.split("/")[2], url, "", "", theme, f"{theme},120;TAX_FNCACT_CEO,300",
            "1#New York#US#USNY#40.7#-74.0#123", "1#New York#US#USNY#40.7#-74.0#123#55",
            "jane doe;john roe", "jane doe,10;john roe,40", "acme corp", "acme corp,20",
            "-2.5,1.2,3.7,4.9,20.1,5.5,420", "", "", "", "", "", "", "", "", "", transl, extras]
    assert len(cols) == 27
    return "\t".join(cols)


for day in range(2):
    for s in range(96):
        slot = start + timedelta(days=day, minutes=15 * s)
        if day == 1 and s == 10:
            continue  # missing slot
        lines = []
        for k in range(5):
            pub = (slot - timedelta(minutes=7 + k, seconds=13)).strftime("%Y%m%d%H%M%S") if k != 3 else None
            lines.append(rec(k, slot, f"https://www.example{k}.com/a/{day}/{s}/{k}", f"Headline {day}-{s}-{k}", pub))
        if s == 5:
            lines.append(rec(9, slot, "https://www.example0.com/a/0/0/0?utm_source=x", "Headline 0-0-0", None))  # dup URL (normalised)
            lines.append(lines[0])                                                                            # exact dup row
            lines.append(rec(10, slot, "https://www.example7.com/z", "Bad date", None, date="20261O01"))      # bad timestamp
            lines.append(rec(11, slot, "https://www.example8.com/y", "Foreign", None, transl="srclc:deu;eng:Google Translate"))
        if day == 0 and s == 7:
            lines.append("only\tthree\tfields")  # malformed line
        p = out / slot.strftime("%Y%m%d") / f"{slot:%Y%m%d%H%M%S}.gkg.csv.zip"
        p.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(f"{slot:%Y%m%d%H%M%S}.gkg.csv", "\n".join(lines) + "\n")
print("synthetic raw files written to", out)
