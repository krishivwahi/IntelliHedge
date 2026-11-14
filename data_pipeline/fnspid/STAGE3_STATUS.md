# Stage 3 status — FNSPID

| Completion criterion | State |
|---|---|
| Paper / authors' repository identified | Yes |
| Hugging Face source paths identified | Yes |
| Published file sizes and hashes recorded | Yes, Hugging Face file pages; re-check with `inspect` |
| Actual CSV schemas and row counts locally verified | **No — source files not downloaded** |
| October 2023 availability confirmed in each file | **No — must inspect actual records** |
| Collector / parser / quality scripts created | Yes |
| Chunked CSV processing | Yes |
| Resumable full-file download | Implemented; server Range support must be confirmed by local run |
| Synthetic tests | Included; run on user's Windows environment |
| Real-data quality metrics | **Not yet available** |
| Licence conflict | Documented as unresolved |

## Next required local actions

1. `python fnspid_collector.py inspect`
2. Review `data/raw/manifests/source_inventory.json` and available disk space.
3. Download only the source(s) needed after reviewing full-file sizes.
4. Run parser and quality scripts; retain the generated reports.
5. Verify October 2023 availability from actual rows; if incomplete, select the latest complete month within actual coverage.
6. Send `source_inventory.json`, reports and test output for review.
