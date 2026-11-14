#!/usr/bin/env python3
"""Chunked FNSPID CSV / ZIP parser. Original columns and raw date values are retained."""
from __future__ import annotations
import argparse, json, re, zipfile
from pathlib import Path
import pandas as pd
from fnspid_dates import parse_date_series, has_explicit_offset, normalize_ticker, normalize_url

ALIASES = {
 "date": ["date","datetime","published_at","timestamp"],
 "title": ["article_title","title","headline"],
 "ticker": ["stock_symbol","ticker","symbol"],
 "url": ["url","article_url","link"],
 "publisher": ["publisher","source","site"],
 "author": ["author","authors"],
 "article": ["article","content","text"],
}
def find_col(cols, key):
    lookup={str(c).strip().lower():c for c in cols}
    for a in ALIASES[key]:
        if a in lookup: return lookup[a]
    return None

def process_frame(df):
    out=df.copy()
    for key in ALIASES:
        col=find_col(out.columns,key)
        if col is not None:
            out[f"ih_{key}"]=out[col]
            if key=="date":
                out["ih_timestamp_parsed_utc_comparable"]=parse_date_series(out[col])
                out["ih_timestamp_had_explicit_offset"]=has_explicit_offset(out[col])
            elif key=="ticker": out["ih_ticker_normalized"]=normalize_ticker(out[col])
            elif key=="url": out["ih_url_normalized"]=normalize_url(out[col])
    return out

def parse_csv(src:Path,dest:Path,chunksize=100_000,start=None,end=None):
    dest.parent.mkdir(parents=True,exist_ok=True)
    total=0; wrote=False; writer=None
    fmt=dest.suffix.lower()
    if fmt not in (".csv",".parquet"): raise ValueError("Output must be .csv or .parquet")
    try:
        for chunk in pd.read_csv(src,chunksize=chunksize,low_memory=False):
            cooked=process_frame(chunk)
            if "ih_timestamp_parsed_utc_comparable" in cooked and (start or end):
                dt=pd.to_datetime(cooked["ih_timestamp_parsed_utc_comparable"],errors="coerce",utc=True)
                mask=pd.Series(True,index=cooked.index)
                if start: mask &= dt>=pd.Timestamp(start,tz="UTC")
                if end: mask &= dt<pd.Timestamp(end,tz="UTC")+pd.Timedelta(days=1)
                cooked=cooked.loc[mask]
            if cooked.empty: continue
            if fmt==".parquet":
                import pyarrow as pa, pyarrow.parquet as pq
                table=pa.Table.from_pandas(cooked,preserve_index=False)
                if writer is None: writer=pq.ParquetWriter(dest,table.schema,compression="snappy")
                writer.write_table(table)
            else:
                cooked.to_csv(dest,mode="a" if wrote else "w",index=False,header=not wrote)
            wrote=True; total+=len(cooked)
    finally:
        if writer is not None: writer.close()
    if not wrote:
        if fmt==".csv": dest.write_text("",encoding="utf-8")
        else:
            import pyarrow as pa, pyarrow.parquet as pq
            pq.write_table(pa.table({}),dest)
    return total

def parse_stock_zip(src:Path,outdir:Path):
    outdir.mkdir(parents=True,exist_ok=True); manifest=[]
    with zipfile.ZipFile(src) as z:
        for info in z.infolist():
            if info.is_dir(): continue
            if info.filename.lower().endswith((".csv",".txt")):
                target=outdir/(Path(info.filename).stem+".csv")
                with z.open(info) as f, open(target,"wb") as o:
                    while True:
                        b=f.read(8*1024*1024)
                        if not b: break
                        o.write(b)
                manifest.append({"member":info.filename,"extracted_to":str(target),"bytes":target.stat().st_size})
    (outdir/"zip_members.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    return manifest

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--news",nargs="*",default=[])
    ap.add_argument("--stock-zip")
    ap.add_argument("--out-dir",default="data/processed")
    ap.add_argument("--format",choices=["csv","parquet"],default="parquet")
    ap.add_argument("--chunksize",type=int,default=100000)
    ap.add_argument("--start"); ap.add_argument("--end")
    a=ap.parse_args(); root=Path(a.out_dir)
    for f in a.news:
        src=Path(f); dest=root/"news"/(src.stem+("_"+a.start+"_"+a.end if a.start and a.end else "" )+("." + a.format))
        n=parse_csv(src,dest,a.chunksize,a.start,a.end); print(f"{src}: {n:,} rows -> {dest}")
    if a.stock_zip:
        items=parse_stock_zip(Path(a.stock_zip),root/"stock_prices")
        print(f"Extracted {len(items)} CSV/TXT members")
if __name__=="__main__": main()
