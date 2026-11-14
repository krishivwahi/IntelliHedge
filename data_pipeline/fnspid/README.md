# IntelliHedge V2 — Stage 3: FNSPID

**Role:** Teammate B — News/Data Engineer
**Scope:** source inspection, reproducible downloads, chunked parsing, source-separated quality analysis.
**Python:** 3.10+; Windows PowerShell supported.

## Important status

This ZIP contains the implementation, documentation and synthetic tests. **It does not contain FNSPID source data and does not claim that real records have been collected or quality metrics computed.** The complete news files are very large; inspect the source metadata before downloading.

The upstream paper reports 15.7M news records and 29.7M price records for 4,775 S&P 500 companies over 1999–2023. These are paper-level figures, not verified local-file counts. The two news CSVs and the stock-price ZIP are kept separate.

## Install (PowerShell)

```powershell
cd FNSPID
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 1. Inspect remote file metadata — no large download

```powershell
python fnspid_collector.py inspect
```

Writes `data/raw/manifests/source_inventory.json`. It probes Hugging Face using a one-byte range request and records remote size / headers where supplied. Network access is required.

## 2. Download only if you accept the full-file size

```powershell
python fnspid_collector.py download --source all_external
python fnspid_collector.py download --source nasdaq_external
python fnspid_collector.py download --source stock_prices
```

Downloads are resumable via `.part` files where the server honours HTTP Range. A download manifest with SHA-256 is written after successful completion. The news CSVs are not guaranteed to be sorted by date, and the collector does not pretend a one-month range can be fetched by byte range. Filtering is performed locally after download.

## 3. Parse/filter news

```powershell
python fnspid_parser.py --news data/raw/news/All_external.csv data/raw/news/nasdaq_exteral_data.csv --start 2023-10-01 --end 2023-10-31 --format parquet
```

The files are processed separately. Outputs go to `data/processed/news/`. For lower memory use, change `--chunksize 25000`. To parse all rows, omit `--start` and `--end`.

## 4. Extract stock price archive

```powershell
python fnspid_parser.py --stock-zip data/raw/stock_prices/full_history.zip
```

This extracts CSV/TXT members to `data/processed/stock_prices/` and records the ZIP member inventory. It does not merge news with prices.

## 5. Quality analysis

```powershell
python fnspid_quality_analysis.py data/raw/news/All_external.csv data/raw/news/nasdaq_exteral_data.csv --out-dir reports
```

The report computes per-file row/date/ticker/publisher/author/URL counts and missingness. Keep the two outputs separate. Cross-file overlap and stock/news time alignment require a real-data run and are not inferred from synthetic tests.

## Tests

```powershell
python -m unittest discover -s tests -v
```

Tests use invented records only. They validate parser transformations and date filtering; test results are not dataset findings.

## Expected layout

- `data/raw/news/` — original news CSVs, untouched
- `data/raw/stock_prices/` — original price ZIP
- `data/raw/manifests/` — source inventory and download manifest
- `data/processed/` — derived outputs
- `data/samples/` — optional user-approved samples; do not redistribute article text
- `docs/`, `reports/`, `tests/` — research, assessments and validation

## Caveats

- Date values are retained in original columns. `ih_timestamp_parsed_utc_comparable` is a UTC-normalized computational field; naive inputs are treated as UTC for comparability only, not as evidence that the source meant UTC. `ih_timestamp_had_explicit_offset` flags strings that carried an explicit offset. Always preserve and inspect the raw date column.
- Do not assume dates represent publication instants in UTC. Verify source semantics before intraday backtests.
- Stock prices and news require market-calendar-aware alignment. Do not join on calendar date alone.
- The parser preserves source columns and adds `ih_*` derived fields.
- The quality script currently computes within-file URL/headline repeats. A cross-source exact/near-duplicate assessment should be run after both files are locally available.
- Article text may be subject to publisher copyright independently of the dataset licence. Do not republish raw articles without rights review.
