# Related-Work Matrix (Phase 0, draft 1)

**Status column:** `V` = existence, title and authors confirmed by web search on 10 Nov 2026 (abstract-level only; the full paper was *not* read). `U` = written from memory, **must be checked against the source before it is cited**. Nobody on the team should cite a row until its status is `R` (read in full by a named person).

**How this was built:** 11 web searches plus prior knowledge. arXiv, SSRN and Google Scholar could not be opened directly from the session, so this is a starting matrix, not a systematic review. Krishiv still owes: a Google Scholar forward-citation pass on rows 1, 12, 19 and 23, and an SSRN search for "news" + "hedging".

## A. Deep hedging: method

| # | Paper | Status | Method | Data | Controls | What it does not do |
|---|---|---|---|---|---|---|
| 1 | Buehler, Gonon, Teichmann, Wood (2019), *Deep Hedging*, Quantitative Finance; arXiv:1802.03042 | V | Neural policy minimising a convex risk measure under frictions | Simulated (Heston) | Model-delta benchmark | **Explicitly says the feature set may include "news analytics"** but never tests it |
| 2 | Buehler, Murray, Pakkanen, Wood (2021), *Learning to Remove the Drift…*, arXiv:2111.07844 | V | Minimal equivalent near-martingale measure so the hedge cannot earn from drift | Simulated | — | No exogenous signals |
| 3 | Imaki, Imajo, Ito, Minami, Nakagawa (2021), *No-Transaction Band Network*, arXiv:2103.01775 | V (authors U) | Architecture that outputs a no-trade band | Simulated | BS delta, plain MLP | No jumps, no signals |
| 4 | Arzel, Lehdili (2026), *Bridging Stochastic Control and Deep Hedging: Structural Priors for No-Transaction Band Networks*, arXiv:2603.29994 | V | Whalley–Wilmott band as a structural prior | Simulated | Stochastic-control bands | Log-normal assumption; no jumps, no signals |
| 5 | Horvath, Teichmann, Žurić (2021), *Deep Hedging under Rough Volatility*, arXiv:2102.01962 | V (authors U) | Deep hedging under rough Bergomi | Simulated | Model hedge | No jumps, no signals |
| 6 | Carbonneau (2021), *Deep Hedging of Long-Term Financial Derivatives*, Insurance: Math. & Econ.; arXiv:2007.15128 | V (author U) | Global hedging with equity jump risk | Simulated | Quadratic vs non-quadratic | No signals |
| 7 | Agram, Øksendal, Rems (2024), *Deep learning for quadratic hedging in incomplete jump market*, arXiv:2407.13688 | V | Minimal-variance hedging in jump-diffusion with NN/LSTM | Simulated | Analytical solution | No transaction-cost/tail focus, no signals |
| 8 | *Constrained deep learning for pricing and hedging European options in incomplete markets*, arXiv:2511.20837 | V (authors unknown) | Robustness of a deep hedger to volatility-jump "regime shifts" and mis-specified intensity | Simulated | Intensity mis-specification | Regime is not observed through any signal |
| 9 | Cao, Chen, Hull, Poulos (2021), *Deep Hedging of Derivatives Using Reinforcement Learning*, J. Financial Data Science | U | RL hedging with costs | Simulated | Delta hedge | No signals |
| 10 | Kolm, Ritter (2019), *Dynamic Replication and Hedging: A Reinforcement Learning Approach*, J. Financial Data Science | U | RL replication with costs | Simulated | Delta hedge | No signals |
| 11 | François, Gauthier, Godin (2014), *Optimal hedging when the underlying asset follows a regime-switching Markov process*, EJOR | V (venue U) | Dynamic-programming hedge under regime switching | Simulated + calibrated | — | Regime inferred from prices only; no neural policy |

## B. Deep hedging: real data

