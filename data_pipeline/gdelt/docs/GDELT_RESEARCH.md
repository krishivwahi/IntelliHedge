# GDELT 2.0 GKG — Research Documentation (IntelliHedge V2, Stage 1)

Evidence labels used below:
**[V]** verified this session from an official GDELT page or an official-page quotation;
**[3P]** seen only in third-party documentation (library docs / papers);
**[R]** recalled from the GKG 2.1 codebook but the PDF could not be fetched here — verify before relying on it;
**[?]** could not be established.

## 1. What the GKG is
The Global Knowledge Graph records individual news articles and extracts persons, organisations, locations, themes, counts and tone from each; the Event database aggregates events across articles [3P: ONS appendix]. GKG 2.0 left alpha status; GDELT states the format is stable and "will not change" [V: blog.gdeltproject.org, *Introducing GKG 2.0*]. GKG 2.0 added character offsets for every extracted object, the `V2EXTRASXML` field, and GCAM content-analysis measures [V: same post].

## 2. Endpoints and archive status
| Item | Value | Status |
|---|---|---|
| English master list | `data.gdeltproject.org/gdeltv2/masterfilelist.txt` | [V] URL listed on GDELT blog |
| Translingual master list | `.../masterfilelist-translation.txt` | [V] |
| Last 15 minutes (English / translingual) | `.../lastupdate.txt`, `.../lastupdate-translation.txt` | [V] |
| GKG file | `.../gdeltv2/YYYYMMDDHHMMSS.gkg.csv.zip` | [3P: py-gdelt docs] |
| Translingual GKG file | `.../gdeltv2/YYYYMMDDHHMMSS.translation.gkg.csv.zip` | [R] |
| Codebook (2.1) | `http://data.gdeltproject.org/documentation/GDELT-Global_Knowledge_Graph_Codebook-V2.1.pdf` | [3P link; not fetchable here] |

* **Update frequency:** every 15 minutes (slots :00/:15/:30/:45) [V: gdeltproject.org/data.html + blog]. ≈96 files/day, ≈2,976 for 31 days.
* **Coverage start:** the 2.0 stream begins late morning 19 Feb 2015 [V: blog]. October 2026 is inside the nominal range.
* **Translingual:** news in 65 languages is machine-translated and processed into GKG; it is a separate file stream [V: blog].

### October 2026 availability — NOT VERIFIED
Every route to `data.gdeltproject.org` from the build sandbox failed (DNS failure; HTTPS proxy 403; WebFetch "not on allowlist"). I therefore **cannot confirm** that October 2026 files exist, nor that the master list is stale. What I did instead:

1. The collector **generates** the 96 file names per day from the clock and downloads them directly, so it does not rely on `masterfilelist.txt` at all.
2. `python gdelt_collector.py check-archive` tests, on your machine: `lastupdate.txt`, the freshness of the master list (latest slot, entries inside Oct 2026 vs the 2,976 expected) and HEAD probes on the first, midday and last slot of the period. It writes `archive_check.json` with an explicit conclusion.
3. Possible reasons the list you inspected looked outdated (untested hypotheses): a cached/mirrored copy, the file being truncated by a partial download (it is very large), or the list lagging the files. `check-archive` distinguishes these.
4. If direct probes also return 404 for October 2026, the collector records every slot as `missing_404` in `manifest.csv` and `download_summary.json` — it never substitutes another period. A documented alternative is Google BigQuery's public GDELT tables [R, untested here].

## 3. File format and schema
Tab-delimited, UTF-8, no header, one zipped CSV per 15 minutes, **27 columns** (GKG 2.1) [R]. Parser column names follow the codebook:

