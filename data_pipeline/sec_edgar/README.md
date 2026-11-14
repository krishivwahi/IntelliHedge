# IntelliHedge V2 — Stage 2: SEC EDGAR Form 8-K collection & evaluation

Python 3.10+, Windows / macOS / Linux. Source: U.S. Securities and Exchange Commission, EDGAR (https://www.sec.gov/edgar).

> **Status:** the pipeline was tested only against a local mock server with synthetic data (26 tests pass). It has **not** been run against sec.gov
> (the build sandbox could not reach it). Run steps 1–2 below first; see `STAGE2_STATUS.md`.

| File | Purpose |
|---|---|
| `sec_edgar_collector.py` | `check-endpoints` and `collect` (index → submissions → headers → index pages → primary documents) |
| `sec_edgar_parser.py` | raw → `data/processed/*.parquet|csv` + extracted text |
| `sec_edgar_quality_analysis.py` | timestamp / duplicate / coverage / retrieval / session metrics → `reports/` |
| `docs/SEC_RESEARCH.md`, `docs/LICENSING_ASSESSMENT.md` | verified research and licence findings |
| `tests/` | synthetic fixtures, mock SEC server, 26 tests, `TEST_RESULTS.md` |

## Install
```bat
python -m venv .venv
.venv\Scripts\activate            :: macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt   :: includes tzdata (needed for US Eastern time on Windows)
```

## SEC fair access — set YOUR contact address (nothing is pre-filled)
SEC requires a declared User-Agent with a contact e-mail; max 10 requests/second in total.
```bat
:: cmd.exe
set SEC_EDGAR_USER_AGENT=IntelliHedge-Research your.name@yourdomain.com
```
```powershell
# PowerShell
$env:SEC_EDGAR_USER_AGENT = "IntelliHedge-Research your.name@yourdomain.com"
```
(or pass `--user-agent "..."`). The collector refuses to start without an e-mail address, defaults to 6 requests/s (hard cap 10), pauses **all** threads on HTTP 403/429 and aborts after 5 consecutive blocks.

## Run order (October 2026 8-K / 8-K/A by default; dates and forms are configurable)
```bat
:: 1. Probe the endpoints once (~6 requests). Writes endpoint_check.json
python sec_edgar_collector.py check-endpoints --start 2026-10-01

:: 2. Metadata-only dry run first (no documents) - see how many filings there are
python sec_edgar_collector.py collect --start 2026-10-01 --end 2026-10-31 --skip-documents

:: 3. Full collection (re-runnable; cached files are skipped)
python sec_edgar_collector.py collect --start 2026-10-01 --end 2026-10-31

:: 4. Parse
python sec_edgar_parser.py --data-root data --start 2026-10-01 --end 2026-10-31

:: 5. Quality analysis
python sec_edgar_quality_analysis.py --data-root data --out-dir reports --start 2026-10-01 --end 2026-10-31
```
Request budget ≈ 3 per filing (header, index page, primary document) + 1 per distinct company + ~1 per day. At the default 6 req/s, N filings take ≈ N/2 seconds. Check N in `data/raw/manifests/filings_selected.csv` after step 2.

Options: `--forms 8-K,8-K/A` (exact match; other forms go to `filings_other`), `--rate`, `--workers`, `--margin-days` (extra days after `--end` whose headers are fetched so filings *accepted* inside the window but *dated* after it are identified), `--max-filings N` (testing), `--format csv|parquet` (parser).

## Output layout
```
data/raw/metadata/daily-index/YYYY/QTRn/  master.*.idx, index.json      (original SEC files, untouched)
data/raw/metadata/submissions/            CIK##########.json (+ older pages)
data/raw/metadata/headers/                <accession>.hdr.sgml
data/raw/metadata/index_pages/            <accession>-index.html
data/raw/filings/<cik>/<accession-no-dashes>/<primary document>
data/raw/manifests/                       manifest.csv (every request: success|skipped_cached|not_found|failed|no_reference),
                                          filings_selected.csv, index_form_counts.json, collection_summary_<run>.json
data/processed/                           filings_primary, filings_margin, filings_other, exhibits (+ text/<accession>.txt)
reports/                                  quality_report.md, quality_metrics.json, *.csv
```
Column prefixes in processed files: `idx_` daily index · `sub_` submissions API · `hdr_` SGML header · `page_` index page; unprefixed columns are derived and documented in the parser docstring.

## Tests (synthetic only)
```bat
python -m unittest discover -s tests -v
```

## Things to know
* **Timestamps:** filing date ≠ acceptance time. The timezone of the API field `acceptanceDateTime` is unresolved, and third-party reports describe a convention change around 2026-10-14. The parser keeps raw values, compares API vs header per filing and records the result (`acceptance_convention`); the quality report tests the hypotheses. Read `docs/SEC_RESEARCH.md` §3 before using acceptance times for trading research.
* Failed / missing documents are never counted as collected: see `primary_doc_status` and the manifest.
* A missing daily index on a business day is reported (`expected_business_days_without_index`); a 404 is never replaced by another date.
* Attribution/licence: `docs/LICENSING_ASSESSMENT.md`. Keep raw filing text internal unless counsel approves redistribution.
