# GDELT — Licensing Assessment (IntelliHedge V2)

Official source: https://www.gdeltproject.org/about.html (Terms of Use section) — fetched and read this session.

## Findings
| Question | Finding | Basis |
|---|---|---|
| Permitted use | Unlimited and unrestricted use for any academic, commercial or governmental purpose, without fee | official terms |
| Attribution | Any use or redistribution must include a citation to the GDELT Project and a link to https://www.gdeltproject.org/ | official terms |
| Redistribution | You may redistribute, rehost, republish and mirror any GDELT dataset in any form, subject to the attribution above | official terms |
| Underlying article copyright | **The terms page is silent** on ownership/copyright of the news articles GDELT points to | official page (absence of text) |
| Storage / retention limit | None stated | official page (absence of text) |

## Interpretation (not legal advice — I am not a lawyer)
1. **GKG records (metadata, extracted entities, themes, tone, URLs):** usable for research and commercial work and redistributable with a GDELT citation + link.
2. **Article URLs:** the URL strings are part of the GDELT dataset. **The content behind those URLs belongs to the publishers** and is governed by their own terms/copyright; GDELT's grant does not cover it. Any step that fetches, stores or republishes article text/headlines scraped from those pages (e.g. to obtain headlines when `PAGE_TITLE` is missing) needs its own review. Headline text that GDELT itself supplies inside `V2EXTRASXML` is part of the GDELT dataset, but short extracts of third-party text can still raise publisher-copyright questions if republished widely.
3. **Quotations field** (`V2.1QUOTATIONS`) contains excerpts of article text; treat as third-party content for any public redistribution.
4. **Required attribution string** to put in the README/report/any shared dataset: *"Data: The GDELT Project (https://www.gdeltproject.org/)"*.

## Do not confuse with "GDELT Cloud"
A search turned up gdeltcloud.com, a separate commercial API/service with its own tiered acceptance-use terms (free tier: evaluation only, no production use; customer-facing redistribution of its generated fields needs a separate licence). Those terms apply to that product, **not** to the raw files from `data.gdeltproject.org`. The Stage 1 pipeline uses only the open raw files, so the open GDELT Project terms above apply. If the team ever switches to GDELT Cloud, redo this assessment.

## Verdict for IntelliHedge
Licence risk for the GKG metadata: **low** (open, commercial use allowed, attribution required). Residual risk is in downstream use of publisher content, which is outside GDELT's grant. Recommend a short legal confirmation before redistributing any article text.
