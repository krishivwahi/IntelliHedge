# IntelliHedge V2 — Stage 1: GDELT 2.0 GKG collection & evaluation

Data: The GDELT Project (https://www.gdeltproject.org/)

| File | Purpose |
|---|---|
| `gdelt_collector.py` | `check-archive` (verify live endpoints) and `download` (validated, resumable download) |
| `gdelt_parser.py` | zip → Parquet; keeps all 27 original fields + clearly separate derived columns |
| `gdelt_quality_analysis.py` | timestamp / duplicate / coverage metrics → JSON, Markdown, CSV |
| `tests/make_synthetic_gkg.py` | synthetic data for smoke-testing only (see `tests/TEST_RESULTS.md`) |
| `docs/GDELT_RESEARCH.md`, `docs/LICENSING_ASSESSMENT.md` | research and licence assessment |
| `STAGE1_STATUS.md` | what is done, what is blocked, what you must run |

## Install
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```
Python 3.10+. Outbound HTTPS/HTTP access to `data.gdeltproject.org` is required.

## Run order (October 2026 by default; all dates are UTC and configurable)
```bash
# 1. Verify the archive and October 2026 availability (writes archive_check.json)
python gdelt_collector.py check-archive --start 2026-10-01 --end 2026-10-31

# 2. Download + validate (≈2,976 files; safe to re-run, only missing/invalid files are fetched)
python gdelt_collector.py download --start 2026-10-01 --end 2026-10-31 --raw-dir data/raw
#    optional: --verify-md5 (checks master-list MD5 where an entry exists), --stream both (adds translingual), --workers 4

# 3. Parse (one Parquet per day; add --slim to drop bulky GCAM/XML columns, originals stay in data/raw)
python gdelt_parser.py --raw-dir data/raw --out-dir data/processed --start 2026-10-01 --end 2026-10-31

# 4. Quality analysis
python gdelt_quality_analysis.py --processed-dir data/processed --raw-dir data/raw \
       --start 2026-10-01 --end 2026-10-31 --out-dir reports
```
Each script runs independently; steps 3–4 only need the outputs of the previous step.

## Outputs
* `data/raw/YYYYMMDD/*.gkg.csv.zip` — untouched originals; `data/raw/manifest.csv` (status per slot: ok / cached / missing_404 / failed); `data/raw/download_summary.json` (missing days & slots)
* `data/processed/gkg_YYYYMMDD.parquet`, `parse_stats.csv` (lines, rows, quarantined malformed lines per file)
* `reports/quality_metrics.json`, `quality_report.md`, `records_per_day.csv`, `top_*.csv`, `missing_slots.csv`

## Notes
* Size: expect several GB of zips and tens of GB uncompressed for a month; use `--slim` if disk is tight.
* Files are validated (zip integrity, one non-empty CSV member, Content-Length match); invalid downloads are retried with backoff. HTTP 404 on a slot is confirmed once and then recorded as missing — never replaced with another period.
* The collector never reads the master list to decide what exists, because it may be stale.
* Attribution: any redistribution must cite the GDELT Project and link to https://www.gdeltproject.org/.
