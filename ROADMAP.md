# IntelliHedge — 12-Month Research & Engineering Roadmap (v2)

**News-Regime-Conditioned Deep Hedging** · Lead: Krishiv Wahi · Team: 2 teammates (B = News/Data, C = Simulation/Eval) + faculty advisor
Supersedes the 24-month roadmap (Sept 2026). Core plan: **40 working weeks + 6 weeks float ≈ 12 months**. Months 13–18 are an optional extension (journal revision + stretch), never a place to park core work.

---

## 0. Read this first: what is wrong today

These were found by reading the current prototype (`merton_env.py`, `deep_hedger.py`, `news_regime.py`, `main.py`) and the old roadmap. Items 1–4 mean **the Phase-1 numbers (33.5% CVaR reduction, p < 0.01) cannot go in a paper or be quoted in an interview as evidence.** A quant interviewer will find these in five minutes; fixing them is Phase 0.

### 0.1 Loopholes in the current prototype

| # | Loophole | Why it invalidates the result | Fix (phase) |
|---|---|---|---|
| 1 | **The tautology is still there.** `MertonJumpEnv._shock_steps = {2,3,4,10,11}` is hard-coded, and the scripted news stream is DOMINANT at exactly t = 2,3,4,10,11. | The simulator and the news were co-written by hand. "Dynamics Separation" holds in the code path but not in the experiment design. | Randomise event times per path from a latent process; news is a *noisy, delayed observation* of it (P3). |
| 2 | **One news sequence shared by all 1,000 paths**, so `Q_t` is a pure function of `t`, and `tau` (time) is already an input to Arm A. | Arm A could learn the same schedule from `tau` alone. Arm B "wins" largely because 45 full-batch epochs under-train Arm A — an optimisation artifact, not an information effect. | Per-path news; train all arms to convergence with equal budgets; report learning curves (P0/P3). |
| 3 | **Hedging puts are priced with Black–Scholes at a backward-looking IV** that only rises *after* a jump. | Before a scheduled jump the put is mispriced. The policy is buying a cheap option ahead of a known crash — statistical arbitrage, not hedging. Mean P&L of +2.69 in every arm is the symptom. | Price instruments consistently with the simulator's model under Q; remove drift (Buehler et al. 2022); require mean P&L ≈ 0 for a pure hedge (P1). |
| 4 | **Statistics.** p < 0.01 from 5 seeds; 99% CVaR on 300 test paths is the mean of 3 numbers; one torch seed per arm; slide bar chart (−14.8% / −4.1%) does not match the table. | Not a valid test; tail estimates are noise. | ≥ 100k test paths, ≥ 10 training seeds, paired bootstrap CIs on the *difference* (P0). |
| 5 | **Gate 1 was skipped.** News was bolted on before showing the network recovers Black–Scholes delta in the frictionless GBM limit. | Nothing downstream is trustworthy until the plain hedger is verified. | First deliverable of P0/P1. |
| 6 | Policy outputs are clamped (`delta ∈ [0,1]`, `put ∈ [0,1.25]`), train/test split is by path index on one seed, `engine.py` duplicates `main.py` logic with different hyper-parameters. | Hidden priors + two sources of truth. | One package, one config, tests (P0). |

### 0.2 Loopholes in the old roadmap

| # | Loophole | Fix |
|---|---|---|
| 7 | **No data source was ever named.** The whole efficacy claim depends on point-in-time news *and* historical option quotes. | Section 4 below; data access is decided in week 2, not month 13. |
| 8 | **It never says how the replay policy is trained.** You cannot train a deep hedger on one historical path. | Pre-train on a calibrated simulator, fine-tune on rolling historical windows, walk-forward evaluate (P4). |
| 9 | **4–6 hand-picked events cannot support a CVaR claim.** A bootstrap over 5 events is meaningless. | Evaluate on *every* weekly hedging episode over a multi-year frozen test period; events are a rule-defined, pre-registered subset. |
| 10 | **Weak baseline.** "Market-only" Arm A sees only price and one IV number. | Arm A gets the full market information set (IV level/skew/term structure, realised vol, VIX). News must add value *beyond implied vol*, or the finding is "news is a noisy proxy for VIX". |
| 11 | **The premise "news arrives before the price moves" is mostly false at daily frequency** — prices react in seconds. | Restate the hypothesis (Section 1): news regime carries information about *future jump intensity and volatility clustering* not yet in option prices. Test lead/lag explicitly. |
| 12 | **Look-ahead through pretrained models.** An embedding model or LLM trained after an event has "seen the future". | Use an encoder whose training cut-off precedes the test period; LLM used only for human-readable labels, never features. |
| 13 | "Pre-registered strength weights" with no labelled set and no registration mechanism. | Small hand-labelled news-only set (≈ 500 headlines) + protocol frozen as a signed git tag / OSF registration before the test set is opened. |
| 14 | Pace ("a few hours a week"), 24 months, no C++, volatility models only as stretch. | This document. |
| 15 | **Novelty claim.** "Never been done" is not checkable and reviewers punish it. Your own slide cites news/sentiment-conditioned hedging (Yang et al. 2025; Chen & Li 2021/2023). | Claim what is defensible (Section 1.2). Do a systematic related-work search in week 1 and verify every citation, including the 2026 arXiv IDs on the slides. |

