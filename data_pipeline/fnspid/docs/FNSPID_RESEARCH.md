# FNSPID research notes

## Primary sources

- Paper: https://arxiv.org/abs/2402.06698
- Authors' repository: https://github.com/Zdong104/FNSPID_Financial_News_Dataset
- Hugging Face dataset: https://huggingface.co/datasets/Zihan1004/FNSPID

The paper describes FNSPID as a financial news and stock-price integration dataset, with 15.7 million financial news records and 29.7 million stock-price records for 4,775 S&P 500 companies, covering 1999–2023. It says news came from four stock-market news websites. These are published claims; this package has not downloaded the files to independently validate the counts or date bounds.

## Candidate source files

| File | Hugging Face path | Published size shown on file page | SHA-256 shown on file page |
|---|---|---:|---|
| All_external.csv | `Stock_news/All_external.csv` | 5.73 GB | `5d4c018036bd82ca821da71b7a9c0c7db3289642e0fc6f897ea69f4a0c5135c3` |
| nasdaq_exteral_data.csv | `Stock_news/nasdaq_exteral_data.csv` | 23.2 GB | `1a7a3eb8e6b97ec19f286f2cfca3371542bddb272ab1eb8f36e33ad98fa5c4da` |
| full_history.zip | `Stock_price/full_history.zip` | 590 MB | `03da4fce7ebea90d5715ba3501773d410ae663b617027b338ef000a9955dab91` |

The Hugging Face file pages identify these as Xet-backed large files. Values above are the displayed file-page metadata and should be rechecked with `python fnspid_collector.py inspect`. The full corpus is approximately 29.6 GB according to a Hugging Face dataset mirror/card; the three files listed above total substantially less because the 29.6 GB size category may include all corpus objects/metadata or another representation. Do not treat the estimates as interchangeable.

## Source history / maintenance

The authors' GitHub README announcement dated 2025-07-24 says repository maintenance will stop. The same README contains a commercial-use prohibition requiring prior author authorization. The upstream Hugging Face dataset file history surfaced in the research review shows uploads in February and April 2024; no newer upstream data refresh was established in this review. This is a historical static dataset, not a live 2026 news feed.

## Schema and date coverage

The paper and repository-level metadata do not establish the exact populated columns or row-level date bounds of every current file. The source files must be inspected after download. Expected preview fields include `Date`, `Article_title`, `Stock_symbol`, `Url`, `Publisher`, `Author`, `Article`, and summary fields, but the parser deliberately discovers columns rather than requiring every field.

October 1–31, 2023 is the proposed sample. Its completeness is **unverified** until actual rows from each news file are scanned. The package does not silently select another month.

## Download feasibility

A CSV that is not guaranteed sorted by date cannot safely yield a date subset using a simple byte-range request. The supported workflow therefore probes remote sizes first, then downloads the full selected source resumably, then filters rows in chunks. No 29.6 GB download is started automatically.
