#!/usr/bin/env python3
"""
gdelt_parser.py - parse GDELT 2.x GKG files into analysis-ready Parquet/CSV.

* Every ORIGINAL field is preserved, verbatim, as a string column named after the codebook
  (GKGRECORDID ... V2EXTRASXML). Nothing is invented.
* Derived columns (prefixed by lower-case names) are clearly separate and only unpack data that
  is physically present in the original fields (URL domain, tone sub-values, page title from
  V2EXTRASXML, theme/person/org/location lists, ...).
* Raw zip files in --raw-dir are never modified. Processed output goes to --out-dir, one file
  per UTC day: gkg_YYYYMMDD.parquet (or .csv.gz if pyarrow is unavailable).

Usage
  python gdelt_parser.py --raw-dir data/raw --out-dir data/processed --start 2026-10-01 --end 2026-10-31
  python gdelt_parser.py --raw-dir data/raw --out-dir data/processed --slim   # drop GCAM/XML blobs
"""
from __future__ import annotations

import argparse
import csv
import html
import io
import logging
import re
import sys
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

LOG = logging.getLogger("gdelt_parser")

# GKG 2.1 column order (27 tab-separated fields), as defined in the GDELT GKG 2.1 codebook.
GKG_COLUMNS = [
    "GKGRECORDID",                 # YYYYMMDDHHMMSS-N (or -TN for translingual)
    "V2.1DATE",                    # YYYYMMDDHHMMSS (UTC) - see docs: batch/first-seen time, NOT article pub time
    "V2SOURCECOLLECTIONIDENTIFIER",# 1=WEB 2=CITATIONONLY 3=CORE 4=DTIC 5=JSTOR 6=NONTEXTUALSOURCE
    "V2SOURCECOMMONNAME",          # usually the domain of the source
    "V2DOCUMENTIDENTIFIER",        # URL (or other document id)
    "V1COUNTS",
    "V2.1COUNTS",
    "V1THEMES",
    "V2ENHANCEDTHEMES",            # THEME,charoffset;...
    "V1LOCATIONS",
    "V2ENHANCEDLOCATIONS",         # type#name#cc#adm1[#adm2]#lat#lon#featureid#offset;...
    "V1PERSONS",
    "V2ENHANCEDPERSONS",           # name,offset;...
    "V1ORGANIZATIONS",
    "V2ENHANCEDORGANIZATIONS",
    "V2.1TONE",                    # tone,pos,neg,polarity,activity,selfgroup,wordcount
    "V2.1ENHANCEDDATES",
    "V2GCAM",
    "V2.1SHARINGIMAGE",
    "V2.1RELATEDIMAGES",
    "V2.1SOCIALIMAGEEMBEDS",
    "V2.1SOCIALVIDEOEMBEDS",
    "V2.1QUOTATIONS",
    "V2.1ALLNAMES",
    "V2.1AMOUNTS",
    "V2.1TRANSLATIONINFO",
    "V2EXTRASXML",
]
HEAVY_COLUMNS = ["V2GCAM", "V2EXTRASXML", "V2.1QUOTATIONS", "V2.1ALLNAMES", "V2.1AMOUNTS",
                 "V2.1ENHANCEDDATES", "V2.1SOCIALIMAGEEMBEDS", "V2.1SOCIALVIDEOEMBEDS",
                 "V2.1RELATEDIMAGES", "V2.1SHARINGIMAGE", "V1COUNTS", "V2.1COUNTS"]
COLLECTION = {"1": "WEB", "2": "CITATIONONLY", "3": "CORE", "4": "DTIC", "5": "JSTOR", "6": "NONTEXTUALSOURCE"}

RE_TITLE = r"<PAGE_TITLE>(.*?)</PAGE_TITLE>"
RE_PUB = r"<PAGE_PRECISEPUBTIMESTAMP>(\d+)</PAGE_PRECISEPUBTIMESTAMP>"
RE_AUTH = r"<PAGE_AUTHORS>(.*?)</PAGE_AUTHORS>"
RE_SRCLANG = re.compile(r"srclc:([a-zA-Z\-]+)")
RE_SLOT = re.compile(r"(\d{14})\.(?:translation\.)?gkg\.csv\.zip$")


