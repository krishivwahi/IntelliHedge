# IntelliHedge V2 --- Dataset 3 Completion Report

## FNSPID Financial News and Stock-Price Data

**Status:** Core collection and initial evaluation completed; several
integration-readiness items remain.\
**Target analysis period:** October 1--31, 2023\
**Source:** [FNSPID on Hugging
Face](https://huggingface.co/datasets/Zihan1004/FNSPID)

## 1. Executive summary

The FNSPID NASDAQ external-news file and historical stock-price ZIP were
downloaded and inspected. The October 2023 news subset was extracted,
validated, quality-audited, and deduplicated at the URL--ticker
association level. All 7,693 extracted stock CSV files were audited, and
October news tickers were matched against tickers with October price
observations.

The observed October news-to-stock ticker match rate is **92.71% (2,619
of 2,825 news tickers)**.

This is a substantial data-procurement and initial-quality milestone. It
is **not yet a full model-ready sign-off**: the 206 unmatched tickers,
price-field missing values, three conflicting summary groups, source
licensing, and the optional `All_external.csv` source still require
documented decisions.

## 2. Source collection and inventory

### NASDAQ external news

-   Source file: `Stock_news/nasdaq_exteral_data.csv`
-   Downloaded size: **23,232,979,597 bytes** (approximately 23.23 GB)
-   Download completed and source file retained.
-   Full-file audit processed **15,549,299** valid dated records.
-   The October 2023 subset was extracted to a separate processed file.

### Historical stock prices

-   Source file: `Stock_price/full_history.zip`
-   Downloaded size: **589,525,596 bytes** (approximately 589.5 MB)
-   ZIP integrity check: PASS.
-   Extracted stock CSV files: **7,693**.
-   The original ZIP was retained.

### Not collected

-   `Stock_news/All_external.csv` (approximately 5.73 GB) was inspected
    remotely but **not downloaded**. Its incremental value and overlap
    with the NASDAQ external file have not yet been assessed.

## 3. Full NASDAQ news-file date audit

  Metric                                      Result
  ------------------------------------- ------------
  Valid dated records                     15,549,299
  Records before 1999                              6
  Records from 2024 onward                        70
  Records within 1999--2023               15,549,223
  Invalid dates reported by the audit              0

The 1969-12-31 record inspected was a Zacks headline about Montpelier Re
Holdings Ltd. (MRH). Its timestamp is suspicious and should be treated
as an unresolved date anomaly, not silently corrected. The pre-1999
records included historical Russian-language archive material. The 70
records from 2024 onward are outside the intended 1999--2023 period.

## 4. October 2023 news extraction and validation

Output file:

`data/processed/news_oct2023/news/nasdaq_exteral_data_2023-10-01_2023-10-31.csv`

  Validation                          Result
  ---------------- -------------------------
  Extracted rows                      89,036
  Earliest date      2023-10-01 00:00:00 UTC
  Latest date        2023-10-31 00:00:00 UTC
  Unique dates                            31
  Invalid dates                            0

All 31 calendar dates in October were represented.

## 5. October news quality findings

  Metric                                                                    Result
  ---------------------------------------------------- ---------------------------
  Rows                                                                      89,036
  Unique tickers                                                             2,825
  Unique URLs                                                               21,584
  Repeated URL occurrences                                                  67,452
  Repeated headline occurrences                                             68,332
  Exact duplicate rows reported by the initial audit                             0
  Missing publisher values                                           89,036 (100%)
  Missing author values                                              89,036 (100%)
  Missing article text                                   1 (approximately 0.0011%)
  Invalid dates                                                                  0

Publisher and author fields are entirely unavailable in this subset, so
publisher- and author-level analysis cannot be performed from these
columns.

Repeated URLs were investigated. Many are legitimate
one-article-to-many-ticker associations: - 21,584 unique URLs. - 7,766
URLs associated with multiple tickers. - 13,818 URLs associated with one
ticker. - Maximum observed tickers associated with one URL: 48. - 88,959
unique URL--ticker pairs from 89,036 rows. - 77 repeated URL--ticker
pairs, involving 154 rows.

### Deduplication performed

The cleaned dataset was created by retaining the first row for each
`(Url, Stock_symbol)` pair.

Output folder: `data/processed/news_oct2023/cleaned/`

Files created: - `news_oct2023_deduplicated.csv` -
`duplicate_pairs_audit.csv` - `conflicting_summary_records.csv`

  Metric                                       Result
  ------------------------------------------ --------
  Original rows                                89,036
  Cleaned rows                                 88,959
  Rows removed                                     77
  Duplicate URL--ticker groups                     77
  Groups with differing columns                    77
  Groups where `Lsa_summary` also differed          3
  Rows preserved in conflict audit                  6

The `Unnamed: 0` source-index column differed in all 77 groups. In three
groups, `Lsa_summary` also differed. The six rows from those three
groups were preserved in `conflicting_summary_records.csv`. The cleaned
file retains the first row per URL--ticker pair; therefore, the conflict
audit must be consulted if summary-level fidelity matters. The original
extracted CSV remains unchanged.

**Data-model recommendation:** represent canonical articles separately
from article--ticker associations. Do not treat every repeated URL as a
duplicate article.

## 6. Stock-price quality audit

All stock CSV files under `data/processed/stock_prices` were scanned.

  Metric                                                Result
  --------------------------------- --------------------------
  CSV files found                                        7,693
  Valid files                                            7,693
  Failed files                                               0
  Total price rows                                  29,677,722
  October 2023 price rows                               98,025
  Files/tickers with October data                        4,458
  Invalid dates                                              0
  Duplicate dates reported                                   0
  Date range                          1962-01-02 to 2023-12-28

The audit reported 257 missing values in each of the following columns:
`volume`, `open`, `high`, `low`, `close`, and `adj_close`. These values
require a documented missing-data policy before model training. The
audit did not establish whether all 257 missing values occur on the same
rows.

Report generated locally:
`reports/fnspid_stock_quality/stock_quality_metrics.json`

## 7. News-to-stock ticker alignment

The first filename-only comparison found 2,807 ticker-name matches out
of 2,825 news tickers. That was not the appropriate final coverage
measure because it included stock files without October observations.

The corrected comparison used only stock tickers with October 2023 price
data:

  Metric                                      Result
  ------------------------------------- ------------
  Unique October news tickers                  2,825
  Stock tickers with October data              4,458
  Matched news tickers                         2,619
  News tickers without October prices            206
  Actual ticker match rate                **92.71%**

The 206 unmatched symbols should be retained in an exception list and
investigated if needed. Possible explanations include delisted
securities, non-common-stock instruments, symbol changes, or naming
mismatches; these explanations have not been individually verified.

## 8. Current deliverables

The following local outputs have been created: -
`data/raw/stock_prices/full_history.zip` -
`data/processed/stock_prices/` --- extracted per-ticker stock CSV
files - `data/raw/news/nasdaq_exteral_data.csv` -
`data/processed/news_oct2023/news/nasdaq_exteral_data_2023-10-01_2023-10-31.csv` -
`data/processed/news_oct2023/cleaned/news_oct2023_deduplicated.csv` -
`data/processed/news_oct2023/cleaned/duplicate_pairs_audit.csv` -
`data/processed/news_oct2023/cleaned/conflicting_summary_records.csv` -
`reports/fnspid_nasdaq_quality/` --- full NASDAQ audit outputs -
`reports/fnspid_oct2023_quality/` --- October news audit outputs -
`reports/fnspid_stock_quality/stock_quality_metrics.json` -
`reports/fnspid_alignment/` --- ticker alignment lists

## 9. Outstanding items and limitations

1.  **`All_external.csv` decision:** not downloaded. Assess overlap and
    incremental value before deciding whether to collect it.
2.  **Licensing:** usage and redistribution permissions remain
    unresolved. Do not assume commercial-use rights. Resolve licensing
    before public or commercial release.
3.  **206 unmatched news tickers:** retain and investigate as required;
    do not silently discard.
4.  **Stock missing values:** define and document handling for the 257
    missing values per audited price/volume field.
5.  **Three summary conflicts:** the cleaned dataset keeps the first
    record per URL--ticker pair; preserve and consult the conflict
    audit.
6.  **Publisher and author metadata:** 100% missing in the October
    subset.
7.  **Model readiness:** no model performance or predictive validity has
    been established by this procurement and quality work.

## 10. Recommended handoff

For the next IntelliHedge stage: - Use `news_oct2023_deduplicated.csv`
as the cleaned URL--ticker-level news input, while retaining the
original and audit files. - Build a canonical article table and a
separate article--ticker mapping table. - Restrict initial October price
alignment to the 2,619 matched tickers, while keeping the 206 unmatched
symbols documented. - Define missing-price handling and timestamp
conventions before feature generation. - Resolve source licensing before
any external publication or commercial use.

## 11. Completion status

**Completed:** source inspection, NASDAQ news download, stock-price
download and extraction, October news extraction and validation, initial
quality audits, URL--ticker deduplication with conflict preservation,
stock-price audit, and October ticker alignment.

**Pending:** final licensing decision, optional `All_external.csv`
decision, review of unmatched tickers and missing stock values, and
downstream feature/model integration.

**Overall conclusion:** Dataset 3's core NASDAQ news and stock-price
procurement and initial October 2023 evaluation are complete. The
dataset is suitable to hand off for controlled preprocessing and
feature-engineering work, subject to the limitations and decisions
listed above. It should not yet be described as fully production-ready
or commercially cleared.
