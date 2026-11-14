# Source inventory and feasibility (Stage 4, research phase)
| Product | Endpoint | Access needed | History | Body text | Cost verified | Status |
|---|---|---|---|---|---|---|
| Alpaca News | data.alpaca.markets/v1beta1/news | Alpaca key pair | "since 2015" [V] | `content` optional/subset [V] | free beta 2022; **current [U]** | feasible if a free key works; **[U] until tested** |
| Alpaca bars/trades/quotes | data.alpaca.markets/v2/stocks/... [A] | Alpaca key pair | since 2016 [V] | n/a | Basic free (IEX, 200/min); Algo Trader Plus $99/mo [V] | feasible on IEX-only free feed |
| Benzinga direct News | api.benzinga.com/api/v2/news | licence/contract (contact sales) [V] | [U] | `displayOutput=full` [V] | **not published [V]** | **BLOCKED** until user confirms access |
| Benzinga via Massive | /benzinga/v2/news | paid Massive plan [S] | 2009– [S] | full body [S] | not verified | not evaluated; would incur charges |

## Period (Section 3)
Preferred **2026-10-01..2026-10-31**. Today is 2026-11-13, so the month is complete and inside Alpaca's documented coverage. Whether either account tier actually returns it: **[U]** until a credentialed probe. Date boundaries: Alpaca `start/end` inclusive, so request `2026-10-01T00:00:00Z` .. `2026-10-31T23:59:59Z` (UTC) and record that ET-day boundaries differ by 4 h; Benzinga `dateFrom/dateTo` are dates with an undocumented zone (**[U]**).

## Provenance (critical)
- **[V]** Alpaca docs say news is "provided directly by Benzinga" (older page) / "one or more feeds" (current). So Alpaca news is **expected to be a Benzinga redistribution**; the two are therefore **not independent** by default. Degree of overlap and any non-Benzinga `source` values: **[U]**, to be measured by comparing ids/URLs/headlines (Alpaca `id` vs Benzinga `id` equality is an unverified hypothesis).
- Distinguish: API vendor (Alpaca / Benzinga / Massive), upstream publisher (Benzinga; others if present), author (`author` field), licensor (Benzinga; Alpaca's own rights **[U]**).

## Recommendation (feasibility only)
1. Start with **Alpaca** free key: pull a 1-day probe (limit 50, one ticker) to confirm entitlement, `source` values, `content` share and timestamps; then the month.
2. **Do not pursue Benzinga direct or Massive** until you confirm you want to contact sales / pay; everything beyond research is blocked on that and I will not incur charges.
3. Expect Alpaca ≈ Benzinga content, so a direct comparison may measure near-total overlap rather than independence — confirm with data before claiming it.
