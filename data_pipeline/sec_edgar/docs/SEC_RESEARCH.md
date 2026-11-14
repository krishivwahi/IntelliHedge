# SEC EDGAR — Research Documentation (IntelliHedge V2, Stage 2)

Evidence labels: **[V]** read on an official sec.gov page this session · **[3P]** third-party source only (blog, GitHub PR, library docs) ·
**[R]** recalled/assumed, not confirmed on an official page · **[?]** unresolved.

## 0. Reachability
From the build sandbox every request to `www.sec.gov` and `data.sec.gov` fails at the proxy (CONNECT tunnel 403). **No SEC endpoint was called live.**
Facts below come from the official documentation pages fetched through the documentation tool; endpoint behaviour is therefore *documented*, not *observed*.
`python sec_edgar_collector.py check-endpoints` performs the live verification on your machine.

## 1. No single API is enough
| Need | Endpoint | Why |
|---|---|---|
| Complete list of every 8-K filed on a date | Daily index `/Archives/edgar/daily-index/YYYY/QTRn/master.YYYYMMDD.idx` | The submissions API is per-company; it cannot enumerate "all filers on a day". Index = completeness backbone. [V] that `daily-index` exists, holds daily files for the current year and has `index.json`; file name pattern `master.YYYYMMDD.idx` and its pipe-delimited layout are [R] |
| Company metadata, items, primary document name, report date, tickers, exchange, SIC | `https://data.sec.gov/submissions/CIK##########.json` | [V]. 10-digit zero-padded CIK; "at least one year of filings or the 1,000 most recent, whichever is larger", older filings in additional JSON files each with a date range; updates in <1 s typically |
| Acceptance timestamp (second precision) | SGML header `/Archives/edgar/data/<cik>/<acc-no-dashes>/<acc>.hdr.sgml` and the submissions field `acceptanceDateTime` | `.hdr.sgml` path [V] (named on the accessing-edgar-data page); `<ACCEPTANCE-DATETIME>` tag name [R] |
| Document list incl. exhibits and types | `/Archives/edgar/data/<cik>/<acc>-index.html` | [V] path exists; table layout [R] |
| Filing text | `/Archives/edgar/data/<cik>/<acc-no-dashes>/<primaryDocument>` | directory pattern [V] (filings after 26 May 2000) |
| Financial-statement facts (XBRL) | Company Facts, Company Concept, Frames, `companyfacts.zip` | [V] they exist; **not used** — XBRL facts do not contain 8-K event text, items or acceptance times |
| Bulk company history | `submissions.zip` (rebuilt nightly, ~03:00 ET) | [V]; not used (we need same-day/point-in-time data and only need the companies that filed) |

Other documented paths: `/Archives/edgar/full-index` (quarterly, 1994Q3+) [V]; raw filing `/Archives/edgar/data/CIK/ACCESSION.txt` [V].
No API keys or authentication are needed [V]; data.sec.gov has no CORS [V].

## 2. Identifiers
* **CIK** — unique number SEC assigns each filer [V: EDGAR glossary]. Submissions API requires 10 digits with leading zeros [V]; archive paths use the integer form [R, used by the collector].
* **Accession number** `0001193125-15-118890` — unique, assigned automatically by EDGAR [V]. First segment = CIK of the *submitting entity, which may be a filer agent* [V]; second = year; third = sequence, "usually but not always" reset each year [V]. Digit lengths are only observed from the example (10-2-6). Consequence: the accession prefix must **not** be used to infer the company.
* A filing can have several filers (co-registrants): the daily index then lists the same accession under several CIKs. The collector keeps one row per accession and records co-filer CIKs.

## 3. Time fields — the central risk for point-in-time alignment
| Field | Meaning | Precision | Source |
|---|---|---|---|
| Filing date | date EDGAR assigns | day | index, submissions `filingDate`, header |
| Acceptance datetime | when EDGAR accepted the submission | second | header `<ACCEPTANCE-DATETIME>` (YYYYMMDDHHMMSS, no zone), submissions `acceptanceDateTime` (ISO string ending `Z`), index page "Accepted" |
| Report date | period/event date of the report | day | `reportDate`, `CONFORMED PERIOD OF REPORT` |
| Collection time | when we downloaded | second | our manifest `collected_at_utc` |

