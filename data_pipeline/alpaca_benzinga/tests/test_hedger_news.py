
import pandas as pd

from data_pipeline.alpaca_benzinga.build_hedger_news import transform_records


def test_duplicate_handling_and_utc_timestamps():
    records = [
        {
            "article": {
                "id": 101,
                "headline": "Later version",
                "created_at": "2023-10-02T10:00:00Z",
            },
            "t_seen": "2023-11-13T23:40:00Z",
        },
        {
            "article": {
                "id": 101,
                "headline": "Earliest version",
                "created_at": "2023-10-02T09:00:00Z",
            },
            "t_seen": "2023-11-13T23:39:00Z",
        },
        {
            "article": {
                "id": 102,
                "headline": "Timezone test",
                "created_at": "2023-10-03T14:30:00+05:30",
            },
            "t_seen": "2023-11-13T23:41:00+00:00",
        },
        {
            "article": {
                "id": 103,
                "headline": "Another article",
                "created_at": "2023-10-04T12:00:00-04:00",
            },
            "t_seen": "2023-11-13T23:42:00Z",
        },
    ]

    df = transform_records(records)

    assert len(df) == 3
    assert df["id"].is_unique

    # Earliest created_at wins for duplicate ID 101.
    row = df[df["id"] == "101"].iloc[0]
    assert row["text"] == "Earliest version"
    assert row["t_pub"] == pd.Timestamp("2023-10-02T09:00:00Z")

    # Different source timezones are converted to UTC.
    row = df[df["id"] == "102"].iloc[0]
    assert row["t_pub"] == pd.Timestamp("2023-10-03T09:00:00Z")

    row = df[df["id"] == "103"].iloc[0]
    assert row["t_pub"] == pd.Timestamp("2023-10-04T16:00:00Z")

    assert str(df["t_pub"].dt.tz) == "UTC"
    assert str(df["t_seen"].dt.tz) == "UTC"
