# Stage 1 status — GDELT 2.0 GKG

## Completion criteria
| Criterion | State |
|---|---|
| Collection method verified | **Partly.** Official docs confirm 15-min cadence, master/lastupdate URLs, 2.0 start date (2015-02-19). File-name pattern confirmed only via third-party docs; translingual naming and the 27-column schema are from the codebook as recalled (PDF not fetchable). |
| October 2026 availability checked | **No — blocked.** Sandbox cannot reach `data.gdeltproject.org` (DNS failure; HTTPS proxy 403; WebFetch allowlist). `check-archive` does this check on your machine. |
| Collector works | Written and logic-reviewed; **not exercised against the real server**. |
| Raw / processed separated | Yes (`data/raw`, `data/processed`). |
| Quality metrics on actual records | **No — no real records obtained.** Code verified on synthetic data only. |
| Licence assessment | Done, from the official terms page. |
| Scripts independently executable | Yes (parser and analysis verified end-to-end on synthetic input). |

## Needs your local execution
Run README steps 1→4. Send me `archive_check.json`, `data/raw/download_summary.json` and `reports/quality_metrics.json` and I will finish the report, samples and Stage-1 sign-off.

## Open items to confirm from real data
1. Whether V2.1DATE equals the file slot (batch time) — decides the point-in-time timestamp you can trust.
2. How often `PAGE_TITLE` / `PAGE_PRECISEPUBTIMESTAMP` exist in `V2EXTRASXML` (headline and publication-time coverage).
3. Whether the master list is actually stale for Oct 2026 (direct probes will show).
