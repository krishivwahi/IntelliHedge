from pathlib import Path
from dotenv import dotenv_values
import requests
import json
import time
import csv
import hashlib

BASE = Path("reports/alpaca_collection_oct2023")
NEWS_DIR = BASE / "news_batches"
BARS_DIR = BASE / "sip_batches"

NEWS_DIR.mkdir(parents=True, exist_ok=True)
BARS_DIR.mkdir(parents=True, exist_ok=True)

START = "2023-10-01T00:00:00Z"
END = "2023-11-01T00:00:00Z"
BATCH_SIZE = 50

env = dotenv_values(Path.cwd() / ".env")
key = env.get("APCA_API_KEY_ID")
secret = env.get("APCA_API_SECRET_KEY")

if not key or not secret:
    raise SystemExit("Missing Alpaca credentials in .env")

headers = {
    "APCA-API-KEY-ID": key,
    "APCA-API-SECRET-KEY": secret
}

session = requests.Session()
session.headers.update(headers)

ticker_file = Path(
    "reports/alpaca_audit/final_oct2023_ticker_universe.csv"
)

if not ticker_file.exists():
    raise SystemExit(f"Missing ticker universe: {ticker_file}")

with open(ticker_file, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    tickers = sorted({
        row["symbol"].strip().upper()
        for row in reader if row.get("symbol")
    })

print("Eligible tickers:", len(tickers))

batches = [
    tickers[i:i+BATCH_SIZE]
    for i in range(0, len(tickers), BATCH_SIZE)
]

def request_json(url, params):
    for attempt in range(8):
        try:
            r = session.get(url, params=params, timeout=60)

            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", "10"))
                print("Rate limited. Waiting", wait, "seconds")
                time.sleep(wait)
                continue

            if r.status_code >= 500:
                time.sleep(min(2 ** attempt, 60))
                continue

            r.raise_for_status()
            return r.json()

        except requests.RequestException as e:
            if attempt == 7:
                raise
            print("Request retry:", str(e)[:150])
            time.sleep(min(2 ** attempt, 60))

    raise RuntimeError("Maximum retries exceeded")

def save_jsonl(path, records):
    temp = path.with_suffix(path.suffix + ".tmp")
    with open(temp, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    temp.replace(path)

def collect_news(batch, index):
    path = NEWS_DIR / f"news_{index:03d}.jsonl"
    if path.exists():
        return "SKIPPED"

    params = {
        "symbols": ",".join(batch),
        "start": START,
        "end": END,
        "limit": 50,
        "sort": "asc",
        "include_content": "false"
    }

    records = []
    pages = 0

    while True:
        data = request_json(
            "https://data.alpaca.markets/v1beta1/news",
            params
        )

        page = data.get("news", [])
        records.extend(page)
        pages += 1

        token = data.get("next_page_token")
        if not token:
            break

        params["page_token"] = token
        time.sleep(0.15)

    save_jsonl(path, records)
    return f"{len(records)} articles / {pages} pages"

def collect_bars(batch, index):
    path = BARS_DIR / f"sip_{index:03d}.jsonl"
    if path.exists():
        return "SKIPPED"

    params = {
        "symbols": ",".join(batch),
        "timeframe": "1Day",
        "start": START,
        "end": END,
        "feed": "sip",
        "adjustment": "raw",
        "limit": 10000,
        "sort": "asc"
    }

    records = []
    pages = 0

    while True:
        data = request_json(
            "https://data.alpaca.markets/v2/stocks/bars",
            params
        )

        for symbol, bars in data.get("bars", {}).items():
            for bar in bars:
                records.append({
                    "symbol": symbol,
                    **bar
                })

        pages += 1
        token = data.get("next_page_token")

        if not token:
            break

        params["page_token"] = token
        time.sleep(0.15)

    save_jsonl(path, records)
    return f"{len(records)} bars / {pages} pages"

print("\n========== NEWS COLLECTION ==========")

for i, batch in enumerate(batches, 1):
    try:
        result = collect_news(batch, i)
        print(f"News batch {i}/{len(batches)}: {result}")
    except Exception as e:
        print(f"NEWS FAILED batch {i}: {e}")
        raise

print("\n========== SIP COLLECTION ==========")

for i, batch in enumerate(batches, 1):
    try:
        result = collect_bars(batch, i)
        print(f"SIP batch {i}/{len(batches)}: {result}")
    except Exception as e:
        print(f"SIP FAILED batch {i}: {e}")
        raise

print("\n========== COLLECTION COMPLETE ==========")
print("News batches:", len(list(NEWS_DIR.glob("*.jsonl"))))
print("SIP batches:", len(list(BARS_DIR.glob("*.jsonl"))))
print("Output:", BASE.resolve())
print("All completed batches are preserved for resuming.")