# --------------------------------------------------------------------------- reading
def read_gkg_zip(path: Path) -> tuple[pd.DataFrame, dict]:
    """Read one GKG zip. Returns (dataframe of original columns as str, parse stats)."""
    stats = {"file": path.name, "lines": 0, "rows": 0, "dropped_malformed": 0, "short_rows": 0}
    with zipfile.ZipFile(path) as zf:
        member = [i for i in zf.infolist() if i.filename.lower().endswith(".csv")][0]
        data = zf.read(member)
    # A well-formed GKG line has exactly 27 fields = 26 tabs. Anything else is quarantined
    # (counted, not silently padded/merged) so malformed lines can never distort the analysis.
    lines = [ln for ln in data.split(b"\n") if ln.strip(b"\r")]
    good = [ln for ln in lines if ln.count(b"\t") == len(GKG_COLUMNS) - 1]
    stats["lines"] = len(lines)
    stats["dropped_malformed"] = len(lines) - len(good)
    df = pd.read_csv(io.BytesIO(b"\n".join(good)), sep="\t", header=None, names=GKG_COLUMNS, dtype=str,
                     quoting=csv.QUOTE_NONE, encoding="utf-8", encoding_errors="replace",
                     keep_default_na=False, na_values=[], engine="c") if good else pd.DataFrame(columns=GKG_COLUMNS)
    stats["rows"] = len(df)
    # keep_default_na=False -> empty fields are "" (original content), convert to NA for analysis
    df = df.replace("", pd.NA)
    m = RE_SLOT.search(path.name)
    df["file_slot"] = m.group(1) if m else None
    df["source_file"] = path.name
    df["stream"] = "translation" if ".translation." in path.name else "english"
    return df, stats


# --------------------------------------------------------------------------- derived fields
def _domain(u):
    if not isinstance(u, str) or not u.lower().startswith(("http://", "https://")):
        return pd.NA
    host = urlparse(u).hostname
    if not host:
        return pd.NA
    host = host.lower()
    return host[4:] if host.startswith("www.") else host


def _names_before_comma(s):
    """'THEME,123;THEME2,456' -> unique names, order kept."""
    if not isinstance(s, str):
        return pd.NA
    seen, out = set(), []
    for item in s.split(";"):
        n = item.rsplit(",", 1)[0].strip()
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return ";".join(out) if out else pd.NA


def _split_semicolon(s):
    if not isinstance(s, str):
        return pd.NA
    items = list(dict.fromkeys(x.strip() for x in s.split(";") if x.strip()))
    return ";".join(items) if items else pd.NA


def _locations(s):
    """Enhanced locations -> (names, country codes). Field count differs by version, so index
    from the front for name/country (positions 1 and 2), which are stable."""
    if not isinstance(s, str):
        return pd.NA, pd.NA
    names, ccs = [], []
    for blk in s.split(";"):
        f = blk.split("#")
        if len(f) >= 3:
            if f[1] and f[1] not in names:
                names.append(f[1])
            if f[2] and f[2] not in ccs:
                ccs.append(f[2])
    return (";".join(names) or pd.NA), (";".join(ccs) or pd.NA)