---

## 1. Thesis, restated so it survives review

### 1.1 Hypothesis

> **H1.** Conditional on the full market information set (price, realised volatility, implied-volatility surface features), a point-in-time news-regime vector reduces out-of-sample tail hedging loss (CVaR) of a short-option book, net of real transaction costs.
> **H2 (mechanism).** The benefit is increasing in the news signal's informativeness about latent jump intensity and in its lead over option-implied volatility, and vanishes when either is zero.

H2 is tested in simulation, H1 on history. **A clean negative on H1 with H2 mapped out is still a publishable paper** ("how informative would news have to be, and it isn't") — and a far better interview story than an inflated positive.

### 1.2 What you can honestly claim as new

1. A **value-of-information framework** for exogenous text signals in deep hedging: a partially observed jump-intensity model where news is a noisy observation channel, with oracle and filter-based bounds.
2. A **point-in-time news-regime engine** (dual-anchor clustering, novelty, hysteresis) with explicit leakage controls.
3. A **pre-registered historical evaluation** with placebo (shuffled) and latency arms against a strong IV-aware baseline.
4. An open-source **C++/Python library** reproducing every number.

Do not write "first ever" or "groundbreaking" anywhere. Let contribution 1–3 speak.

### 1.3 Evaluation arms (final)

| Arm | Information | Purpose |
|---|---|---|
| A0 | Model delta / delta-gamma hedge (BS, Merton, Bates) | Classical benchmark |
| A | Deep hedger, full market features, no news | Primary control |
| B | A + real point-in-time news regime | Treatment |
| C | A + news block-shuffled across dates (same marginal distribution) | Placebo: capacity / leakage |
| D | A + news lagged by 1, 2, 5 steps | Timing-decay curve |
| E *(sim only)* | A + true latent regime | Oracle upper bound |

Identical architecture, parameter count, epochs, seeds, and hyper-parameter search budget across A–E.

---

## 2. Timeline at a glance

| Phase | Weeks | Duration | Output | Gate |
|---|---|---|---|---|
| **P0** Repair, lock-in, data access | 1–4 | 4 wk | Clean package, valid stats harness, data decision, related-work matrix | G0 |
| **P1** Deep hedging core + volatility models + C++ simulator | 5–12 | 8 wk | Verified hedger under GBM / Heston / Merton / Bates | G1 |
| **P2** Data pipelines + news engine (parallel with P1, P3) | 5–18 | 14 wk | Point-in-time store, validated regime vector | G2 |
| **P3** Coupled news–market simulator + mechanism study | 13–20 | 8 wk | Value-of-information surface (H2) | G3 |
| **P4** Historical replay | 21–34 | 14 wk | Frozen-test result (H1) | G4 |
| **P5** Paper + release | 35–40 | 6 wk | Submission, arXiv, tagged repo | — |
| Float (exams, slips) | — | 6 wk | — | — |
| **Extension** (optional) | months 13–18 | — | Journal revision, stretch items | — |

Start = week of 10 Nov 2026 → week 40 ≈ mid-Aug 2027; with float ≈ end Sept 2027. Write the paper *as you go*: each gate produces its section and figures.

**Team cadence:** 15-min stand-up Mon/Thu; one 60-min review per week where one person's code is adversarially audited for leakage; advisor at every gate plus a monthly one-page written update. Every PR needs a test and Krishiv's review; nothing touching timestamps or evaluation merges without it.

---

## 3. Phases

