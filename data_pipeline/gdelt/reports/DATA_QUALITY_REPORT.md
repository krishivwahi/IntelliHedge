# GDELT GKG Data-Quality Report — October 2026

**STATUS: NOT COMPUTED.** No real GDELT records could be downloaded in the build environment (network allowlist blocks `data.gdeltproject.org`). To avoid inventing numbers, every metric below is intentionally empty.

Running `python gdelt_quality_analysis.py ...` (README step 4) overwrites `reports/quality_report.md` and `quality_metrics.json` with computed values for the actual files. Use those, not this file.

| Metric | Value |
|---|---|
| Records collected | pending local run |
| Expected / present 15-min slots (2,976 expected) | pending |
| Missing dates / slots | pending |
| V2.1DATE missing % / invalid % | pending |
| % V2.1DATE equal to file slot; % with non-zero seconds | pending (tests the batch-time hypothesis) |
| Page publication timestamp coverage % | pending |
| Record − publication delay percentiles | pending |
| Exact duplicate rows; duplicate URLs (raw/normalised); duplicate headlines | pending |
| Unique domains; language, theme, person, org, country distributions | pending |

Pipeline correctness was checked on synthetic data only: `tests/TEST_RESULTS.md`.
