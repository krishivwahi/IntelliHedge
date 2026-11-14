
from pathlib import Path
import pandas as pd

DATA_DIR = Path("gdelt_stage1/data/processed")
OUTPUT = Path("gdelt_stage1/reports/duplicate_samples.csv")

targets = [
    "Targeted News Service",
    "China Daily Website - Connecting China Connecting the World",
    "Subscribe to the Cairns Post",
    "Deadline",
    "Switching to Samsung Galaxy? Here's Why It's Now Easier Than Ever.",
]

frames = []

for file in sorted(DATA_DIR.glob("gkg_202610*.parquet")):
    df = pd.read_parquet(
        file,
        columns=["headline", "source_domain", "url", "record_ts"]
    )
    frames.append(df[df["headline"].isin(targets)])

result = pd.concat(frames, ignore_index=True)

result.to_csv(OUTPUT, index=False)

for headline in targets:
    group = result[result["headline"] == headline]
    print(f"\n===== {headline} =====")
    print(f"Records: {len(group):,}")
    print(group[["source_domain", "url"]].head(5).to_string(index=False))

print(f"\nSaved samples to: {OUTPUT}")