Each phase lists: goal · work by person · **prerequisites for Krishiv** (math first) · gate with numeric pass criteria.

### P0 — Repair, lock-in, data access (weeks 1–4)

**Goal:** make the existing prototype honest, and remove the two existential risks (data access, novelty overlap) before building anything.

| Krishiv | B (News/Data) | C (Sim/Eval) |
|---|---|---|
| Restructure into a package (`intellihedge/{sim,hedge,news,eval}`), single YAML config, delete the `engine.py` duplicate. Build the evaluation harness: N test paths ≥ 100k, K ≥ 10 seeds, paired bootstrap CI on ΔCVaR. Re-run the prototype under it and record the corrected (likely much smaller) effect. Related-work matrix (≥ 25 papers: method, data, controls, what they do not do). Data decision memo + budget ask to advisor. One-page pre-analysis plan draft. | Git/PR workflow, pytest, pandas. Pull one month of each candidate news source (Section 4); report timestamp precision, duplicates, coverage, licence. | Git/PR workflow, pytest, NumPy/PyTorch basics. Unit tests for `bs_put_price_and_delta` (put–call parity, limits) and `cvar_loss` (against a closed-form normal CVaR). GitHub Actions CI. |

**Prerequisites (Krishiv):**
- *Probability:* conditional expectation, filtrations, martingales, change of measure at the level of Shreve, *Stochastic Calculus for Finance II*, ch. 1–5.
- *Risk measures:* VaR vs CVaR, coherence; Rockafellar & Uryasev (2000) representation `CVaR_α(L) = min_w { w + E[(L−w)⁺]/(1−α) }` — you will train with this form (learnable `w`) instead of `topk`.
- *Statistics:* bootstrap (percentile, paired), standard error of a tail quantile / expected shortfall — understand why 300 paths cannot estimate a 99% CVaR.
- *Paper:* Buehler, Gonon, Teichmann & Wood (2019), end to end, with every equation re-derived.

**Gate G0:** (a) one command reproduces all numbers from a clean clone; (b) corrected prototype numbers written down with CIs; (c) data sources chosen, access confirmed, a sample of each on disk; (d) advisor signs the hypothesis and arms in Section 1; (e) related-work matrix shows the gap you claim actually exists.

---

### P1 — Deep hedging core, volatility models, C++ simulator (weeks 5–12)

**Goal:** a hedger you can defend line by line, on models of increasing realism, with *no news anywhere*.

Model ladder (each rung has its own acceptance test):

1. **GBM**, frictionless → must recover Black–Scholes delta. Then proportional costs → must show a no-trade band consistent with Whalley–Wilmott asymptotics.
2. **Heston** (stochastic volatility) → hedge with underlying + one option; compare with model delta–vega hedge.
3. **Merton** jump-diffusion → compare with Merton delta and the quadratic (minimum-variance) hedge using options.
4. **Bates** (Heston + jumps) → the default simulator from P3 onward.

Instruments are priced under Q **by the same model that generates paths** (Merton series formula; Heston/Bates via the COS method or Carr–Madan FFT). Train under the risk-neutral / drift-removed measure so the policy cannot earn from drift.

| Krishiv | B | C |
|---|---|---|
| Math spec (LaTeX, becomes paper §3). Policy: recurrent/semi-recurrent net over the full state; objectives: entropic and CVaR (Rockafellar–Uryasev). **C++17 core `libhedge`:** path generators (GBM, Heston QE scheme, Merton, Bates), COS pricer, exposed through pybind11; Google Benchmark vs the NumPy version. | Continues P2 (below). | Classical benchmark hedgers (BS delta, delta–gamma, Whalley–Wilmott band, Merton delta). Arm harness with equal-budget enforcement. Convergence plots. GoogleTest cases for `libhedge` against the Python reference. |

