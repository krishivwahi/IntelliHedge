# Stage 3 Status — FNSPID

**Collection period:** October 1–31, 2023
**Status:** Core NASDAQ news and historical stock-price collection, processing and first-pass quality evaluation completed.

## 1. Completion criteria

| Criterion | State |
|---|---|
| Research paper and authors' repository identified | Complete |
| Hugging Face source inventory inspected | Complete |
| NASDAQ external-news file downloaded | Complete |
| Historical stock-price ZIP downloaded | Complete |
| Stock-price ZIP integrity | PASS |
| Stock CSV files extracted | 7,693 |
| Full NASDAQ news-file audit | Complete |
| October 2023 news subset extracted | 89,036 records |
| October news dates validated | 31/31 dates |
| URL-ticker deduplication | Complete |
| Duplicate and conflict audit | Complete |
| Stock-price quality audit | Complete |
| October news-to-stock matching | Complete |
| Local FNSPID tests | 7 passed in FNSPID suite; repository-wide rerun pending |
| Licensing assessment | Documented; unresolved |

## 2. Source collection

### NASDAQ external news

- Source: Stock_news/nasdaq_exteral_data.csv
- Downloaded size: approximately 23.23 GB.
- Full-file audit: 15,549,299 valid dated records.
- October 2023 subset extracted and validated.

### Historical stock prices

- Source: Stock_price/full_history.zip
- Downloaded size: approximately 589.5 MB.
- ZIP integrity check: PASS.
- Extracted stock CSV files: 7,693.
- All 7,693 files passed the stock-quality audit.

### Not collected

- Stock_news/All_external.csv (approximately 5.73 GB) was inspected remotely but not downloaded.
- Its incremental value and overlap with the NASDAQ external-news file remain unassessed.

## 3. October 2023 news quality

- Extracted records: 89,036.
- Unique tickers: 2,825.
- Unique URLs: 21,584.
- Repeated URL occurrences: 67,452.
- Repeated headline occurrences: 68,332.
- Missing publisher values: 100%.
- Missing author values: 100%.
- Missing article text: 1 record.
- Invalid dates: 0.
- All 31 calendar dates represented.

### Deduplication

The cleaned dataset retains the first record for each URL-ticker pair.

| Metric | Result |
|---|---:|
| Original rows | 89,036 |
| Cleaned rows | 88,959 |
| Rows removed | 77 |
| Duplicate URL-ticker groups | 77 |
| Groups with differing columns | 77 |
| Groups with differing LSA summaries | 3 |
| Conflict rows preserved for review | 6 |

Canonical articles and article-ticker associations should remain separate in downstream integration.

## 4. Stock-price quality

- Total price rows audited: 29,677,722.
- October 2023 price rows: 98,025.
- Tickers with October prices: 4,458.
- Invalid dates: 0.
- Duplicate dates reported: 0.
- Failed files: 0.
- Date range: 1962-01-02 to 2023-12-28.

The audit reported 257 missing values in each of volume, open, high, low, close and adjusted close. A missing-data policy remains necessary.

## 5. News-to-stock alignment

| Metric | Result |
|---|---:|
| October news tickers | 2,825 |
| Stock tickers with October prices | 4,458 |
| Matched news tickers | 2,619 |
| News tickers without October prices | 206 |
| Actual ticker match rate | 92.71% |

The 206 unmatched tickers remain documented in the exception list.

## 6. Timestamp limitations

For the October 2023 subset:

- 89,036/89,036 original Date values contain a literal UTC suffix.
- Every record has a time-of-day of 00:00:00.
- The observed granularity is daily, not intraday.
- The underlying timestamp-generation methodology and publication-time accuracy remain unverified.

The parser preserves original values and creates a separate comparable timestamp. For other source records without an explicit timezone marker, UTC normalization is a software assumption, not verified source metadata.

Preserve original timestamps and do not use the October date values for intraday event ordering.

## 7. Licensing and source limitations

1. FNSPID licensing information remains unresolved.
2. Do not assume commercial-use or redistribution rights.
3. The supplemental All_external.csv source was not downloaded.
4. Publisher and author fields are entirely missing in the October news subset.
5. The 206 unmatched tickers and stock missing values need documented handling.
6. Three summary-conflict groups require review.
7. No predictive performance or model validity has been established by this data-procurement work.

## 8. Evidence and reports

- reports/IntelliHedge_V2_Dataset_3_Completion_Report.md
- reports/fnspid_nasdaq_quality/quality_metrics.json
- reports/fnspid_oct2023_quality/quality_metrics.json
- reports/TIMESTAMP_ANALYSIS.md
- reports/fnspid_stock_quality/stock_quality_metrics.json
- reports/fnspid_alignment/
- docs/LICENSING_ASSESSMENT.md
- tests/TEST_RESULTS.md

**Stage 3 core NASDAQ news and stock-price collection and initial evaluation: complete.**

Supplemental source collection, licensing resolution, verification of timestamp-generation methodology and publication-time accuracy, missing-data policy and downstream model integration remain outstanding.
