from pathlib import Path
from collections import Counter
from datetime import datetime
import json

source = Path("reports/alpaca_collection_oct2023/news_batches")
output = Path("reports/alpaca_collection_oct2023/cleaned")
output.mkdir(parents=True, exist_ok=True)

articles = {}

for file in source.glob("*.jsonl"):
    with open(file, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue

            row = json.loads(line)
            article_id = str(row.get("id"))

            if article_id not in articles:
                articles[article_id] = row
                articles[article_id]["symbols"] = list(
                    row.get("symbols") or []
                )
            else:
                existing = set(articles[article_id]["symbols"])
                existing.update(row.get("symbols") or [])
                articles[article_id]["symbols"] = sorted(existing)

clean = []

for row in articles.values():
    created = row.get("created_at")

    try:
        dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
    except Exception:
        continue

    if dt.year == 2023 and dt.month == 10:
        clean.append(row)

clean.sort(key=lambda x: (x.get("created_at", ""), str(x.get("id", ""))))

out_file = output / "alpaca_news_oct2023_clean.jsonl"

with open(out_file, "w", encoding="utf-8") as f:
    for row in clean:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

source_counts = Counter(r.get("source", "UNKNOWN") for r in clean)
ticker_set = {
    symbol
    for row in clean
    for symbol in (row.get("symbols") or [])
}

print("========== CLEAN NEWS DATASET ==========")
print("Raw records:", sum(1 for p in source.glob("*.jsonl") for _ in open(p, encoding="utf-8")))
print("Unique IDs before date filter:", len(articles))
print("October 2023 articles:", len(clean))
print("Unique tickers represented:", len(ticker_set))
print("Sources:", dict(source_counts))
print("Date range:",
      clean[0]["created_at"] if clean else None,
      "to",
      clean[-1]["created_at"] if clean else None)
print("Saved:", out_file.resolve())
print("CLEANING COMPLETE")
