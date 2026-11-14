# GDELT GKG — Data Quality Report

**Collection period:** 2026-10-01 to 2026-10-31
**Status:** Real-data collection, processing and quality analysis completed.

## Collection summary

- Total records analysed: 2,985,215
- Dates covered: 31/31
- 15-minute slots covered: 2,976/2,976
- Unique source domains: 12,172
- Language stream: English

## Timestamp analysis

- GKG V2.1DATE: 14-digit YYYYMMDDHHMMSS.
- All records matched their respective 15-minute file slots.
- V2.1DATE is therefore a collection/batch timestamp, not a reliable article publication timestamp.
- PAGE_PRECISEPUBTIMESTAMP coverage: 57.5684%.
- Missing PAGE_PRECISEPUBTIMESTAMP: 42.4316%.

The GDELT record timestamp is documented as UTC, but the data itself does not independently verify that timezone. Publication timestamps should be treated separately.

## Duplicate analysis

| Test | Redundant records | Duplicate rate |
|---|---:|---:|
| GKGRECORDID | 0 | 0% |
| All original fields | 0 | 0% |
| Original fields excluding record ID | 0 | 0% |
| Original URL | 0 | 0% |
| Normalized URL | 16,582 | 0.5555% |
| Domain + normalized headline | 127,552 | 4.2808% |
| Normalized headline | 1,125,220 | 37.7637% |

Repeated headlines may include syndicated stories and should not automatically be treated as exact duplicate articles.

## Coverage and field availability

- Observed period: 2026-10-01 to 2026-10-31.
- Missing dates: 0.
- Unique themes: 21,298.
- Unique persons: 1,606,729.
- Unique organisations: 950,621.
- Unique countries: 257.
- Headline presence: 100%.
- URL presence: 100%.
- Tone presence: 100%.
- Page publication timestamp presence: 57.5684%.

## Limitations

1. V2.1DATE represents the GDELT processing/file-slot time rather than article publication time.
2. PAGE_PRECISEPUBTIMESTAMP is missing from 42.4316% of records.
3. Normalized headline repetition is high and requires careful deduplication.
4. Publication-time accuracy cannot be established solely from record precision.

## Evidence

Detailed computed metrics are available in `reports/quality_report.md` and `reports/quality_metrics.json`.

**Result:** Real-data quality metrics have been computed for the October 2026 GDELT collection. This is not a synthetic-only analysis.
