from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime
import json

base = Path("reports/alpaca_collection_oct2023")
news_dir = base / "news_batches"
bars_dir = base / "sip_batches"
report_dir = Path("reports/alpaca_audit")
report_dir.mkdir(parents=True, exist_ok=True)

news_files = sorted(news_dir.glob("*.jsonl"))
bar_files = sorted(bars_dir.glob("*.jsonl"))

news_ids = set()
news_tickers = set()
sources = Counter()
news_dates = Counter()
duplicate_news = 0
invalid_news_dates = 0
news_rows = 0

print("========== NEWS AUDIT ==========")

for file in news_files:
    with open(file, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue

            try:
                row = json.loads(line)
                news_rows += 1

                article_id = row.get("id")
                if article_id is not None:
                    if article_id in news_ids:
                        duplicate_news += 1
                    news_ids.add(article_id)

                sources[row.get("source") or "UNKNOWN"] += 1

                for symbol in row.get("symbols") or []:
                    news_tickers.add(symbol.upper())

                dt = row.get("created_at")
                try:
                    date = datetime.fromisoformat(
                        dt.replace("Z", "+00:00")
                    ).date().isoformat()
                    news_dates[date] += 1
                except Exception:
                    invalid_news_dates += 1

            except Exception:
                invalid_news_dates += 1

print("News batch files:", len(news_files))
print("Total news records:", news_rows)
print("Unique article IDs:", len(news_ids))
print("Duplicate article IDs:", duplicate_news)
print("Invalid/missing timestamps:", invalid_news_dates)
print("News tickers represented:", len(news_tickers))
print("News date range:",
      min(news_dates) if news_dates else None,
      "to",
      max(news_dates) if news_dates else None)

print("\nNEWS SOURCE DISTRIBUTION:")
for source, count in sources.most_common():
    print(source, count)

bars = 0
bar_tickers = set()
bar_dates = set()
ticker_dates = defaultdict(set)
ticker_counts = Counter()
duplicate_bars = 0
seen_bar_keys = set()
invalid_bars = 0

print("\n========== SIP AUDIT ==========")

for file in bar_files:
    with open(file, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue

            try:
                row = json.loads(line)
                symbol = row.get("symbol")
                timestamp = row.get("t")

                if not symbol or not timestamp:
                    invalid_bars += 1
                    continue

                day = timestamp[:10]
                key = (symbol, day)

                if key in seen_bar_keys:
                    duplicate_bars += 1
                seen_bar_keys.add(key)

                bars += 1
                bar_tickers.add(symbol)
                bar_dates.add(day)
                ticker_dates[symbol].add(day)
                ticker_counts[symbol] += 1

            except Exception:
                invalid_bars += 1

print("SIP batch files:", len(bar_files))
print("Total SIP bars:", bars)
print("Unique SIP tickers:", len(bar_tickers))
print("Unique trading dates:", len(bar_dates))
print("Date range:",
      min(bar_dates) if bar_dates else None,
      "to",
      max(bar_dates) if bar_dates else None)
print("Duplicate ticker-date bars:", duplicate_bars)
print("Invalid bar records:", invalid_bars)

print("\nSIP BAR COUNT DISTRIBUTION:")
print("Tickers with 22 bars:", sum(v == 22 for v in ticker_counts.values()))
print("Tickers with fewer than 22 bars:", sum(v < 22 for v in ticker_counts.values()))
print("Tickers with more than 22 bars:", sum(v > 22 for v in ticker_counts.values()))

print("\nLOWEST COVERAGE TICKERS:")
for ticker, count in sorted(ticker_counts.items(), key=lambda x: x[1])[:20]:
    print(ticker, count)

summary = {
    "news_batch_files": len(news_files),
    "news_records": news_rows,
    "unique_news_ids": len(news_ids),
    "duplicate_news_ids": duplicate_news,
    "invalid_news_timestamps": invalid_news_dates,
    "news_tickers": len(news_tickers),
    "news_dates": len(news_dates),
    "news_sources": dict(sources),
    "sip_batch_files": len(bar_files),
    "sip_records": bars,
    "sip_tickers": len(bar_tickers),
    "sip_dates": sorted(bar_dates),
    "duplicate_sip_ticker_dates": duplicate_bars,
    "invalid_sip_records": invalid_bars,
    "tickers_with_22_bars": sum(v == 22 for v in ticker_counts.values()),
    "tickers_with_fewer_than_22_bars": sum(v < 22 for v in ticker_counts.values()),
    "tickers_with_more_than_22_bars": sum(v > 22 for v in ticker_counts.values())
}

(report_dir / "alpaca_oct2023_final_quality.json").write_text(
    json.dumps(summary, indent=2), encoding="utf-8"
)

print("\nSaved:", report_dir / "alpaca_oct2023_final_quality.json")
print("\nQUALITY AUDIT COMPLETE")