| # | Paper | Status | Method | Data | Controls | What it does not do |
|---|---|---|---|---|---|---|
| 12 | Chen, Li (2021/2023), *Data-driven Hedging of Stock Index Options via Deep Learning*, Operations Research Letters 51(4):408–413; arXiv:2111.03477 | V | NN hedge ratio from maturity, BS delta and a "sentiment" variable | S&P 500 options, OptionMetrics, 2010–2019 | BS delta, prior data-driven model | **"Sentiment" is VIX (calls) / index return (puts), not text.** No news, no placebo |
| 13 | Ruf, Wang (2022), *Hedging with Linear Regressions and Neural Networks*, J. Business & Economic Statistics | U | One-period hedge-ratio learning; warns about leakage in option panels | S&P 500, Euro Stoxx options | Linear benchmark, leakage discussion | No signals |
| 14 | Mikkilä, Kanniainen (2023), *Empirical Deep Hedging*, Quantitative Finance | V (mention only) | RL trained directly on historical index options | S&P 500 options | Delta hedge, costs | No signals |
| 15 | François, Gauthier, Godin, Pérez-Mendoza (2025), deep hedging on an implied-volatility surface, arXiv:2504.06208 | V (title U) | Deep hedging of index option portfolios with IV-surface state | Train 1996–2020, test straddles 2020–2023 | Delta–gamma, costs | No text signal. **Closest design to our Arm A; read first** |
| 16 | Bracha, Michańków, Sakowski (2025), *Application of Deep Reinforcement Learning to At-the-Money S&P 500 Options Hedging*, arXiv:2510.09247 | V | TD3 on ~30-day ATM calls, walk-forward | S&P 500, ~17 years out of sample | BS delta | No text signal |
| 17 | Zernikov (2026), *What Does Deep Hedging Actually Learn? Delta Corrections, Regime Fragility, and Symbolic Distillation*, arXiv:2605.21696 | V | TD3 vs daily BS delta, walk-forward 2015–2023, symbolic distillation | S&P 500 options | BS delta | Finds gains are regime-dependent (2022 hurts) but does not condition on any regime signal |
| 18 | Kumar (2026), *Deep Hedging Under Realistic Market Frictions: A Regime-Conditional Empirical Study… Bitcoin Options*, arXiv:2608.29025 | V | Deep hedging vs classical on Deribit 2020–2024, results split by regime | BTC options | Classical baselines | Regimes are an evaluation split, not a policy input from news |
| 19 | *Deep delta hedging on residuals*, arXiv:2407.19367 | V (title/authors U) | Learn residual to BS delta with extra features | Index options | Feature ablation | Reports market sentiment as *less* important — a counter-result to cite honestly |

## C. News or text combined with hedging or option pricing (nearest neighbours)

| # | Paper | Status | Method | Data | Controls | What it does not do |
|---|---|---|---|---|---|---|
| 20 | Yang et al. (2025), *Dynamic Hedging Strategies in Derivatives Markets with LLM-Driven Sentiment and News Analytics*, arXiv:2504.04295 (cs.CL) | V | LLM sentiment from news/social media adjusts hedging positions | Text + market data (details unread) | Static-hedge comparison (per abstract) | **Our closest competitor. Must be read in full.** From the abstract: no placebo/shuffled-news arm, no lag arm, no point-in-time discipline stated, LLM look-ahead not addressed — all unconfirmed until read |
| 21 | *Deep gg-Pricing for CSI 300 Index Options with Volatility Trajectories and Market Sentiment*, arXiv:2601.18804 | V (authors unknown) | Option pricing net with text-derived sentiment; hedge ratio by autodiff | CSI 300 options | — | Pricing-first; no dynamic hedging policy, no placebo |

## D. News, volatility and jumps (evidence for or against the premise)

