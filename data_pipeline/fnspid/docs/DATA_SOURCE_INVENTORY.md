# FNSPID source inventory

| Source | Role | Current package handling |
|---|---|---|
| `All_external.csv` | External financial news collection | Separate source; chunked local filter |
| `nasdaq_exteral_data.csv` | Nasdaq news data | Separate source; chunked local filter |
| `full_history.zip` | Historical stock-price data | Separate ZIP; list/extract CSV/TXT members |

The authors' README links directly to the Hugging Face `full_history.zip` and `nasdaq_exteral_data.csv`. `All_external.csv` is also present in the official Hugging Face repository.

Run `python fnspid_collector.py inspect` to write the current endpoint probe. Record actual file bytes, SHA-256 and ZIP member names after downloading. Never infer actual schema or date coverage from a filename.
