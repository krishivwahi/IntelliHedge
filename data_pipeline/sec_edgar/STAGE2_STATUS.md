# Stage 2 status — SEC EDGAR

| Completion criterion | State |
|---|---|
| Official endpoints researched | **Yes, documentation-level.** APIs, rate limit, User-Agent, paths, accession format, reuse policy read on official pages. Some layouts (daily-index file name/columns, header tags, index-page HTML) are recalled/third-party → `docs/SEC_RESEARCH.md` §8 |
| Endpoints verified live | **No — blocked.** Sandbox gets CONNECT tunnel 403 for sec.gov and data.sec.gov. Use `check-endpoints` |
| October 2026 availability checked | **No** (same blocker) |
| Filings collected | **None.** No real data was obtained |
| Quality metrics on real records | **None** |
| Raw / processed separated | Yes (`data/raw`, `data/processed`) |
| Collector + parser independent | Yes (tested on synthetic data) |
| Fair access followed | Implemented and tested against a mock: declared UA with required e-mail (none invented), ≤10 req/s global limiter, all-thread pause on 403/429, abort after repeated blocks |
| Licensing documented | Yes, from official pages |
| Synthetic tests pass | Yes — 26/26 (Linux). Not yet run on Windows |
| README allows independent execution | Yes |

## Needs you
1. Provide a real contact e-mail in the User-Agent (README).
2. Run README steps 1–5; send `endpoint_check.json`, `data/raw/manifests/collection_summary_*.json`, `reports/quality_metrics.json`.
3. Decide with counsel on redistribution of filing text.

## Unresolved questions the real run will answer
* Do the assumed endpoint layouts match live responses?
* Is `acceptanceDateTime` UTC, Eastern, or mixed in October 2026 (reported change ~2026-10-14)?
* How many 8-K / 8-K/A filings exist in the period, and what share of primary documents are retrievable?