**Prerequisites (Krishiv):**
- *Stochastic calculus:* Itô's formula, Girsanov, Feynman–Kac; BS PDE and Greeks derived by hand (Shreve II ch. 4–6).
- *Jump processes:* Poisson and compound Poisson processes, Itô for jump-diffusions, compensators, why jumps make the market incomplete; Merton (1976) series price. Cont & Tankov, *Financial Modelling with Jump Processes*, ch. 2, 8, 10.
- *Stochastic volatility:* Heston (1993) characteristic function, Feller condition, leverage effect; Bates (1996). Gatheral, *The Volatility Surface*, ch. 1–3.
- *Fourier pricing:* characteristic functions, Carr–Madan (1999), Fang & Oosterlee (2008) COS method.
- *Incomplete-market hedging:* quadratic hedging / minimal-variance (Föllmer–Schweizer), indifference pricing, convex risk measures (Föllmer & Schied ch. 4).
- *Transaction costs:* Leland (1985); Whalley & Wilmott (1997).
- *Monte Carlo:* discretisation bias, variance reduction, Andersen's QE scheme (Glasserman, *Monte Carlo Methods in Financial Engineering*, ch. 3, 4, 6).
- *Deep hedging follow-ups:* Buehler et al. "Learning to Remove the Drift" (2022); Imaki et al. no-transaction-band network (2021).
- *C++:* RAII, templates, `std::span`/`<random>`, Eigen, CMake, pybind11, sanitizers.

**Gate G1 (numeric):**
- GBM frictionless: mean |learned δ − N(d₁)| < 0.02 on a state grid; hedging-error std within 5% of BS delta at equal rebalancing frequency; mean P&L not significantly different from 0.
- With costs: CVaR₉₅ strictly better than BS delta with non-overlapping CIs; visible no-trade band.
- Heston / Merton / Bates: at least matches the best classical benchmark on CVaR₉₅.
- C++ and Python simulators agree in distribution (KS test on terminal prices; prices within MC error); C++ speed-up measured and reported.

Do not start P3 until G1 passes. This is the gate the old plan skipped.

---

### P2 — Data pipelines and news engine (weeks 5–18, B-led, parallel)

**Goal:** an immutable, bi-temporal store and a regime vector validated on news-only evidence.

Pipeline: `ingest → normalise → dedup (MinHash/LSH) → embed → dual-anchor online clustering → novelty → strength → hysteresis → Q_t snapshot`.

