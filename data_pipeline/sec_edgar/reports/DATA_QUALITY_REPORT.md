# SEC EDGAR 8-K Data-Quality Report — October 2026

**STATUS: NOT COMPUTED.** No real SEC records could be collected in the build environment (www.sec.gov and data.sec.gov are unreachable from it).
Every value below is deliberately empty; none is estimated.

Running README steps 1–5 overwrites `reports/quality_report.md` and `reports/quality_metrics.json` with values computed from the real files. Use those.

| Metric | Value |
|---|---|
| Filings expected (unique 8-K / 8-K/A accessions in the Oct 2026 daily indexes) | pending local run |
| Filings with metadata collected | pending |
| Primary documents retrieved / failed / not found | pending |
| Text extraction success | pending |
| Missing business days (no daily index) | pending |
| Acceptance timestamp missing % / invalid % (API, header, index page) | pending |
| Filing date − acceptance date distribution | pending |
| Timezone hypothesis test (header = ET; API = UTC; API = ET) | pending — decides which acceptance time is trustworthy |
| Mixed API conventions by day (around 2026-10-14) | pending (`convention_by_day.csv`) |
| Duplicate accessions / URLs / documents; originals vs amendments | pending |
| Unique companies / CIKs / tickers; item and SIC distributions | pending |
| Session distribution (pre / regular / after-hours / overnight) | pending |

Pipeline logic was verified on synthetic data only: `tests/TEST_RESULTS.md`.