| # | Paper | Status | Finding | Relevance |
|---|---|---|---|---|
| 22 | He (2026), *Interpretable Systematic Risk around the Clock*, arXiv:2604.13458 | V | Links systematic jumps to Dow Jones Newswires 1997–2020; ~70% of systematic jumps occur overnight | Overnight jumps cannot be hedged intraday — a limit on what news can buy us; must be discussed |
| 23 | Glasserman, Mamaysky (2019), *Does Unusual News Forecast Market Stress?*, JFQA | V (venue U) | News measures forecast volatility; information "not fully reflected in contemporaneous option prices" | **The strongest prior support for H1** |
| 24 | Jeon, McCurdy, Zhao (2022), *News as sources of jumps in stock returns*, J. Financial Economics 145(2) | V (title U) | News-flow measures relate to jump intensity and jump-size distribution; 21M articles, 9,000 firms | Supports the P3 model: news as an observation of latent jump intensity |
| 25 | Cao, Han, Li, Yang, Zhan, *Forecasting Option Returns with News* | V (mention only) | Media coverage predicts future changes in volatility / option returns | Support for H1 at firm level |
| 26 | Deveikyte, Geman, Piccari, Provetti (2020), *A Sentiment Analysis Approach to the Prediction of Market Volatility*, arXiv:2012.05906 | V (arXiv) | Sentiment correlates with next-day volatility; strongest in tweets | Journal version (Frontiers in AI) on the slide was **not** confirmed by search |
| 27 | Manela, Moreira (2017), *News Implied Volatility and Disaster Concerns*, J. Financial Economics | U | Text-based "NVIX" tracks disaster risk | Text carries tail-risk information |
| 28 | Baker, Bloom, Davis, Sammon, *What Triggers Stock Market Jumps?* | U | Human-coded news causes of large daily moves | Independent event labels |
| 29 | Bybee, Kelly, Manela, Xiu, *Business News and Business Cycles*, J. Finance | U | Topic-model news attention series | Narrative-attention precedent for our strength signal |
| 30 | Tetlock (2007), *Giving Content to Investor Sentiment*, J. Finance | U | Media pessimism predicts returns/volume | Classic |
| 31 | Ke, Kelly, Xiu (2019), *Predicting Returns with Text Data* | U | Supervised sentiment from text | Benchmark text method |
| 32 | Lee, Mykland (2008), *Jumps in Financial Markets*, Review of Financial Studies | U | Non-parametric jump test; jumps associated with news | Independent jump-day proxy |

## E. Methodological hazards

| # | Paper | Status | Why it matters |
|---|---|---|---|
| 33 | Glasserman, Lin (2023), look-ahead bias in LLM sentiment | U | A model trained after the event has seen the outcome |
| 34 | Sarkar, Vafa (2024), *Lookahead Bias in Pretrained Language Models* | U | Same hazard; motivates the frozen-vintage encoder |
| 35 | Bailey, López de Prado (2014), *The Deflated Sharpe Ratio* | U | Multiple-testing discipline for backtests |
| 36 | Politis, Romano (1994), *The Stationary Bootstrap*, JASA | U | Dependent-data confidence intervals |

## The gap, stated carefully

No paper found in this search does all three of:

1. feeds a **point-in-time, text-derived regime signal** into a **deep hedging policy** (rows 20–21 come closest; row 1 anticipated it);
2. tests it with **placebo (shuffled) and lag arms** against a baseline that already sees implied volatility;
3. explains *when* it should work with a **partially observed jump-intensity model**.

This supports "to our knowledge, the first to combine (1)–(3)", **conditional on reading row 20 in full**. It does not support "nobody has combined news with hedging": rows 1, 12, 20 and 21 all touch it. Rows 19 and 22 are evidence *against* an easy win and belong in the paper.

## Audit of the seven citations on the Phase-1 slide

| Slide entry | Verdict |
|---|---|
| Buehler et al. (2019), Deep Hedging | Correct. |
| Yang et al. (2025), arXiv:2504.04295 | Exists. Full title is *Dynamic Hedging Strategies in Derivatives Markets with LLM-Driven Sentiment and News Analytics*. Listed under cs.CL, not q-fin. |
| Chen & Li (2021 preprint), arXiv:2111.03477 | Exists; ORL 51(4), 2023. **Fix the description:** their "market sentiment" is VIX / index return, not news. It cannot be cited as evidence that news improves hedging. |
| He (2026), arXiv:2604.13458 | Exists, posted 15 Apr 2026. |
| Buehler et al. (2021), arXiv:2111.07844 | Exists; authors Buehler, Murray, Pakkanen, Wood. |
| Arzel & Lehdili (2026), arXiv:2603.29994 | Exists, posted 31 Mar 2026. |
| Deveikyte et al. (2020/2022), arXiv:2012.05906 | arXiv version exists. The Frontiers DOI on the slide was not confirmed — open the DOI and check. |
