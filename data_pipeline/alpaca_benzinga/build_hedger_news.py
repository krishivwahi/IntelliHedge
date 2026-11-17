
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


EXPECTED_ROWS = 12_025
COLUMNS = ["id", "source", "text", "t_pub", "t_seen"]


def parse_utc(value):
    """Parse a timestamp and return timezone-aware UTC."""
    if value is None or not str(value).strip():
        return pd.NaT

    return pd.to_datetime(value, utc=True, errors="coerce")



def transform_records(batch_records):
    """
    Convert raw Alpaca articles into hedger rows.
    Deduplicate by ID using earliest created_at, then retain October 2023.
    """
    rows = []

    for item in batch_records:
        article = item["article"]
        article_id = article.get("id")

        rows.append({
            "id": str(article_id).strip() if article_id is not None else "",
            "source": "Benzinga",
            "text": str(article.get("headline") or "").strip(),
            "t_pub": parse_utc(article.get("created_at")),
            "t_seen": parse_utc(item.get("t_seen")),
        })

    df = pd.DataFrame(rows, columns=COLUMNS)

    # Check required fields before filtering or deduplication.
    for column in ["id", "text"]:
        if df[column].isna().any() or df[column].str.strip().eq("").any():
            raise ValueError(f"Missing required values in {column}")

    for column in ["t_pub", "t_seen"]:
        if df[column].isna().any():
            raise ValueError(f"Missing or invalid timestamps in {column}")

    raw_count = len(df)

    # Keep the earliest created_at for each article ID.
    df = df.sort_values(
        ["t_pub", "t_seen"],
        kind="stable"
    )
    df = df.drop_duplicates(subset="id", keep="first")

    unique_count = len(df)

    # Filter after deduplication.
    start = pd.Timestamp("2023-10-01T00:00:00Z")
    end = pd.Timestamp("2023-11-01T00:00:00Z")

    before_filter = len(df)
    df = df[(df["t_pub"] >= start) & (df["t_pub"] < end)]
    excluded_count = before_filter - len(df)

    df = df.reset_index(drop=True)

    df.attrs["raw_count"] = raw_count
    df.attrs["unique_count"] = unique_count
    df.attrs["excluded_outside_october"] = excluded_count

    print(f"Raw records: {raw_count:,}")
    print(f"Unique IDs after deduplication: {unique_count:,}")
    print(f"Unique records outside October: {excluded_count:,}")
    print(f"Final October records: {len(df):,}")

    return df



def validate_dataset(df):
    """Print validation results and stop if a required check fails."""

    required = ["id", "text", "t_pub", "t_seen"]

    for column in required:
        missing = int(
            df[column].isna().sum()
            if column in ["t_pub", "t_seen"]
            else df[column].fillna("").astype(str).str.strip().eq("").sum()
        )

        print(f"Missing {column}: {missing}")

        if missing:
            raise ValueError(f"Validation failed: missing {column}")

    duplicate_ids = int(df["id"].duplicated().sum())
    print(f"Duplicate IDs: {duplicate_ids}")

    if duplicate_ids:
        raise ValueError("Validation failed: IDs are not unique")

    # Ensure both timestamp columns are timezone-aware UTC.
    for column in ["t_pub", "t_seen"]:
        if not isinstance(df[column].dtype, pd.DatetimeTZDtype):
            raise ValueError(f"{column} is not timezone-aware")

        if str(df[column].dt.tz) != "UTC":
            raise ValueError(f"{column} is not in UTC")

    print("Timezone validation: PASS (UTC, timezone-aware)")

    start = pd.Timestamp("2023-10-01T00:00:00Z")
    end = pd.Timestamp("2023-11-01T00:00:00Z")

    outside_october = int(
        ((df["t_pub"] < start) | (df["t_pub"] >= end)).sum()
    )

    print(f"Publication timestamps outside October 2023: {outside_october}")

    if outside_october:
        raise ValueError("Validation failed: t_pub outside October 2023")

    late_publication = int((df["t_pub"] > df["t_seen"]).sum())
    print(f"t_pub later than t_seen: {late_publication}")

    if late_publication:
        raise ValueError("Validation failed: publication after observation")

    print(f"Unique article rows: {len(df):,}")
    print(f"Expected approximate rows: {EXPECTED_ROWS:,}")
    print(f"Difference from expected: {len(df) - EXPECTED_ROWS:+,}")

    if abs(len(df) - EXPECTED_ROWS) > 500:
        print(
            "WARNING: Row count differs substantially from expectation. "
            "Possible causes include missing batches, source coverage, "
            "or duplicate-ID removal. Investigate before using the output."
        )

    print("\nAll mandatory validation checks passed.")


def load_batches(input_dir):
    """Read all original news batches and attach batch-level t_seen."""

    batch_files = sorted(input_dir.glob("news_*.jsonl"))

    if not batch_files:
        raise FileNotFoundError(f"No news_*.jsonl files found in {input_dir}")

    print(f"Found {len(batch_files)} batch files.")

    records = []

    for batch_file in batch_files:
        # Filesystem modification time, interpreted as UTC.
        t_seen = datetime.fromtimestamp(
            batch_file.stat().st_mtime,
            tz=timezone.utc
        )

        with batch_file.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                if not line.strip():
                    continue

                try:
                    article = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Invalid JSON in {batch_file.name}, "
                        f"line {line_number}: {exc}"
                    ) from exc

                records.append({
                    "article": article,
                    "t_seen": t_seen,
                })

        print(f"Read {batch_file.name}: {t_seen.isoformat()}")

    return records


def main():
    parser = argparse.ArgumentParser(
        description="Build the October 2023 Alpaca news table for the hedger."
    )

    parser.add_argument(
        "--input-dir",
        required=True,
        help="Folder containing the original news_XXX.jsonl batches."
    )

    parser.add_argument(
        "--output",
        default="data_pipeline/alpaca_benzinga/hedger_news_oct2023.parquet",
        help="Output Parquet path."
    )

    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_path = Path(args.output)

    if not input_dir.is_dir():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    batch_records = load_batches(input_dir)

    print(f"\nRaw article records: {len(batch_records):,}")

    df = transform_records(batch_records)

    print(f"Rows after ID deduplication: {len(df):,}\n")

    validate_dataset(df)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False, engine="pyarrow")

    print(f"\nParquet successfully written: {output_path.resolve()}")
    print(f"Output columns: {list(df.columns)}")


if __name__ == "__main__":
    main()
