# SEC EDGAR 8-K — Data Quality Report

**Collection period:** 2026-10-01 to 2026-10-31
**Status:** Real filing metadata collection and quality analysis completed.

## 1. Collection summary

- Primary filings: 5,061
- Original 8-K filings: 4,951
- Amended 8-K/A filings: 110
- Unique companies: 3,113
- Unique CIKs: 3,113
- Unique tickers: 3,699
- Filings with ticker information: 89.5673%

## 2. Timestamp analysis

| Timestamp source | Format | Missing | Precision |
|---|---|---:|---|
| Submissions API acceptanceDateTime | ISO-8601 with Z suffix | 0% | Seconds |
| SGML header ACCEPTANCE-DATETIME | YYYYMMDDHHMMSS, no timezone | 0% | Seconds |
| Filing index Accepted field | YYYY-MM-DD HH:MM:SS | 0% | Seconds |

### Timezone limitation

Timezone interpretation remains unresolved.

- Header timestamps have been evaluated under an Eastern-time hypothesis.
- API timestamps have been evaluated under a UTC hypothesis.
- The per-filing comparison preferred the API-as-UTC convention for all 5,061 records.
- The alternative API-as-Eastern hypothesis produced substantially more filing-date rule violations.

These diagnostics do not independently establish the authoritative timezone.

Both the raw timestamps and original timezone assumptions must be preserved. Do not silently label every timestamp as UTC or Eastern.

## 3. Duplicate analysis

| Metric | Result |
|---|---:|
| Daily-index lines across selected forms, including margin | 6,541 |
| Unique primary accessions | 5,061 |
| Duplicate accession rows in processed primary dataset | 0 |
| Multi-filer accessions | 103 |
| Duplicate daily-index lines across all forms | 1,517 |
| Duplicate daily-index line rate | 1.4546% |

The 1,517 index-line duplicates are not equivalent to duplicate primary filing records.

## 4. Coverage

- Observed filing-date range: 2026-10-01 to 2026-10-30.
- Expected business days: 21.
- Missing business days: 0.
- Unique companies: 3,113.
- Unique tickers: 3,699.
- Filings with ticker information: 89.5673%.
- 8-K filings: 4,951.
- 8-K/A filings: 110.
- Filings with item metadata: 5,061 (100%).
- Filings with at least one exhibit: 74.5307%.

## 5. Retrieval and document scope

| Component | Result |
|---|---|
| Submissions metadata | 5,061 / 5,061 |
| Filing headers | 5,061 / 5,061, including cached |
| Filing index pages | 5,061 / 5,061, including cached |
| Primary filing documents | Not attempted |
| Full-text extraction | Not attempted |

This collection is metadata-focused. It does not constitute a full-text filing corpus.

Exhibit metadata was parsed from the filing index pages.

## 6. Market-session analysis

Under the evaluated Eastern-time interpretation:

- After-hours: 2,743 filings.
- Pre-market: 1,623 filings.
- Regular session: 614 filings.
- Overnight: 81 filings.
- Outside regular session: 87.868%.

These classifications remain subject to the unresolved timezone interpretation.

## 7. Limitations

1. Acceptance timestamp timezone semantics remain unresolved.
2. Full primary filing documents were not downloaded.
3. Ticker information is missing for approximately 10.43% of filings.
4. Daily-index duplicate lines must be distinguished from duplicate accessions.
5. Filing date and acceptance timestamp are not interchangeable.

## Evidence

Detailed computed metrics are in `reports/quality_report.md` and `reports/quality_metrics.json`.

Licensing research is documented in `docs/LICENSING_ASSESSMENT.md`.

**Result:** Real SEC filing metadata was collected and evaluated. Full-document collection remains outside the completed scope.
