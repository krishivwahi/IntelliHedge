from pathlib import Path
import json
import csv

news_file = Path("reports/alpaca_collection_oct2023/cleaned/alpaca_news_oct2023_clean.jsonl")
fnspid_file = Path("FNSPID/data/processed/news_oct2023/cleaned/news_oct2023_deduplicated.csv")
bars_dir = Path("reports/alpaca_collection_oct2023/sip_batches")

news_tickers = set()
with open(news_file, encoding="utf-8") as f:
    for line in f:
        row = json.loads(line)
        news_tickers.update(s.upper() for s in row.get("symbols", []))

fnspid_tickers = set()
with open(fnspid_file, encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        if row.get("Stock_symbol"):
            fnspid_tickers.add(row["Stock_symbol"].strip().upper())

sip_tickers = set()
sip_dates = set()
sip_rows = 0

for file in bars_dir.glob("*.jsonl"):
    with open(file, encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            sip_tickers.add(row["symbol"].upper())
            sip_dates.add(row["t"][:10])
            sip_rows += 1

print("========== FINAL CROSS-DATASET AUDIT ==========")
print("Alpaca news tickers:", len(news_tickers))
print("FNSPID news tickers:", len(fnspid_tickers))
print("Alpaca SIP tickers:", len(sip_tickers))
print("News + FNSPID overlap:", len(news_tickers & fnspid_tickers))
print("News + SIP overlap:", len(news_tickers & sip_tickers))
print("All three datasets overlap:", len(news_tickers & fnspid_tickers & sip_tickers))
print("FNSPID + SIP overlap:", len(fnspid_tickers & sip_tickers))
print("SIP records:", sip_rows)
print("SIP trading dates:", len(sip_dates))
print("SIP date range:", min(sip_dates), "to", max(sip_dates))

print("\nFINAL AUDIT COMPLETE")