| # | Field | Meaning (per codebook) |
|---|---|---|
| 1 | GKGRECORDID | `YYYYMMDDHHMMSS-N`; `-TN` for translingual. Unique per record; sequence implies nothing [V: blog on IDs] |
| 2 | V2.1DATE | `YYYYMMDDHHMMSS`; 2.0 used `YYYYMMDD` [V: codebook quote on hackage] |
| 3 | V2SOURCECOLLECTIONIDENTIFIER | 1 Web, 2 Citation-only, 3 Core, 4 DTIC, 5 JSTOR, 6 Non-textual |
| 4 | V2SOURCECOMMONNAME | usually the source domain |
| 5 | V2DOCUMENTIDENTIFIER | URL (or other document id) |
| 6–7 | V1COUNTS, V2.1COUNTS | extracted counts |
| 8–9 | V1THEMES, V2ENHANCEDTHEMES | theme codes; enhanced adds char offsets |
| 10–11 | V1LOCATIONS, V2ENHANCEDLOCATIONS | `type#name#country#adm1…#lat#lon#featureID[#offset]` |
| 12–13 | V1PERSONS, V2ENHANCEDPERSONS | names (+offsets) |
| 14–15 | V1ORGANIZATIONS, V2ENHANCEDORGANIZATIONS | names (+offsets) |
| 16 | V2.1TONE | 7 comma values: tone, positive, negative, polarity, activity density, self/group density, word count |
| 17 | V2.1ENHANCEDDATES | dates mentioned in the text |
| 18 | V2GCAM | thousands of content-analysis dimensions |
| 19–22 | image / social embed fields | sharing image, related images, social image & video embeds |
| 23 | V2.1QUOTATIONS | extracted quotes |
| 24 | V2.1ALLNAMES | all proper names |
| 25 | V2.1AMOUNTS | quantities |
| 26 | V2.1TRANSLATIONINFO | e.g. `srclc:deu;eng:…` for translated documents |
| 27 | V2EXTRASXML | XML blob for specialised/extra fields (e.g. page title, authors, precise publication timestamp, AMP/mobile URLs) [V that the field exists and carries article metadata, per the GDELT blog "New GKG 2.0 Article Metadata Fields"; exact tag names `PAGE_TITLE`, `PAGE_PRECISEPUBTIMESTAMP`, `PAGE_AUTHORS` are [R]] |

**Not provided as dedicated columns:** headline, author, article body, ticker symbols, company identifiers. The headline exists only if `PAGE_TITLE` is present in `V2EXTRASXML`; `gdelt_quality_analysis.py` reports how often. The parser derives nothing that is not physically in a record.

## 4. Timestamp semantics (critical for point-in-time use)
Three different times exist; do not conflate them:

| Time | Where | What it is |
|---|---|---|
| **File slot** | file name | the 15-minute batch in which GDELT emitted the record |
| **Record time** | `V2.1DATE` (+ prefix of GKGRECORDID) | per the codebook it is described in publication-date terms [R]; in practice it is expected to coincide with the 15-minute batch stamp, i.e. GDELT's collection/processing time **[hypothesis — the quality script tests it: % of records where V2.1DATE equals the file slot, % with non-zero seconds]** |
| **Page publication time** | `V2EXTRASXML` `PAGE_PRECISEPUBTIMESTAMP` [R] | publication time GDELT parsed from the page's own metadata; second-level precision, **only present for a subset of pages** and only as reliable as the page's markup |

Consequences for look-ahead bias: use the *file slot / record time* as the earliest time GDELT could have *observed* the article (a conservative availability time, precision 15 min), and the page publication time only as supplementary information. Timezone: UTC [R; the data cannot prove it]. The GKG record is **not** the article's original publication timestamp.

## 5. Language
There is no dedicated language column. `V2.1TRANSLATIONINFO` carries the source language code for translated documents; for the English stream the parser records `eng` and labels the basis "english-stream (inferred from file stream)" so the inference is explicit.

## 6. Licensing → see `LICENSING_ASSESSMENT.md`.

## 7. Sources
* GDELT data page: https://www.gdeltproject.org/data.html
* GDELT about / terms of use: https://www.gdeltproject.org/about.html
* GDELT 2.0 announcement (file lists, 15-min cadence, 2015-02-19 start): https://blog.gdeltproject.org/gdelt-2-0-our-global-world-in-realtime/
* Introducing GKG 2.0: https://blog.gdeltproject.org/introducing-gkg-2-0-the-next-generation-of-the-gdelt-global-knowledge-graph/
* New GKG 2.0 article metadata fields: https://blog.gdeltproject.org/?p=3176
* GKG codebook V2.1 (link as cited by third parties; not fetched): http://data.gdeltproject.org/documentation/GDELT-Global_Knowledge_Graph_Codebook-V2.1.pdf
