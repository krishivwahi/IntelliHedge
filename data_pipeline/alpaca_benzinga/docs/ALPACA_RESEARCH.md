# Alpaca research (accessed 2026-11-13)
Labels: **[V]** verified in a cited page; **[S]** secondary source; **[U]** unresolved. Nothing was called against the live API (no credentials; not requested).

## News API
- **[V]** `GET https://data.alpaca.markets/v1beta1/news` (sandbox host `data.sandbox.alpaca.markets`). Params: `symbols`, `start`/`end` (inclusive, RFC-3339 or YYYY-MM-DD), `limit` (default 10, **max 50**), `sort` asc/desc ("by updated date"), `include_content`, `exclude_contentless`, `page_token`. Response `news[]` + `next_page_token`. Source: [News articles reference](https://docs.alpaca.markets/us/reference/news-3.md).
- **[V]** Article fields: `id`, `headline`, `author` (may be empty), `created_at`, `updated_at` (RFC-3339), `summary` (may be empty), `content` (may contain HTML / be empty), `url` (optional), `source`, `symbols`, `images`. Errors 400/401/403/429/500.
- **[V]** "historical news data dating back to 2015"; "average of 130+ articles per day"; "All news data is currently provided directly by Benzinga" ([Historical News Data](https://docs.alpaca.markets/us/v1.4.2/docs/historical-news-data) — versioned v1.4.2 page, may be stale). The current overview page instead says articles "can come from one or more news feeds" ([Historical News Data](https://docs.alpaca.markets/us/docs/historical-news-data)). **Whether `source` currently has values other than Benzinga: [U]** (measured only after a real pull).
- **[V]** 2022 launch post: news was a free beta; "may be additional pricing changes"; Alpaca "not affiliated with Benzinga" ([blog, 2022-02-07, modified 2023-07-26](https://alpaca.markets/blog/introducing-news-api-for-real-time-fiancial-news)). **Current news pricing/entitlement per plan: [U]** — not stated on pages read.
- **[V]** Full `content` only for a subset: blog says "130-160 full-length articles" vs "600-900 headlines per day" (2022). Current share: [U], measured later.

## Market data
- **[V]** Plans (Trading API): Basic free — equities **IEX only**, historical limit "latest 15 minutes" (i.e. most recent 15 min of SIP not served), **200 calls/min**; Algo Trader Plus **$99/month** — all US exchanges, no historical restriction, **10,000 calls/min**. Equities history "since 2016". Source: [About Market Data API](https://docs.alpaca.markets/us/docs/about-market-data-api.md).
- **[U]** Bars timeframes, adjustment options, per-page limits, feed parameter semantics (page not fetchable in this session). Do not call free data consolidated: the page says Basic = IEX only.
- **[U]** Rate limit applicable to news calls on each plan (blog says news limits follow Market Data plan; may be outdated).

## Credentials
- **[A]** Headers `APCA-API-KEY-ID` / `APCA-API-SECRET-KEY` (standard Alpaca scheme; not shown on the pages read). A free Alpaca account (paper trading keys) is the expected route; **[U]** whether paper keys return historical news.

## Terms
- **[U]** Alpaca's own Market Data / news terms were not located in a primary source this session. Do not assume research, storage, ML or redistribution rights. Third-party blog posts surfaced by search were not used.