Design rules:
- **Bi-temporal records:** `t_event` (if known), `t_pub` (vendor timestamp), `t_seen` (our first capture), `t_avail = max(t_pub, t_seen) + processing latency`. The policy joins on `t_avail` only. Append-only Parquet partitioned by date; queried with DuckDB. No updates, ever — revisions are new rows.
- **Encoder frozen with a cut-off before the test period** (e.g. a 2021-vintage sentence-transformer when the test set starts in 2022). Record model hash.
- **LLM:** offline, cached, labels for human inspection only. Never a feature.
- **Strength weights:** fixed from a ≈ 500-headline hand-labelled set (two annotators, report Cohen's κ) built from the *training* period only. Market data never enters.
- Replace the prototype's bag-of-vocabulary embedding and the 15-headline scripted stream with the real corpus; keep the scripted stream only as a unit-test fixture.

| Krishiv | B | C (from week 13) |
|---|---|---|
| Specify schemas and the `t_avail` join contract; review every threshold. Port dedup + online clustering hot path to C++ once the Python version is validated, and **measure** end-to-end publication-to-feature latency (replaces the "illustrative 420 ms" on the slide). | Ingestion for each source, dedup, embedding, clustering, novelty, hysteresis; clustering-quality report (purity / adjusted Rand vs labelled set); data-provenance appendix. | Property tests: no record with `t_avail` > decision time is ever returned (fuzzed). Market-data loaders, option-chain cleaning (no-arbitrage filters), IV surface fit. |

**Prerequisites (Krishiv):**
- *Linear algebra / geometry:* cosine similarity in high dimension, concentration of distances, why thresholds drift with dimension.
- *Hashing:* MinHash as an unbiased Jaccard estimator, LSH banding S-curve.
- *Online clustering:* leader/DP-means, EMA centroid as a stochastic-approximation update.
- *Information theory:* Shannon entropy (source entropy feature), KL divergence.
- *Point processes (start now, needed in P3):* inhomogeneous Poisson, Hawkes processes, branching ratio (Bacry, Mastromatteo & Muzy 2015).
- *Signal processing:* EMA as a first-order IIR filter, hysteresis / Schmitt trigger, dwell time vs false-switch rate.
- *Validation:* precision/recall, Cohen's κ, adjusted Rand index.
- *Look-ahead bias in language models:* Glasserman & Lin (2023); Sarkar & Vafa (2024).

**Gate G2:** (a) ≥ 5 years of news ingested with the leak test passing; (b) clustering ARI and dedup precision/recall reported on the labelled set; (c) *external validity, descriptive only:* strength spikes align with a pre-listed set of known dates (FOMC, major geopolitical events) drawn from the training period; (d) cleaned option panel with a fitted surface for every training date.

---

### P3 — Coupled news–market simulator and mechanism study (weeks 13–20)

**Goal:** answer H2 and fix loopholes 1–3 properly. This is the section that makes the paper more than an engineering report.

Model (the honest replacement for the hand-aligned schedule):

- Latent regime `Z_t` (2–3 state continuous-time Markov chain, or a Hawkes intensity) drives jump intensity `λ(Z_t)` and vol-of-vol in the Bates simulator.
- **News is a noisy, shifted observation:** `Y_t = h(Z_{t−ℓ}) + noise`, with informativeness `ρ ∈ [0,1]` and lead `ℓ` (ℓ > 0 news leads; ℓ < 0 news lags the market). Sampled independently per path.
- **Option prices carry their own view:** implied vol incorporates a fraction `φ ∈ [0,1]` of the regime information ("market efficiency").
- Sweep `(ρ, ℓ, φ)` → surface of ΔCVaR(B − A). Built-in placebos: at `ρ = 0` or `φ = 1` with no stock-leg benefit, B must equal A within CI. Arm E (oracle `Z`) and a **Wonham/HMM-filter hedger** bound what is achievable.

| Krishiv | B | C |
|---|---|---|
| Derive the model and the filter; implement regime switching in `libhedge`; run the sweep; write paper §4. Calibrate (`λ`, jump sizes, transition rates) to the *training-period* SPX history. | Synthetic news generator emitting the same `Q_t` schema as the real engine, so one policy interface serves both. Finish P2. | Sweep orchestration (Hydra + W&B/MLflow), seeds, bootstrap CIs, heat-map figures. |

**Prerequisites (Krishiv):**
- *Hidden Markov models:* forward algorithm, Baum–Welch; continuous-time Markov chains and generators.
- *Filtering:* Wonham filter for a Markov chain observed in noise; Kalman filter for intuition. (Elliott, Aggoun & Moore, *Hidden Markov Models*, ch. 1–2, or Liptser & Shiryaev at a skim.)
- *Doubly stochastic (Cox) and Hawkes processes:* intensity, compensator, simulation by thinning (Ogata).
- *Regime-switching models:* Hamilton (1989); option pricing under regime switching at a conceptual level.
- *Partially observed control:* separation principle idea — why the filter posterior is a sufficient statistic, which is what the network should approximately learn.
- *Value of information:* Blackwell ordering at a conceptual level.
- *Calibration:* maximum likelihood for jump-diffusions, method of moments, identifiability problems.

**Gate G3:** (a) placebo corners pass (ΔCVaR CI contains 0 at ρ = 0); (b) ΔCVaR monotone in ρ and decaying in lag; (c) deep hedger B lies between A and oracle E and near the filter benchmark; (d) Arm A demonstrably trained to convergence (it cannot be beaten by more epochs alone). If (a) fails you have a leak — stop and find it.

---

### P4 — Historical replay (weeks 21–34)

**Goal:** test H1 once, cleanly.

Design:
- **Book:** every week, short a ≈ 30-day ATM put on the chosen index/ETF; hedge to expiry with the underlying plus one or two liquid listed options; rebalance daily (intraday if the data budget allows). Overlapping episodes → several hundred in total.
- **Costs:** real quoted bid–ask on options, a spread + impact model on the underlying.
- **Splits (walk-forward, example):** train 2015–2019 · validation 2020–2021 · **frozen test 2022–2025**. Test is opened once.
- **Training:** pre-train on the P3 simulator calibrated to the training period → fine-tune on historical training episodes → select on validation only.
- **Events:** rule-defined from an independent proxy (e.g. top-5% days by |ΔVIX| or realised-vol percentile), frozen in the pre-analysis plan. Report both *all episodes* and *event-window episodes*.
- **Statistics:** stationary/block bootstrap (Politis & Romano) over episodes for ΔCVaR; Diebold–Mariano on loss differentials; Hansen SPA / White Reality Check across all variants you tried; Deflated Sharpe-style honesty about the number of configurations.
- **Pre-registration:** pre-analysis plan + code hash as a signed git tag (and OSF if the advisor agrees) before unblinding.

| Krishiv | B | C |
|---|---|---|
| Replay design and all statistical claims; event-driven replay engine (strict timestamp ordering; C++ if P1 C++ is solid, otherwise Python — do not let this block the result); final unblinding with the advisor present. | News/price/quote alignment on one clock (exchange time zone, DST, holidays, half-days); provenance audit; block-shuffle generator for Arm C. | Arms automation, bootstrap/SPA routines, robustness grid (cost levels, rebalancing frequency, CVaR level, top-K narratives). |

**Prerequisites (Krishiv):**
- *Time-series inference:* dependence and why i.i.d. bootstrap fails; block and stationary bootstrap; HAC (Newey–West) standard errors.
- *Forecast/strategy comparison:* Diebold–Mariano; White's Reality Check; Hansen's SPA; multiple testing (Bonferroni, BH-FDR).
- *Backtest overfitting:* Bailey & López de Prado (PBO, Deflated Sharpe); purged/embargoed cross-validation for overlapping labels.
- *Volatility surface practice:* static no-arbitrage conditions, SVI parametrisation, forward/dividend handling, early-exercise premium on ETF options (why index options are cleaner).
- *Realised volatility:* realised variance, bipower variation and the Barndorff-Nielsen–Shephard jump test — a principled independent "jump day" proxy; HAR-RV (Corsi 2009) as a baseline feature.
- *Microstructure basics:* quoted vs effective spread, stale quotes, closing-auction effects.
- *Causal language discipline:* what a placebo test does and does not identify; you are showing *incremental predictive information under controls*, not causation.

**Gate G4:** all arms run on the frozen test exactly once; results, whatever their sign, are written up with CIs. If C ≈ B, report a leak or a capacity effect — that is the finding.

---

### P5 — Paper and release (weeks 35–40)

Drafting is continuous from week 5; this phase is assembly, internal red-team, and submission.

- **Structure:** 1 Introduction · 2 Related work · 3 Deep hedging under jumps and stochastic volatility · 4 News as a noisy observation of latent jump intensity (H2) · 5 Point-in-time news-regime engine · 6 Historical evaluation (H1) · 7 Limitations · Appendices: data provenance, pre-analysis plan, reproducibility.
- **Authorship:** agree order and contributions in writing with the advisor in P0.
- **Venues** (confirm every deadline on the official call; the dates below are historical patterns, not verified for 2027):
  - ACM ICAIF — main-track deadline has typically fallen around early August; workshops later. Week 40 lands right on it, so target the main track only if G4 passes by week 32; otherwise workshop.
  - arXiv (q-fin.CP / q-fin.RM) + SSRN the day you submit — this is what recruiters actually read.
  - Journal for the extension period: *Quantitative Finance*, *Journal of Computational Finance*, *Journal of Financial Data Science*.
- **Release:** tagged repo, one-command reproduction, Docker image, synthetic-data path that runs without licensed data, model/data cards.

---

### Extension (months 13–18, optional)

Journal revision and, in this order: rough-volatility simulator (rBergomi) · multi-asset book with cross-asset narratives · intraday replay · adversarial news (spoofed/duplicated headlines, timestamp manipulation) · C++ inference path with measured tick-to-decision latency.

---

## 4. Data sources

Decide in P0. Verify current coverage, licence, and price for each before committing — do not rely on this table alone.

**News (point-in-time):**

| Source | Why | Caveat |
|---|---|---|
| GDELT 2.0 (GKG / DOC) | Free, global, 15-minute cadence from 2015 | Timestamp is crawl time — acceptable as a conservative `t_seen`; noisy, needs heavy dedup |
| SEC EDGAR filings (8-K etc.) | Free, official acceptance timestamps to the second — the cleanest point-in-time text there is | Company-level, not macro |
| Central-bank and macro releases (FOMC statements, scheduled data) | Free, exactly known release times; ideal for timing tests | Scheduled → partly priced in; label as such |
| FNSPID (open financial-news dataset, ~1999–2023) | Free, large, headline-level | Check timestamp granularity and licence |
| Alpaca / Benzinga, Tiingo news APIs | Timestamped headlines, cheap or free tiers | History depth and redistribution terms vary |
| Refinitiv / RavenPack / Bloomberg | Gold standard | Only via university licence — ask the advisor in week 1 |

**Markets:**

| Need | Options |
|---|---|
| Option chains (the critical dependency) | OptionMetrics IvyDB via WRDS if the university has it · Cboe DataShop · ThetaData / Polygon / Databento (paid, intraday) · OptionsDX-style end-of-day chains for SPX/SPY (cheapest path) · NSE bhavcopy for NIFTY options (free EOD, extremely liquid — viable if US option data is unaffordable, but then the news corpus must cover India) |
| Underlying | Daily: Yahoo/Stooq. Intraday bars: Alpaca / Polygon |
| Vol indices, rates | Cboe (VIX family), FRED (rates) |

**Recommended default:** S&P 500 (SPX/SPY) — news corpus is English and US-centric, options are the most studied, and the 2022–2025 test window contains several distinct stress episodes. Daily rebalancing on end-of-day chains is the core; intraday is an upgrade only if the budget appears. With daily data the claim is about *next-day-and-beyond jump/vol risk beyond implied vol*, not about reacting in milliseconds — say so in the paper.

**Fallback if no affordable option history is obtained by week 4:** hedge with the underlying only plus VIX-future-style proxies, and state the limitation. Do not discover this in month 8.

---

## 5. Tech stack

| Layer | Choice | Note |
|---|---|---|
| Research / training | Python 3.11, PyTorch | Training stays in Python. C++ is not for the network. |
| **Numerical core** | **C++17 `libhedge`** — Eigen, pybind11, CMake, GoogleTest, Google Benchmark | Path generators (GBM / Heston QE / Merton / Bates, regime switching), COS pricer, later dedup + online clustering and the replay engine |
| Data | Parquet + DuckDB, Polars/pandas | Append-only, bi-temporal |
| Text | sentence-transformers (frozen vintage), MinHash/LSH (datasketch → own C++), FAISS only if the corpus needs it | |
| Statistics | NumPy/SciPy, statsmodels, `arch` (bootstrap, SPA) | |
| Experiments | Hydra configs, W&B or MLflow, DVC for data versions | |
| Quality | pytest + hypothesis (leak fuzzing), ruff, mypy, clang-tidy, ASan/UBSan, GitHub Actions | |
| Writing | LaTeX (Overleaf), figures generated by scripts only | |

**On C++ and "HFT":** this is a daily-to-intraday hedging project, not a high-frequency one, and calling it HFT in an interview will backfire. What the C++ honestly demonstrates — and what a quant dev/researcher interviewer wants to see — is a correct, tested, benchmarked numerical library with Python bindings, and a measured low-latency text-to-feature path. Report real speed-ups and latencies; never the illustrative ones.

---

## 6. Risks and cut order

| Risk | Response |
|---|---|
| No affordable option data | Decided by G0; NSE or underlying-only fallback |
| Effect disappears once loopholes 1–4 are fixed (likely to shrink a lot) | H2 mechanism study still stands; negative H1 is reported |
| Krishiv becomes the bottleneck | B owns the news engine end to end by week 10, C owns the eval harness by week 8; Krishiv reviews rather than writes there |
| C++ eats the schedule | C++ is never on the critical path: every component has a validated Python reference first |
| Exams / placements | 6 weeks float; gates move, scope does not |

**If behind, cut in this order:** intraday replay → C++ replay engine (keep Python) → Heston-only rung (go straight to Bates) → second hedging option → C++ news hot path. **Never cut:** G1, the placebo and lag arms, the frozen test, the bootstrap CIs, the strong Arm A.

---

## 7. Core reading list (verify editions/DOIs before citing)

Buehler, Gonon, Teichmann & Wood (2019) *Deep Hedging* · Buehler et al. (2022) *Learning to Remove the Drift* · Imaki et al. (2021) *No-Transaction Band Network* · Merton (1976) · Heston (1993) · Bates (1996) · Carr & Madan (1999) · Fang & Oosterlee (2008) · Whalley & Wilmott (1997) · Rockafellar & Uryasev (2000) · Föllmer & Schied, *Stochastic Finance* · Cont & Tankov, *Financial Modelling with Jump Processes* · Gatheral, *The Volatility Surface* · Glasserman, *Monte Carlo Methods in Financial Engineering* · Shreve, *Stochastic Calculus for Finance II* · Bacry, Mastromatteo & Muzy (2015) *Hawkes Processes in Finance* · Hamilton (1989) · Politis & Romano (1994) · White (2000) · Hansen (2005) · Bailey & López de Prado (2014) · Barndorff-Nielsen & Shephard (2004, 2006) · Corsi (2009) · Glasserman & Lin (2023) · Tetlock (2007) · Ke, Kelly & Xiu (2019) *Predicting Returns with Text Data*.
