# Test results — SYNTHETIC data only (NOT SEC results)

Command: `python -m unittest discover -s tests -v`  →  **Ran 26 tests, OK** (≈12 s, Linux, Python 3, pandas + pyarrow).
Not yet run on Windows by me; the code uses `pathlib`, `os.replace`, Windows-safe file names and `tzdata`.

The tests build an invented mini-EDGAR tree (`tests/synthetic_data/build_synthetic_sec.py`, companies named "SYNTHETIC … CORP") and serve it from a local
HTTP server (`tests/mock_sec_server.py`). They exercise the real collector → parser → quality-analysis code paths over HTTP. They prove the logic on planted
cases; they say nothing about sec.gov, real filings, or real data quality.

| Area | Planted case | Verified |
|---|---|---|
| Fair access | no/invalid e-mail in User-Agent | refused (`SystemExit`) |
| | every request | carries the declared User-Agent |
| | 20 calls from 4 threads at 10/s | ≥1.9 s, spacing ≥0.095 s |
| | `--rate 50` | clamped to 10 |
| | single HTTP 403 | all requests pause, retry succeeds (attempts=2) |
| | persistent 403 | run aborts (exit 3) after ≤3 requests |
| Selection | 8-K, 8-K/A, 10-Q, margin filing, weekend/no-index days | 6 primary, 1 margin, 10-Q excluded, amendment flagged |
| | co-filer listed under two CIKs | one row, `idx_row_count=2`, co-filer recorded |
| | filing only on an older submissions page | found via pagination |
| | no submissions record | primary document found via index page |
| Documents | 404 document | `not_found`, not counted as success |
| | empty (0-byte) document | `failed` ("empty body") |
| | re-run | no re-download of cached headers/pages/documents |
| Timestamps | API true UTC / API Eastern-labelled-Z / API absent | `api_true_utc` / `api_wallclock_equals_header_wallclock` / `unverifiable` |
| | accepted 18:00 ET, filed next day | gap 1 day, after-1730 flag, rule consistent, `after_hours` |
| | 10:15 ET | 14:15 UTC (EDT) |
| | filed after window, accepted inside | detected (`in_acceptance_window_et`) |
| | bad/short/garbage stamps | parsed to `None` |
| Content | items, titles, SIC, ticker, exchange, exhibit EX-99.1 | preserved |
| | HTML → text (style removed), items in text vs metadata | OK |
| Quality | duplicate documents by SHA-256 (ACME = ETA) | 1 redundant |
| | retrieval / text success | 66.6667 % (4 of 6) |
| | session distribution | regular 4, after_hours 1, pre_market 1 |
| | timezone hypothesis test | correct hypothesis scores 0 % violations |

History: the first run had 3 failures caused by wrong test expectations (BETA's document exists, so 4 not 3 documents; CSV float formatting). The code was unchanged; expectations were corrected.
