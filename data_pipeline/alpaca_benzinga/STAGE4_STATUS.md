# Stage 4 Status — Alpaca / Benzinga

**Collection period:** October 1–31, 2023
**Status:** Historical news and SIP market-data collection and first-pass quality analysis completed.

## Completion criteria

| Criterion | State |
|---|---|
| Alpaca account and API authentication | Verified |
| Historical news endpoint | HTTP 200; October 2023 access confirmed |
| Historical SIP bars endpoint | HTTP 200; October 2023 access confirmed |
| Historical IEX and SIP comparison | Completed on five-ticker October 2026 sample |
| Real news records collected | 18,131 raw records across 53 batches |
| Unique news article IDs before date filtering | 12,037 |
| Clean October 2023 news articles | 12,025 |
| News source attribution | Benzinga for all 12,025 clean articles |
| Unique news tickers represented | 4,539 |
| SIP daily bars collected | 57,552 |
| SIP tickers | 2,616 |
| SIP trading dates | 22 |
| Duplicate SIP ticker-date records | 0 |
| Invalid SIP records | 0 |
| Cross-dataset ticker overlap analysis | Completed |
| Quality reports | Computed from collected records |

## News collection and cleaning

- 53 raw news batches collected.
- 18,131 raw records returned.
- 12,037 unique article IDs before date filtering.
- 6,094 repeated copies across ticker batches.
- All 12,037 unique records had an October 2023 updated_at timestamp.
- 12 unique articles had created_at timestamps outside October 2023.
- The cleaned dataset retains the 12,025 articles created during October 2023.
- Duplicate copies were merged by article ID, with associated ticker symbols combined.

## SIP market-data collection

- 53 SIP batches collected.
- 57,552 daily bars.
- 2,616 unique tickers.
- 22 trading dates, from October 2 through October 31, 2023.
- Every collected ticker had 22 bars.
- Zero duplicate ticker-date bars.
- Zero invalid bar records.

October 1, 2023 was a non-trading day.

## Cross-dataset ticker overlap

| Comparison | Shared tickers |
|---|---:|
| Alpaca news and FNSPID news | 1,987 |
| Alpaca news and SIP prices | 1,868 |
| FNSPID news and SIP prices | 2,616 |
| All three datasets | 1,868 |

## Provenance and limitations

1. News was collected through the Alpaca API. The source field identified Benzinga for all clean October articles. This is Benzinga-attributed news accessed through Alpaca, not an independently collected direct Benzinga feed.
2. Direct Benzinga API access was not obtained or tested.
3. The news query returned records updated during October. The final publication cohort was filtered using created_at.
4. The collector requested metadata without full article content. Full-text availability is not established.
5. API access does not independently establish redistribution, storage or model-training permissions. Review the applicable Alpaca and Benzinga terms before external use.
6. SIP is the selected market-data feed for this collection. The earlier IEX/SIP comparison was a separate five-ticker October 2026 audit.
7. Ticker overlap does not establish article-to-price alignment or news availability on every trading day.

## Evidence and outputs

- `reports/alpaca_audit/alpaca_oct2023_final_quality.json`
- `reports/alpaca_audit/final_oct2023_ticker_universe.csv`
- `reports/alpaca_audit/market_audit_oct2026.json`
- `reports/alpaca_audit/market_bars_oct2026.csv`

The original raw batches and cleaned JSONL collection are retained locally and are intentionally not included in this GitHub repository copy.

Research and usage limitations are documented in:
- `docs/ALPACA_RESEARCH.md`
- `docs/BENZINGA_RESEARCH.md`
- `docs/DATA_LIMITATIONS.md`
- `docs/LICENSING_ASSESSMENT.md`

**Stage 4 collection and first-pass quality evaluation: complete.**

Licensing verification and full-text availability remain limitations for downstream research use.
