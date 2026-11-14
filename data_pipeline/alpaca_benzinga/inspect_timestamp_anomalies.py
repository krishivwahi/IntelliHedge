
from pathlib import Path
import pandas as pd

DATA_DIR = Path("gdelt_stage1/data/processed")
OUTPUT_DIR = Path("gdelt_stage1/reports")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

columns = [
    "GKGRECORDID",
    "record_ts",
    "page_pub_ts",
    "page_pub_ts_raw",
    "headline",
    "url",
    "source_domain",
]

total_pairs = 0
total_later = 0
anomaly_samples = []

for file in sorted(DATA_DIR.glob("gkg_202610*.parquet")):
    df = pd.read_parquet(file, columns=columns)

    record_time = pd.to_datetime(df["record_ts"], utc=True, errors="coerce")
    publication_time = pd.to_datetime(
        df["page_pub_ts"], utc=True, errors="coerce"
    )

    valid = record_time.notna() & publication_time.notna()
    anomalies = valid & (publication_time > record_time)

    total_pairs += int(valid.sum())
    total_later += int(anomalies.sum())

    if anomalies.any():
        sample = df.loc[anomalies, columns].copy()
        sample["delay_minutes"] = (
            publication_time[anomalies] - record_time[anomalies]
        ).dt.total_seconds() / 60

        anomaly_samples.append(sample)

    print(
        f"{file.name}: "
        f"{int(valid.sum()):,} timestamp pairs, "
        f"{int(anomalies.sum()):,} later publication times"
    )

percentage = (
    total_later / total_pairs * 100 if total_pairs else 0
)

print("\n===== TIMESTAMP ANOMALY SUMMARY =====")
print(f"Valid timestamp pairs: {total_pairs:,}")
print(f"Publication after record time: {total_later:,}")
print(f"Percentage: {percentage:.4f}%")

if anomaly_samples:
    result = pd.concat(anomaly_samples, ignore_index=True)
    result.to_csv(
        OUTPUT_DIR / "timestamp_anomalies.csv",
        index=False
    )
    print(f"Saved {len(result):,} anomalies to timestamp_anomalies.csv")
else:
    print("No timestamp anomalies found.")
