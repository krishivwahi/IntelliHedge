# SEC EDGAR — Licensing & Usage Assessment (IntelliHedge V2)

Not legal advice. Findings marked **[V]** were read on the official page named; "absent" means the page was read and says nothing on the point.

## 1. Verified findings
| Topic | Finding | Source |
|---|---|---|
| Public-information status | Information on sec.gov "is considered public information"; users may copy or further distribute it without the SEC's permission [V] | https://www.sec.gov/about/privacy-information ("Website Dissemination") |
| Attribution | SEC asks users to *consider* appropriate citation to the SEC as the source; no required format [V] | same |
| Logos / marks | Do not use the SEC seal, logos or artwork; "SEC", EDGAR, EDGARLink are registered trademarks; text references to EDGAR are allowed if they do not imply SEC affiliation or approval [V] | same |
| Automated access | SEC "does not allow 'unclassified' bots or automated tools to crawl the site"; automated access must follow the SEC privacy/security policy [V]. "Unclassified" is not defined (absent) | same; API page |
| Request rate | "Current max request rate: 10 requests/second", across all machines combined; SEC may change it and reserves the right to limit rates [V] | https://www.sec.gov/os/accessing-edgar-data ; privacy page |
| Consequence of exceeding | Further requests from the IP may be limited briefly; access resumes after the rate stays below the limit for 10 minutes; excessive IPs may be blocked [V] | privacy page |
| User-Agent | Declare a user agent in the request headers; sample: "Sample Company Name AdminContact@<domain>.com" [V]. Whether it is formally mandatory is not stated (absent) | accessing-edgar-data |
| Credentials | No API key / authentication required for data.sec.gov [V] | API page |
| Support | SEC offers no technical support for developing or debugging scripted downloads [V] | accessing-edgar-data, API page |
| Third-party material in filings | **Absent.** No statement on copyright of documents submitted by outside parties, no takedown procedure, no open licence text [V (absence)] | privacy page |

## 2. Distinction required by the brief
| Category | Examples | Position |
|---|---|---|
| **SEC-generated metadata** | accession number, CIK, filing/acceptance dates, form type, index and header fields, EDGAR-assigned item lists, SIC code | Public information; free to copy and redistribute per the SEC statement above. Citing the SEC as the source is requested. |
| **Content submitted by filers** | 8-K narrative text, exhibits (press releases, agreements, opinions), images | Authored by companies or third parties. SEC's page neither grants nor removes copyright for it. Public disclosure under securities law does not by itself settle reuse rights for redistribution of large corpora. Exhibits may embed third-party copyrighted material (analyst quotes, licensed images, reports). |
| **Derived data** (our parsed tables, item labels, flags) | `filings_primary`, `session_bucket` | Ours; but it embeds the two categories above. Item *titles* in the parser come from a third-party reference, not the SEC. |

## 3. Recommended practice for IntelliHedge
1. Use metadata and item numbers freely for research; cite "Source: U.S. Securities and Exchange Commission, EDGAR (https://www.sec.gov/edgar)".
2. Keep raw filing documents **internal**; do not redistribute bulk filing text or exhibits publicly without legal review. Short extracts for analysis are the lower-risk use.
3. Never present derived data as SEC-endorsed; do not use SEC logos.
4. Follow fair access: declared User-Agent with a **real contact address you own**, ≤10 req/s total (default 6), stop on repeated 403/429. Do not run several collectors in parallel from one network.
5. Re-read the privacy/website policy before production use; the SEC states these rules may change.

## 4. Open questions for counsel
* Redistribution rights for full-text exhibits in a shared/commercial dataset.
* Whether "unclassified bots" language applies to a declared, rate-limited research client (the sample User-Agent guidance suggests declared clients are expected, but the term is undefined).
* Retention/redistribution rules for any third-party content within exhibits.

## 5. Sources
https://www.sec.gov/about/privacy-information · https://www.sec.gov/os/accessing-edgar-data · https://www.sec.gov/search-filings/edgar-application-programming-interfaces
