#!/usr/bin/env python3
"""FNSPID source inspector and resumable downloader. No large download occurs by default."""
from __future__ import annotations
import argparse, csv, hashlib, json, os, sys, time, zipfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
import requests

BASE = "https://huggingface.co/datasets/Zihan1004/FNSPID/resolve/main/"
SOURCES = {
    "all_external": BASE + "Stock_news/All_external.csv",
    "nasdaq_external": BASE + "Stock_news/nasdaq_exteral_data.csv",
    "stock_prices": BASE + "Stock_price/full_history.zip",
}
CHUNK = 8 * 1024 * 1024

def request_metadata(url, timeout=45):
    headers = {"User-Agent": "IntelliHedgeV2-FNSPID-research/1.0"}
    r = requests.get(url, headers={**headers, "Range": "bytes=0-0"}, stream=True,
                     allow_redirects=True, timeout=timeout)
    r.raise_for_status()
    h = r.headers
    size = h.get("x-linked-size") or h.get("content-range", "").split("/")[-1]
    if not size or not str(size).isdigit():
        size = h.get("content-length")
    result = {"requested_url": url, "final_url": r.url, "status": r.status_code,
              "size_bytes": int(size) if size and str(size).isdigit() else None,
              "etag": h.get("etag"), "accept_ranges": h.get("accept-ranges"),
              "content_type": h.get("content-type"), "xet_hash": h.get("x-xet-hash")}
    r.close()
    return result

def inspect(out):
    out.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    inventory = {"checked_at_utc": datetime.utcnow().isoformat(timespec="seconds")+"Z",
                 "repository": "https://huggingface.co/datasets/Zihan1004/FNSPID",
                 "files": {}}
    for name, url in SOURCES.items():
        try:
            inventory["files"][name] = request_metadata(url)
        except Exception as e:
            inventory["files"][name] = {"requested_url": url, "error": str(e)}
    path = out / "source_inventory.json"
    path.write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    print(json.dumps(inventory, indent=2))
    print(f"\nSaved: {path}")
    return inventory

def download(url, dest, retries=5, timeout=90):
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    headers = {"User-Agent": "IntelliHedgeV2-FNSPID-research/1.0"}
    for attempt in range(retries):
        offset = part.stat().st_size if part.exists() else 0
        try:
            h = dict(headers)
            if offset: h["Range"] = f"bytes={offset}-"
            with requests.get(url, headers=h, stream=True, timeout=timeout) as r:
                if offset and r.status_code == 200: # server ignored range; restart safely
                    offset = 0
                    with open(part, "wb") as f:
                        for b in r.iter_content(CHUNK):
                            if b: f.write(b)
                else:
                    r.raise_for_status()
                    mode = "ab" if offset and r.status_code == 206 else "wb"
                    with open(part, mode) as f:
                        for b in r.iter_content(CHUNK):
                            if b: f.write(b)
            os.replace(part, dest)
            return dest
        except Exception:
            if attempt + 1 == retries: raise
            time.sleep(min(60, 2 ** attempt))
    raise RuntimeError("download failed")

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(CHUNK),b""): h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    sub=ap.add_subparsers(dest="cmd",required=True)
    i=sub.add_parser("inspect", help="HEAD/range probe source sizes and metadata")
    i.add_argument("--out-dir",default="data/raw/manifests")
    d=sub.add_parser("download",help="download one named complete source file; resumable")
    d.add_argument("--source",choices=SOURCES,required=True)
    d.add_argument("--out-dir",default="data/raw")
    args=ap.parse_args()
    if args.cmd=="inspect":
        inspect(Path(args.out_dir)); return
    url=SOURCES[args.source]
    destdir=Path(args.out_dir)
    suffix=".zip" if args.source=="stock_prices" else ".csv"
    name={"all_external":"All_external.csv","nasdaq_external":"nasdaq_exteral_data.csv","stock_prices":"full_history.zip"}[args.source]
    dest=destdir/("stock_prices" if args.source=="stock_prices" else "news")/name
    meta=request_metadata(url)
    print(f"Remote size: {meta.get('size_bytes')} bytes ({(meta.get('size_bytes') or 0)/1e9:.2f} GB)")
    if dest.exists():
        print("Already downloaded:",dest,"SHA256:",sha256(dest)); return
    download(url,dest)
    result={"source":args.source,"path":str(dest),"bytes":dest.stat().st_size,"sha256":sha256(dest),"downloaded_at_utc":datetime.utcnow().isoformat()+"Z","remote":meta}
    manifest=destdir/"manifests"/"download_manifest.json"
    manifest.parent.mkdir(parents=True,exist_ok=True)
    old=json.loads(manifest.read_text()) if manifest.exists() else {"downloads":[]}
    old["downloads"].append(result)
    manifest.write_text(json.dumps(old,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))
    if suffix==".zip":
        with zipfile.ZipFile(dest) as z:
            print("ZIP members:")
            for x in z.infolist()[:100]: print(x.filename,x.file_size)
if __name__=="__main__": main()
