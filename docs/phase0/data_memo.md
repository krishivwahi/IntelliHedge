# Data Decision Memo and Budget Request (draft for advisor)

**From:** Krishiv Wahi · **To:** [Advisor] · **Decision needed by:** end of week 2

## 1. The decision

The paper's main claim needs two historical datasets on one clock: **timestamped news** and **option quotes with bid and ask**. News can be had for free. Option history is the constraint; without it the real-data half of the paper does not exist. I need to know what the university can provide before choosing.

## 2. Questions for you (yes/no is enough)

1. Does the university or any department have **WRDS** access? If yes, does it include **OptionMetrics IvyDB US**?
2. Does the library have **Refinitiv/LSEG Workspace or Eikon**, **Bloomberg terminals**, or **RavenPack**? Are students allowed to export data for research?
3. Is there a **department or project fund** for a one-off data purchase, and what is the ceiling and the approval route?
4. Can you put me in touch with anyone on campus who has purchased **NSE historical F&O data** or holds a data vendor contract?
5. Is there **GPU or cluster time** available to final-year projects?

## 3. Options, in order of preference

| | Option data | News | Cost | Consequence |
|---|---|---|---|---|
| **A** | OptionMetrics via WRDS (S&P 500 index options, daily, 1996–) | GDELT + SEC EDGAR + central-bank releases (free); Refinitiv if licensed | None to the project | Best case. Same data source as the published papers we compare against (Chen & Li 2023; François et al. 2025) |
| **B** | Purchased end-of-day SPX/SPY chains from a retail vendor (2015–2025) | Same free news | One-off purchase — **quote to be obtained this week; I am not guessing a figure** | Fully workable. Daily rebalancing only |
| **C** | NSE NIFTY option bhavcopy (free, end-of-day) | GDELT filtered to India + Indian business press | None | Workable and novel (Indian market), but the news corpus needs rebuilding and reviewers know the US data better |
| **D** | None — hedge with the underlying only | Free news | None | Last resort. The paper loses the option leg and becomes a much weaker result |

Intraday option data is an upgrade to A or B and is **not** requested now.

## 4. What I will do regardless

- Week 1: pull one month of each free news source and report timestamp precision, duplicates and licence terms.
- Week 2: obtain written quotes for option B from at least two vendors and confirm the exact date range and fields (bid, ask, IV, open interest).
- Week 4 hard stop: if neither A nor B is confirmed, switch to C.

## 5. Recommendation

A if available; otherwise B, with C as the committed fallback. I am asking for approval to spend up to **[amount, once quotes are in]** on option B if WRDS is unavailable.

## 6. Licence and ethics notes

- Vendor data stays out of the public repository. The repo ships a synthetic-data path so results are reproducible in structure without the licensed files.
- News text is stored for research use only; the public release contains IDs, timestamps and derived features, not article text.
