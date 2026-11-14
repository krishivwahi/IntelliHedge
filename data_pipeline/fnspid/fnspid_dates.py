"""Timestamp helpers. Original source strings remain in their original columns."""
from __future__ import annotations
import pandas as pd

def parse_date_series(values):
    # UTC is used only to obtain a comparable datetime representation.
    # Naive source timestamps are NOT proven UTC; preserve raw value and offset flag.
    raw=values.astype("string")
    return pd.to_datetime(raw,errors="coerce",utc=True,format="mixed")

def has_explicit_offset(values):
    raw=values.astype("string")
    return raw.str.contains(r"(?:Z|[+-]\d{2}:?\d{2})$",case=False,regex=True,na=False)

def normalize_ticker(values):
    return values.astype("string").str.strip().str.upper().replace({"":pd.NA,"NAN":pd.NA,"NONE":pd.NA})

def normalize_url(values):
    s=values.astype("string").str.strip()
    return s.str.replace(r"(?i)^http://","https://",regex=True).str.replace(r"[?#].*$","",regex=True).str.rstrip("/")
