#!/usr/bin/env python3
"""Chunked, source-separated quality metrics for FNSPID news CSVs."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from collections import Counter
import pandas as pd
from fnspid_parser import find_col, process_frame

def analyse(path:Path,chunksize=100000,start=None,end=None):
    metrics={"file":str(path),"rows":0,"missing":{},"unique_publishers":0,"unique_tickers":0,
             "unique_urls":0,"unique_authors":0,"date_min":None,"date_max":None,
             "invalid_dates":0,"duplicate_exact_rows_estimate":0,"duplicate_urls":0,
             "duplicate_headlines":0,"daily_counts":{},"publisher_counts":{},"ticker_counts":{}}
    seen_rows=set(); urls=set(); titles=set(); title_publisher=set(); article_ticker=set(); pubs=set(); tickers=set(); authors=set(); days=Counter(); pcounts=Counter(); tcounts=Counter()
    for chunk in pd.read_csv(path,chunksize=chunksize,low_memory=False):
        n=len(chunk); metrics["rows"]+=n
        # Exact row hashes are computed over original CSV values, independent of derived fields.
        for row in chunk.astype("string").fillna("").itertuples(index=False,name=None):
            digest=hashlib.sha256("\\x1f".join(row).encode("utf-8")).hexdigest()
            if digest in seen_rows: metrics["duplicate_exact_rows_estimate"] += 1
            else: seen_rows.add(digest)
        for c in chunk.columns:
            metrics["missing"][c]=metrics["missing"].get(c,0)+int(chunk[c].isna().sum())
        dcol=find_col(chunk.columns,"date"); tcol=find_col(chunk.columns,"title"); ucol=find_col(chunk.columns,"url")
        pcol=find_col(chunk.columns,"publisher"); scol=find_col(chunk.columns,"ticker"); acol=find_col(chunk.columns,"author")
        if dcol:
            dt=pd.to_datetime(chunk[dcol],errors="coerce",format="mixed",utc=True)
            metrics["invalid_dates"]+=int(dt.isna().sum())
            if dt.notna().any():
                lo,hi=dt.min(),dt.max()
                metrics["date_min"]=str(lo) if metrics["date_min"] is None else min(metrics["date_min"],str(lo))
                metrics["date_max"]=str(hi) if metrics["date_max"] is None else max(metrics["date_max"],str(hi))
                days.update(dt.dropna().dt.strftime("%Y-%m-%d"))
        if ucol:
            norm=chunk[ucol].astype("string").str.strip().str.lower().str.replace(r"[?#].*$","",regex=True).str.rstrip("/")
            for x in norm.dropna():
                if x in urls: metrics["duplicate_urls"]+=1
                else: urls.add(x)
        if tcol:
            for x in chunk[tcol].dropna().astype(str).str.strip().str.lower():
                if x in titles: metrics["duplicate_headlines"]+=1
                else: titles.add(x)
        if pcol: pcounts.update(chunk[pcol].dropna().astype(str))
        if scol:
            vals=chunk[scol].astype("string").str.upper().str.strip()
            tcounts.update(vals.dropna())
        if acol: authors.update(chunk[acol].dropna().astype(str))
    metrics["unique_urls"]=len(urls); metrics["unique_publishers"]=len(pcounts)
    metrics["unique_tickers"]=len(tcounts); metrics["unique_authors"]=len(authors)
    metrics["daily_counts"]=dict(days); metrics["publisher_counts"]=dict(pcounts.most_common(50)); metrics["ticker_counts"]=dict(tcounts.most_common(100))
    metrics["missing_pct"]={k:round(v/metrics["rows"]*100,4) if metrics["rows"] else None for k,v in metrics["missing"].items()}
    return metrics

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files",nargs="+"); ap.add_argument("--out-dir",default="reports"); ap.add_argument("--chunksize",type=int,default=100000)
    ap.add_argument("--start"); ap.add_argument("--end")
    a=ap.parse_args(); out=Path(a.out_dir); out.mkdir(parents=True,exist_ok=True)
    results=[]
    for f in a.files:
        m=analyse(Path(f),a.chunksize,a.start,a.end); results.append(m)
        print(f"{f}: {m['rows']:,} rows, {m['unique_tickers']:,} tickers, dates {m['date_min']} to {m['date_max']}")
    payload={"note":"Metrics are computed on the supplied local files; no real-data result is implied by this package.","sources":results}
    (out/"quality_metrics.json").write_text(json.dumps(payload,indent=2,default=str),encoding="utf-8")
    lines=["# FNSPID data quality report","","> Generated from local files. Check scope and source paths in quality_metrics.json.",""]
    for m in results:
        lines += [f"## {m['file']}","",f"- Rows: {m['rows']:,}",f"- Date range: {m['date_min']} to {m['date_max']}",f"- Invalid dates: {m['invalid_dates']:,}",f"- Unique tickers: {m['unique_tickers']:,}",f"- Unique publishers: {m['unique_publishers']:,}",f"- Unique URLs: {m['unique_urls']:,}",f"- Repeated normalized URLs (within file): {m['duplicate_urls']:,}",f"- Repeated headlines (within file): {m['duplicate_headlines']:,}",""]
    (out/"DATA_QUALITY_REPORT.md").write_text("\n".join(lines),encoding="utf-8")
if __name__=="__main__": main()