def add_derived(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    d = df
    d["record_ts"] = pd.to_datetime(d["V2.1DATE"], format="%Y%m%d%H%M%S", errors="coerce", utc=True)
    d["source_collection"] = d["V2SOURCECOLLECTIONIDENTIFIER"].map(COLLECTION)
    d["url"] = d["V2DOCUMENTIDENTIFIER"].where(d["V2DOCUMENTIDENTIFIER"].str.startswith(("http://", "https://"), na=False))
    d["source_domain"] = d["V2DOCUMENTIDENTIFIER"].map(_domain)

    extras = d["V2EXTRASXML"]
    d["headline"] = extras.str.extract(RE_TITLE, expand=False).map(lambda x: html.unescape(x).strip() if isinstance(x, str) else pd.NA)
    d["page_pub_ts_raw"] = extras.str.extract(RE_PUB, expand=False)
    d["page_pub_ts"] = pd.to_datetime(d["page_pub_ts_raw"], format="%Y%m%d%H%M%S", errors="coerce", utc=True)
    d["page_authors"] = extras.str.extract(RE_AUTH, expand=False)

    tone = d["V2.1TONE"].str.split(",", expand=True).reindex(columns=range(7))
    for i, col in enumerate(["tone", "tone_positive", "tone_negative", "tone_polarity",
                             "tone_activity_density", "tone_selfgroup_density", "word_count"]):
        d[col] = pd.to_numeric(tone[i], errors="coerce")

    themes = d["V2ENHANCEDTHEMES"].map(_names_before_comma)
    d["themes"] = themes.where(themes.notna(), d["V1THEMES"].map(_split_semicolon))
    d["persons"] = d["V1PERSONS"].map(_split_semicolon)
    d["organizations"] = d["V1ORGANIZATIONS"].map(_split_semicolon)
    loc = d["V2ENHANCEDLOCATIONS"].map(_locations)
    d["location_names"] = loc.map(lambda t: t[0])
    d["location_countries"] = loc.map(lambda t: t[1])
    for col, base in [("n_themes", "themes"), ("n_persons", "persons"),
                      ("n_organizations", "organizations"), ("n_locations", "location_names")]:
        d[col] = d[base].map(lambda s: 0 if pd.isna(s) else s.count(";") + 1).astype("int32")

    def lang(row_info, stream):
        if isinstance(row_info, str):
            m = RE_SRCLANG.search(row_info)
            if m:
                return m.group(1).lower()
        return "eng" if stream == "english" else pd.NA
    d["language"] = [lang(i, s) for i, s in zip(d["V2.1TRANSLATIONINFO"], d["stream"])]
    d["language_basis"] = ["translationinfo" if isinstance(i, str) and RE_SRCLANG.search(i)
                           else ("english-stream (inferred from file stream)" if s == "english" else "unknown")
                           for i, s in zip(d["V2.1TRANSLATIONINFO"], d["stream"])]
    return d


# --------------------------------------------------------------------------- output
def write_day(df: pd.DataFrame, out_dir: Path, day: str, fmt: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    if fmt == "parquet":
        try:
            p = out_dir / f"gkg_{day}.parquet"
            df.to_parquet(p, index=False)
            return p
        except ImportError:
            LOG.warning("pyarrow/fastparquet missing - falling back to csv.gz")
    p = out_dir / f"gkg_{day}.csv.gz"
    df.to_csv(p, index=False, compression="gzip")
    return p


def run(args: argparse.Namespace) -> int:
    raw_dir, out_dir = Path(args.raw_dir), Path(args.out_dir)
    start = datetime.strptime(args.start, "%Y-%m-%d")
    end = datetime.strptime(args.end, "%Y-%m-%d")
    days = [(start + timedelta(days=i)).strftime("%Y%m%d") for i in range((end - start).days + 1)]
    all_stats, written = [], []
    for day in days:
        target = out_dir / f"gkg_{day}.parquet"
        target_csv = out_dir / f"gkg_{day}.csv.gz"
        if (target.exists() or target_csv.exists()) and not args.force:
            LOG.info("%s already processed - skipping (use --force)", day)
            continue
        files = sorted((raw_dir / day).glob("*.gkg.csv.zip")) if (raw_dir / day).is_dir() else []
        if not files:
            LOG.warning("%s: no raw files", day)
            continue
        parts = []
        for f in files:
            try:
                part, st = read_gkg_zip(f)
            except Exception as e:  # corrupt file that slipped through
                LOG.error("%s: cannot parse (%s)", f.name, e)
                all_stats.append({"file": f.name, "error": str(e)})
                continue
            all_stats.append(st)
            parts.append(part)
        if not parts:
            continue
        df = add_derived(pd.concat(parts, ignore_index=True))
        if args.slim:
            df = df.drop(columns=[c for c in HEAVY_COLUMNS if c in df.columns])
        p = write_day(df, out_dir, day, args.format)
        written.append(str(p))
        LOG.info("%s: %d records from %d files -> %s", day, len(df), len(parts), p.name)
    if all_stats:
        out_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(all_stats).to_csv(out_dir / "parse_stats.csv", index=False)
    LOG.info("done: %d day-files written", len(written))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw-dir", default="data/raw")
    ap.add_argument("--out-dir", default="data/processed")
    ap.add_argument("--start", default="2026-10-01")
    ap.add_argument("--end", default="2026-10-31")
    ap.add_argument("--format", choices=["parquet", "csv"], default="parquet")
    ap.add_argument("--slim", action="store_true",
                    help="drop bulky original columns (GCAM, XML extras, quotations...) after deriving fields; "
                         "originals remain in the raw zips")
    ap.add_argument("--force", action="store_true", help="re-process days that already have output")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
