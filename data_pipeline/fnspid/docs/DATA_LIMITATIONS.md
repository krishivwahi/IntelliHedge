# Data limitations and unresolved checks

- Published corpus totals are not verified against downloaded source files.
- Actual row-level schemas, date bounds, populated fields and October 2023 completeness remain to be measured.
- News files are distinct sources; they are not concatenated by default.
- Cross-file overlap, syndicated copies and multi-ticker article associations remain unmeasured until both news files are present.
- Parser retains raw timestamps and adds a UTC-comparable timestamp plus an explicit-offset flag. Naive values are coerced to UTC only as a computational convention; their true source timezone remains unknown.
- Stock/news matching requires trading calendars, exchange timezone and session-aware lag rules; this package does not auto-join.
- FNSPID is historical (paper coverage through 2023), not a current 2026 feed.
- Publisher article text may carry separate copyright restrictions.
- Downloading one month may still require downloading an entire CSV if rows are not sorted/indexed and no trustworthy server-side filter exists.
