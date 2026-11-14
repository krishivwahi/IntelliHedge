
from pathlib import Path
import pandas as pd

DATA_DIR = Path("gdelt_stage1/data/processed")
OUTPUT_DIR = Path("gdelt_stage1/reports")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

columns = ["headline", "source_domain", "url", "record_ts"]

frames = []

for file in sorted(DATA_DIR.glob("gkg_202610*.parquet")):
    df = pd.read_parquet(file, columns=columns)
    df["headline_clean"] = (
        df["headline"]
        .fillna("")
        .str.strip()
        .str.lower()
    )
    df = df[df["headline_clean"] != ""]
    frames.append(df)

    print(f"Loaded {file.name}: {len(df):,} records")

data = pd.concat(frames, ignore_index=True)

# Find repeated headlines across all domains
counts = (
    data.groupby("headline_clean")
    .agg(
        record_count=("headline_clean", "size"),
        unique_domains=("source_domain", "nunique"),
        unique_urls=("url", "nunique"),
        headline=("headline", "first"),
    )
    .reset_index()
)

duplicates = counts[counts["record_count"] > 1]
top = duplicates.sort_values(
    "record_count", ascending=False
).head(50)

output = OUTPUT_DIR / "top_duplicate_headlines.csv"
top.to_csv(output, index=False)

print("\n===== DUPLICATE HEADLINE SUMMARY =====")
print(f"Records with headlines: {len(data):,}")
print(f"Unique headlines: {data['headline_clean'].nunique():,}")
print(f"Repeated headline groups: {len(duplicates):,}")

print("\n===== TOP 20 REPEATED HEADLINES =====")
print(
    top[[
        "record_count",
        "unique_domains",
        "unique_urls",
        "headline"
    ]].head(20).to_string(index=False)
)

print(f"\nSaved report: {output}")
