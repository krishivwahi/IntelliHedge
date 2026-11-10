# Pre-Analysis Plan (one page, draft 0.1)

To be frozen as a signed git tag **before** the test period is opened. Anything not in this plan is reported as exploratory.

**Hypotheses.**
H1: Given the full market information set, a point-in-time news-regime vector reduces out-of-sample CVaR of hedging loss on a short-option book, net of costs.
H2: In a partially observed jump-intensity model, the reduction increases with news informativeness ρ and lead ℓ, and is zero at ρ = 0.

**Book.** Each week, short one ≈30-day at-the-money put on the S&P 500 (SPX or SPY, fixed once data is chosen). Hedge to expiry with the underlying and one listed out-of-the-money put. Daily rebalancing at the close. Costs: half the quoted spread on options; 1 bp on the underlying.

**Arms.** Identical network, parameter count, epochs, seeds and tuning budget.

| Arm | Input |
|---|---|
| A0 | Black–Scholes delta and delta–gamma hedges (no learning) |
| A | Market features only: moneyness, time to expiry, ATM implied vol, skew, term slope, 5- and 21-day realised vol, VIX, previous position |
| B | A + news-regime vector available at decision time |
| C | A + news vector block-shuffled across dates (20-day blocks) |
| D | A + news vector lagged 1, 2 and 5 trading days |

**Splits.** Train 2015–2019 · validation 2020–2021 · **test 2022–2025, opened once.** Text encoder frozen with a training cut-off before 2022. Strength weights fixed from ≈500 hand-labelled headlines drawn from 2015–2019 only. Policies are pre-trained on a simulator calibrated to 2015–2019, fine-tuned on training episodes, selected on validation.

**Primary outcome.** ΔCVaR₉₅ of terminal hedging loss, Arm B − Arm A, over all test episodes, averaged over 10 training seeds.

**Secondary outcomes.** ΔCVaR₉₉; mean loss; turnover and cost; the same on *event* episodes only. An event day is one in the top 5% of |ΔVIX| within the test period; an event episode contains at least one.

**Inference.** Stationary bootstrap over episodes (mean block 4 weeks), resampling training seeds jointly; 95% percentile interval, 10,000 replicates. H1 is supported only if **all** hold:
1. the interval for B − A lies below zero;
2. the interval for C − A contains zero;
3. B − D is negative and shrinks toward zero as the lag grows.

If (1) holds and (2) fails, the result is reported as a capacity or leakage artifact, not as support for H1.

**Multiple testing.** One primary test. Every configuration tried on validation is logged; Hansen's SPA test is reported across them.

**Stopping and deviations.** No arm is retrained after the test set is opened. Any deviation is listed in an appendix with its date and reason.

**Simulation study (H2).** Bates model with a hidden two-state intensity; news = noisy, shifted observation. Grid: ρ ∈ {0, 0.25, 0.5, 0.75, 1}, ℓ ∈ {−2, −1, 0, 1, 2} steps, market-efficiency φ ∈ {0, 0.5, 1}. 100,000 test paths, 10 seeds, paired bootstrap. Pass conditions: interval contains zero at ρ = 0; effect monotone in ρ; Arm B lies between Arm A and the oracle that sees the true regime.

**Open items for the advisor.** Index vs ETF options · block length · whether to register on OSF in addition to the git tag.