**Unresolved [?]: the timezone of `acceptanceDateTime`.** No official page read this session states it.
* [3P] A GitHub PR (aaltaay/Nova #670, merged 2026-10-01) reports that some filers' submissions JSON holds **Eastern wall-clock time behind a `Z` suffix** (e.g. an 8-K shown `16:31:36Z` while its index page says "Accepted 16:31:36 (Eastern)"), per-filer-file, ~30% of 2021 filings and ~0.5% of 2026 filings in the author's store.
* [3P] A second PR (vishalrana/stock-recommendation-engine #63) reports EDGAR switching "document by document from about **2026-10-14**" to true UTC, with large-filer examples (AAPL 8-K header 16:30:28 ET ↔ JSON `20:30:28Z`).
* Both are unofficial and the second self-reports a limited sample. **The reported switch date falls inside our collection window**, so the October data may mix conventions.

Handling in this project:
1. The parser stores both timestamps raw and the **per-filing comparison** `acceptance_convention` ∈ {`api_true_utc`, `api_wallclock_equals_header_wallclock`, `inconsistent`, `unverifiable`}.
2. The "best" acceptance time is the **header time, assumed US Eastern** (confidence "medium", an assumption), falling back to the API time (confidence "low").
3. The quality script scores three hypotheses against two rules reported by [3P] (EDGAR accepts ~06:00–22:00 ET on business days; submissions accepted after 17:30 ET receive the next business day's filing date). Neither rule was confirmed on an official page. Treat the result as evidence, not proof; ask the SEC or confirm against EDGAR's Atom feed (which reportedly carries explicit offsets [3P]) before trading-grade use.

Filing date ≠ acceptance date: a filing accepted at 18:00 ET is dated the next business day [3P]. Using the filing date as the event time can shift an event by a trading day.

## 4. Form 8-K and amendments
* 8-K = current report of material corporate events. Item numbers (1.01 … 9.01) are stored in submissions `items` (comma-separated) and as `ITEM INFORMATION` lines in the header. Titles used in `sec_edgar_parser.ITEM_TITLES` come from a **third-party reference (edgar.tools)**; the official `form8-k.pdf` could not be fetched. Item numbers themselves always come from SEC metadata.
* **8-K/A** (amendment) is kept in the primary dataset with `is_amendment=True`, because (a) it can carry material corrections/late items and (b) dropping it silently loses information; users can filter it out. Original vs amended are never merged. Both are listed in the daily index as separate form types.
* Other potentially relevant forms (e.g. SC 13D/G, 424B, 10-Q/10-K, 6-K for foreign issuers, Form 4) are **not collected by default**. `--forms` makes them selectable; they land in `filings_other`, never in `filings_primary`.

## 5. Contribution of 8-K items to event detection (no model built)
| Event class | Typical items |
|---|---|
| Earnings / results | 2.02 (+9.01 exhibits, usually EX-99.1 press release) |
| M&A, material agreements | 1.01, 1.02, 2.01 |
| Executive/board changes | 5.02 |
| Bankruptcy / restructuring / impairments | 1.03, 2.05, 2.06 |
| Financing / obligations | 2.03, 2.04, 3.02 |
| Listing, control, accounting issues | 3.01, 5.01, 4.01, 4.02 |
| Cyber incidents | 1.05 |
| Regulation FD / other | 7.01, 8.01 |
Item numbers are preserved verbatim in `items_list` / `items_titles`; mapping them to events is deliberately left for a later stage.

## 6. Trading-session alignment
From acceptance time (ET) the parser derives `session_bucket`: pre_market 04:00–09:30, regular 09:30–16:00, after_hours 16:00–20:00, overnight otherwise, and `accepted_after_1730_et`. A trading calendar (holidays, early closes) is **not** included; the closed-day list in the scripts is an assumption (US federal holidays 2026) used only to label expected missing index days. Alignment is feasible **only with the acceptance time**; the filing date alone is not enough.

## 7. Access limits (see LICENSING_ASSESSMENT.md)
10 requests/second maximum, all machines combined; declared User-Agent; excess may be limited for a period; SEC provides no support for debugging scripts [V].

## 8. Known gaps / open questions
1. Live behaviour of every endpoint — untested (sandbox blocked).
2. Daily-index filename/layout, header tag names, index-page HTML layout, submissions column names and the `files[].filingFrom/filingTo` keys — recalled from third-party sources; the collector fails loudly (manifest `failed`) if they differ.
3. Timezone of `acceptanceDateTime` (section 3).
4. Whether daily indexes are published for every business day and how late-day filings are indexed.
5. Whether an 8-K's primary document is always the first document of type 8-K (collector uses the submissions `primaryDocument`, falling back to the index page).

## 9. Official sources
* APIs: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
* Accessing EDGAR data (fair access, paths, indexes, accession format): https://www.sec.gov/os/accessing-edgar-data
* Privacy & website policy (reuse, automated access): https://www.sec.gov/about/privacy-information
* EDGAR glossary: https://www.sec.gov/page/edgar-glossary
* Archive roots: https://www.sec.gov/Archives/edgar/ · https://www.sec.gov/Archives/edgar/daily-index/
* Third-party (unofficial) used: https://github.com/aaltaay/Nova/pull/670 · https://github.com/vishalrana/stock-recommendation-engine/pull/63 · https://www.edgar.tools/blog/8-k-item-index
