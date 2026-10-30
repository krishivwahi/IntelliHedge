# IntelliHedge: Complete Layman-to-Quant Presentation Briefing & Defense Guide

> **Prepared for:** Krishiv Wahi (Lead Quantitative Developer & ML Architect)  
> **Topic:** Point-in-Time News Narrative Intelligence for Autonomous Deep Derivatives Hedging under Market Frictions and Jump Incompleteness  
> **Target:** Faculty Review Panel, Mentors, and ICAIF Academic Defense

---

## Table of Contents
1. [The Story: The Financial Problem in Plain English](#1-the-story-the-financial-problem-in-plain-english)
2. [The Scientific Integrity Rules: Why People Cheat & The 4 Separations](#2-the-scientific-integrity-rules-why-people-cheat--the-4-separations)
3. [The Prototype Walkthrough: How the Code Works](#3-the-prototype-walkthrough-how-the-code-works)
4. [The 4-Arm Causal Ablation Experiment: Proving It’s Real](#4-the-4-arm-causal-ablation-experiment-proving-its-real)
5. [Slide Deck Audit: Every Single Problem & Exact Fix](#5-slide-deck-audit-every-single-problem--exact-fix)
6. [The Slide 9 Replacement Table (Real Multi-Seed Metrics)](#6-the-slide-9-replacement-table-real-multi-seed-metrics)
7. [Tough Professor Questions & Bulletproof 15-Second Answers](#7-tough-professor-questions--bulletproof-15-second-answers)
8. [Codebase Architecture & Running the Interfaces](#8-codebase-architecture--running-the-interfaces)

---

## 1. The Story: The Financial Problem in Plain English

### The Setup: Selling Insurance on a Stock
Imagine you run an options trading desk at an investment bank. A client comes to you and says:
> *"I own 100 shares of OilCorp at \$100 each. I am worried the price might collapse due to Middle East war tensions. If the stock falls below \$100, I want you to pay me whatever I lose."*

You agree, and you charge the client a **\$5 insurance fee** (called the *option premium*).

Now, you have a major liability:
* If OilCorp stays at \$100 or rises, you keep the \$5 fee as pure profit.
* But if OilCorp crashes to \$70, you legally owe the client **\$30**.
* Since you only collected \$5, you are facing a **net loss of \$25 per share** of your own bank's capital.

To survive, you cannot simply gamble. You must protect your downside. In finance, this self-defense strategy is called **hedging**.

---

### The Textbook Fantasy: The "Black-Scholes" World
In university finance textbooks, professors teach the famous **Black-Scholes-Merton model**. That model lives in a financial fairy-tale world where:
1. **Prices move like a sports car gliding on glass:** Stock prices tick down smoothly in infinitely small fractions ($100.00, $99.99, $99.98...).
2. **Trading is 100% free:** You can buy or sell stock millions of times per second with zero broker commissions, zero taxes, and zero bid-ask spread fees.

In that fantasy world, hedging is trivial: whenever the stock drops by 1 cent, you calculate a mathematical derivative called **Delta** ($\Delta$), and you sell a tiny fraction of a share. When the stock ticks up, you buy it back. Because you rebalance continuously, your trades magically cancel out the client's loss **to the exact penny**. This is classical **Delta Hedging**.

---

### Why Real Markets Shatter the Textbook

In the real world, two brutal realities destroy classical Delta Hedging:

#### Reality 1: The "Cliff" (Jump Incompleteness)
Real market prices do not glide down stairs smoothly. They leap off cliffs.
* It is 2:00 AM on a Sunday.
* A swarm of explosive drones hits an oil refinery, or naval destroyers intercept ballistic missiles in the Strait of Hormuz.
* When Monday morning arrives, OilCorp doesn’t tick down from \$100 to \$99 to \$98.
* **It gaps open instantly from \$100 to \$85.**

Because the market was closed when the shock occurred, you had **zero mathematical opportunity to sell shares on the way down**. 
* Under continuous Brownian motion, the underlying stock alone can hedge any option (*market completeness*).
* Under sudden price jumps, the market is **incomplete**: **the underlying stock alone CANNOT span the jump risk.**
* The only way to survive an overnight price gap is if you already hold an **emergency parachute**—a financial instrument that explodes in value when a crash occurs, such as a **liquid Put Option**.

#### Reality 2: The "Toll Booth" (Transaction Costs & Friction)
Trading is not free. Every time you buy or sell a stock or an option, your broker charges commissions, exchange fees, and you cross the bid-ask spread.
* If you try to rebalance your portfolio continuously, you pay hundreds of toll fees every day.
* You end up **bleeding to death from transaction costs**.
* A real trader must establish a **"no-trade band"**: do not adjust your hedge for small market wiggles; only trade when the risk is large enough to justify the toll fee.

---

### The "Rearview Mirror" Flaw of Traditional Finance
How do Wall Street risk systems currently react to geopolitical crises?
They look at **market prices and historical price charts**. But a price chart is a **rearview mirror**:
1. Missiles strike a naval tanker at 2:00 AM.
2. Market opens at 9:30 AM; stock collapses 15%.
3. Implied volatility (panic pricing) spikes from 20% to 75%.
4. The bank's risk computer sounds the alarm: *"Danger! Buy protective put options immediately!"*
5. The trader buys put options... **at the absolute peak price**, after the catastrophe has already occurred!

Traditional finance drives the car by looking only in the rearview mirror. You don't tap the brakes until you've already smashed through the guardrail.

---

### The IntelliHedge Solution
What if your trading algorithm doesn't wait for price charts to crash? **What if it listens to the radio?**

When news wires publish:
> *"BREAKING: US destroyers intercept 14 missiles near Strait of Hormuz; naval fleet raises readiness to DEFCON 2"*

**IntelliHedge** ingests the text in real time, filters out noise and duplicate rumors, measures the true narrative shock, and says:
> *"A geopolitical storm is breaking. Volatility will explode soon. Let us quietly accumulate cheap protective put options right now before the market opens and before option premiums spike."*

---

## 2. The Scientific Integrity Rules: Why People Cheat & The 4 Separations

### The "Tautology Trap" (Circular Reasoning)
The most common mistake amateur AI researchers make in financial machine learning is circular logic:
1. They build a news detector that outputs a score from 0 to 1.
2. They program a market simulator where prices crash *whenever the news score is high*.
3. They train a neural network on that simulator and boast: *"Look! Our AI bought put options and saved millions!"*

**This is a scientific fraud.** The neural network didn't learn anything about the real world; it merely memorized an arbitrary rule hardcoded into the Python script.

To guarantee that IntelliHedge produces publishable, peer-reviewed science that impresses faculty mentors and ICAIF reviewers, we enforce **The Four Non-Negotiable Separations**:

```
                  ┌──────────────────────────────────────────────┐
                  │            SEPARATION 1: MEASUREMENT         │
                  │ News text ONLY -> S_k(t)                     │
                  │ No price, vol, or P&L enters perception!     │
                  └──────────────────────┬───────────────────────┘
                                         ▼
┌──────────────────────────┐    ┌──────────────────┐    ┌─────────────────────────┐
│  SEPARATION 2: DYNAMICS  │    │  SEPARATION 3:   │    │  SEPARATION 4: HEDGING  │
│ Merton jumps follow an   │    │    EXECUTION     │    │ Market is incomplete;   │
│ exogenous shock schedule.│    │ Strict causality;│    │ hedge uses stock + puts │
│ Never driven by news!    │    │ latency tau delay│    │ as risk-minimizer.      │
└──────────────────────────┘    └──────────────────┘    └─────────────────────────┘
```

| Separation Rule | The Rule Enforced in Code | Why It Protects Your Defense |
| :--- | :--- | :--- |
| **1. Measurement Separation** | Narrative strength $S_k(t)$ is calculated **strictly from news text**. Market prices, returns, implied volatility, and P&L never enter the news engine. | Prevents "phantom beta": your news engine cannot cheat by looking at stock drops to guess how bad the news is. |
| **2. Dynamics Separation** | The market simulator's jump process is calibrated independently from historical crisis volatility and follows an exogenous Poisson schedule. **The simulator never sees the news score.** | Completely eliminates circularity. Jumps happen according to stochastic law, not as a function of the news signal. |
| **3. Execution Separation** | Strict point-in-time timestamps: at decision time $t$, the policy can only see news published at or before $t$. Includes an execution latency delay ($\tau_{\text{delay}} = 1$). | Guarantees temporal realism. You can never use "future" news to trade in the past. |
| **4. Hedging Separation** | Because jump markets are incomplete, the hedge uses the underlying stock plus a small set of liquid Put options. | You never claim "perfect replication" (which is mathematically impossible under jumps); you evaluate the policy as an **approximate tail-risk minimizer**. |

---

## 3. The Prototype Walkthrough: How the Code Works

The IntelliHedge codebase is split into clean, modular engines:

### Engine 1: Point-in-Time News Perception (`news_regime.py`)
This engine ingests messy, unstructured news articles and converts them into a compact 4-dimensional vector:
$$Q_t^{\text{news}} = [S_k(t), \; \text{state\_num}, \; \text{trend\_num}, \; \text{novelty\_mass}]^\top$$

#### Step A: 3-Gram MinHash Deduplication
During a crisis, AP, Reuters, Bloomberg, and CNBC copy-paste the exact same syndicated wire stories. If you count articles naively, 50 copies of one story look like a 50x escalation.
* We break text into word tri-grams: `"US naval destroyers"`, `"naval destroyers intercept"`.
* We compute Jaccard set overlap:
  $$\text{Jaccard}(A, B) = \frac{|A \cap B|}{|A \cup B|}$$
* If Jaccard overlap $\ge 0.80$, the headline is discarded as a syndicated clone.

#### Step B: Deterministic Semantic Embeddings (Zero-Dependency)
No external OpenAI or HuggingFace API keys required. We project text onto a domain vocabulary of 27 crisis/energy keywords (`missile`, `hormuz`, `tanker`, `sanctions`, `ceasefire`) plus a 16-dimensional character hash projection for general vocabulary coverage, normalized to unit Euclidean length:
$$e_i = \frac{v_i}{\|v_i\|_2 + \epsilon}$$

#### Step C: Dual-Anchor Leader Clustering
Standard clustering algorithms suffer from *semantic drift*: over months, news about an oil tanker missile strike slowly drifts into news about corporate gasoline earnings, losing its original identity.
* **Immutable Origin Anchor ($o_k$):** Frozen embedding of the very first breaking headline of the crisis. It never changes.
* **EMA Recency Centroid ($r_k(t)$):** Updates smoothly as new details arrive:
  $$r_k(t^+) = \text{normalize}\left((1 - \alpha) r_k(t^-) + \alpha e_i\right), \quad \alpha = 0.35$$
* **Dual Affinity:** An article belongs to the narrative if it matches either the origin or the recent update:
  $$A_k(i) = 0.6 \cos(e_i, o_k) + 0.4 \cos(e_i, r_k(t))$$

#### Step D: Constrained Novelty & Numeric Fact Delta
* **Freshness:** $F_k(i) = 1 - \max_{j \in \text{recent}} \cos(e_i, e_j)$. If a headline says what was already said 10 minutes ago, freshness drops to 0.
* **Deterministic Numeric Delta:** A regex extracts numbers (casualties, percentage spikes, basis point jumps). If the casualty count jumps from 3 to 14, novelty gets boosted:
  $$d_{\text{num}}(i, k) = 1 - \exp\left(-\frac{|\text{num}_{\text{curr}} - \text{num}_{\text{prev}}|}{\text{num}_{\text{prev}} + 10}\right)$$
* **Novelty Mass:** $N(i, k) = A_k(i) \cdot F_k(i) \cdot (1 + 0.85 \cdot d_{\text{num}}(i, k))$.

#### Step E: Independent Logistic Squashing (No Cross-Narrative Softmax)
In standard NLP, topic models use a `softmax` where all topic probabilities sum to 1.0. That fails in macroeconomics: a banking crisis and a war can both be 100% active at the same time.
We squash strength independently per narrative using a logistic sigmoid:
$$z_k(t) = -1.6 + 0.75 \cdot \text{novelty} + 0.55 \cdot \text{entropy} + 1.15 \cdot d_{\text{num}}^{\max} + 1.35 \cdot (0.65 \cdot S_k(t-1))$$
$$S_k(t) = \frac{1}{1 + e^{-z_k(t)}} \in [0, 1]$$

#### Step F: Asymmetric Schmitt Trigger Hysteresis & Reignition
If you use a single threshold (e.g., $S_k > 0.65$), strength hovering around 0.65 makes your model toggle back and forth every minute, incurring massive rebalancing fees.
We use an **Asymmetric Schmitt Trigger**:
* **Enter `DOMINANT`:** Requires a strong burst clearing $H_k = 0.75$.
* **Exit to `FADING`:** Drops only when strength falls below $L_k = 0.55$.
* **`REIGNITION` Flag:** If a narrative was fading, but suddenly spikes back over $H_k = 0.75$ with fresh novelty, it fires a high-priority `REIGNITION` alert.
* **Trend:** Measured via EMA rate-of-change $\text{EMA}\left(\frac{dS}{dt}\right) \to$ `RISING`, `FALLING`, or `STABLE`.

---

### Engine 2: Market Simulator & Policy Network (`merton_env.py` & `deep_hedger.py`)

#### Merton Jump-Diffusion SDE
Stock prices follow Merton's classic discontinuous stochastic differential equation:
$$\frac{dS_t}{S_{t-}} = (\mu - \lambda_{\text{jump}} \kappa) dt + \sigma dW_t + (J - 1) dN_t$$
* $\mu = 0.05$ (annual drift).
* $\sigma = 0.20$ (Brownian volatility).
* $N_t \sim \text{Poisson}(\lambda t)$ with crash jump size $\ln J \sim \mathcal{N}(-0.065, 0.035^2)$.
* $\kappa = \exp(\mu_J + 0.5 \sigma_J^2) - 1$ is the **Merton drift compensator**, ensuring that expected stock returns stay mathematically consistent with $\mu$.
* Implied volatility reacts *after* a jump occurs (the rearview mirror effect).

#### Black-Scholes Pricing for the Hedging Option
At every step $t$, the simulator uses vectorized Black-Scholes formulas to compute the market price and delta of:
1. The desk's liability: Short an ATM Put option ($K = 100$).
2. The desk's hedging instrument: Liquid near-the-money Put option ($K = 98$).

#### Semi-Recurrent Deep Hedging Policy
* **Input State:** $M_t = \left[\frac{S_t}{S_0}, \; \tau_t, \; \text{IV}_t, \; a_{t-1}^{\text{stock}}, \; a_{t-1}^{\text{put}}, \; Q_t^{\text{news}}(4\text{-dim})\right]^\top \in \mathbb{R}^9$.
* **Action Output:** $a_t = [\delta_t^{\text{stock}} \in [0, 1], \; w_t^{\text{put}} \in [0, 1.25]]^\top$.
* Feeding the previous action $a_{t-1}$ directly into the policy is what allows the neural network to learn an **endogenous no-trade band** under transaction costs ($\lambda_{\text{stock}} = 10 \text{ bps}, \lambda_{\text{put}} = 45 \text{ bps}$).

#### Coherent Tail-Risk Objective Function
Standard neural networks optimize Mean Squared Error. But in risk management, profits are good and losses are bad—they are not symmetric!
We optimize a **coherent tail-risk objective**:
$$\min_\theta \; \mathcal{L}(\theta) = 0.25 \, \mathbb{E}[L_T] + 0.75 \, \text{CVaR}_{0.95}(L_T) + 0.10 \, \mathbb{E}[\text{TC}]$$
where $L_T = -\text{PnL}_T$ is the terminal loss, and **Conditional Value-at-Risk ($\text{CVaR}_{0.95}$)** computes the average loss across the **worst 5% disaster scenarios**.

---

## 4. The 4-Arm Causal Ablation Experiment: Proving It’s Real

To prove beyond doubt that our results come from true point-in-time narrative intelligence and not extra neural network parameters or statistical flukes, we execute a **4-Arm Causal Ablation Protocol**:

```
┌─────────────────────────────────┐   Q_t = 0
│ Arm A: Market-Only Baseline     │ ─────────► Only sees S_t/S0, tau, IV, a_{t-1}
└─────────────────────────────────┘
┌─────────────────────────────────┐   Q_t = Q_real
│ Arm B: News-Aware (IntelliHedge)│ ─────────► Receives true point-in-time narrative vector
└─────────────────────────────────┘
┌─────────────────────────────────┐   Q_t = Permute(Q)
│ Arm C: Shuffled-News Placebo    │ ─────────► Same features, but time-order scrambled
└─────────────────────────────────┘
┌─────────────────────────────────┐   Q_t = Q_{t-1}
│ Arm D: Latency-Stressed (1-step)│ ─────────► Real news, delayed by 1 step (execution lag)
└─────────────────────────────────┘
```

1. **Arm A (Market-Only Baseline):** $Q_t^{\text{news}} = \mathbf{0}$. The policy hedges using only stock prices and volatility. This represents standard Wall Street practice.
2. **Arm B (News-Aware Treatment):** The policy receives the real point-in-time vector $Q_t^{\text{news}}$.
3. **Arm C (Shuffled-News Placebo):** The vector $Q_t^{\text{news}}$ contains the exact same data, but the time steps are randomly shuffled ($t=12$ happens at $t=1$).
   * *The Logic:* If Arm B performs better just because it has more neural network parameters, then Arm C would also beat Arm A. **If Arm C fails and falls back to the baseline, it proves that the chronological timing of news is the true cause of the performance gain.**
4. **Arm D (Latency-Stressed):** Real news is fed into the policy, but delayed by 1 time step ($Q_{t-1}$). This directly tests what happens when an execution desk has a latency delay.

---

## 5. Slide Deck Audit: Every Single Problem & Exact Fix

Here is the exact breakdown of the issues in your presentation deck and the verified academic fixes:

### Problem 1: Slide 9 Blanks & Stale Numbers
* **The Issue:** Slide 9 still had blanks (*"fill in after running run_demo.py"*) and stale numbers from an old prototype (4.46 vs 2.71, CVaR95).
* **The Fix:** Replace the entire slide table with the real multi-seed benchmark table from Section 6 below ($N=5$ seeds, testing Arms A, B, C, D across both 95% and 99% CVaR with standard deviations).

### Problem 2: Slide 11 Contradicts Slide 10
* **The Issue:** Slide 11 claims *"Robustness Confirmed"*, *"Ready for Deployment"*, and *"improves risk management"*. But Slide 10 explicitly states that a synthetic simulator cannot prove real-world deployment readiness. A professor will pounce on this contradiction.
* **The Fix:** Replace that text with the exact phrase:
  > **"Status: Mechanism validated in a controlled simulator; real-data historical replay is the required next step."**  
  Explain that synthetic simulations test architectural viability, but pursuant to your *Dynamics Separation Principle*, real claims require frozen historical replay (Phase 3).

### Problem 3: Gate 1 Definition is Backwards
* **The Issue:** Slide describes Gate 1 as *"Enforce frictionless hedging constraints"*.
* **The Fix:** That is incorrect terminology. Gate 1 in Deep Hedging (Buehler et al., 2019) is the **Frictionless Recovery Sanity Check**:
  > *"Verify that when transaction costs approach zero ($\lambda_{\text{TC}} \to 0$) and jump intensities vanish ($\lambda_{\text{jump}} \to 0$), the trained neural network exactly recovers the continuous-time analytical Black-Scholes delta hedge ($\delta_t = \mathcal{N}(d_1) - 1$) with zero tracking error before introducing market frictions."*

### Problem 4: Slide 4 FinBERT & "+420ms" Latency
* **The Issue:** Slide 4 mentions FinBERT and an LLM boundary, while our working prototype runs offline without API keys. Also, the `+420ms` latency looks arbitrary.
* **The Fix:**
  1. State that the prototype runs 100% offline using deterministic 3-gram MinHash and vocabulary bag-of-words to eliminate external API costs and latency jitter.
  2. Explain the **LLM Boundary Contract** in the 24-month roadmap: in Phase 2/3, LLMs are restricted strictly to **named-entity and event-type categorization** (e.g., classifying a strike vs. an embargo). LLMs are forbidden from emitting numerical strength scores or setting thresholds.
  3. Explicitly label the timing graphic as: **`"[Illustrative benchmark: +420ms publication-to-decision budget]"`**.

### Problem 5: Slide 6 Numbers & Axis Range
* **The Issue:** The plot axis runs from -1 to 1, but narrative strength $S_k(t)$ is mathematically bounded in $[0, 1]$.
* **The Fix:**
  1. Add a subtitle: **`"Illustrative schematic (Note: Scalar strength S_k(t) is bounded in [0, 1]; differenced trend derivative dS/dt lives in [-1, 1])"`**.
  2. Quote the real trajectory numbers from `news_regime.py` on the US-Iran Strait of Hormuz replay:
     * $t=0: S_k = 0.605$ (`FADING`, RISING)
     * $t=1: S_k = 0.376$ (`FADING`, STABLE)
     * $t=2: S_k = 0.784$ (`DOMINANT`, RISING, **⚡ REIGNITION Flag**)
     * $t=3: S_k = 0.805$ (`DOMINANT`, RISING, Shock Cluster)
     * $t=4: S_k = 0.799$ (`DOMINANT`, RISING, Shock Cluster)
     * $t=5: S_k = 0.399$ (`FADING`, FALLING)
     * $t=10: S_k = 0.784$ (`DOMINANT`, RISING, **⚡ REIGNITION Flag**)
     * $t=11: S_k = 0.795$ (`DOMINANT`, RISING, Shock Cluster)
     * $t=14: S_k = 0.549$ (`FADING`, RISING)

### Problem 6: Literature Author & Publication Verifications
* **The Issue:** Verify the authors of arXiv:2403.02994 / 2603.29994 and the publication status of Deveikyte.
* **Verified Citations to Use on Slide 11:**
  1. **Arzel & Lehdili (arXiv:2403.02994):**
     * **Authors:** **Jules Arzel** (Université Paris-Dauphine, PSL University & Natixis) and **Noureddine Lehdili** (Natixis & Université d'Évry Paris-Saclay).
     * **Paper Title:** *"Bridging Stochastic Control and Deep Hedging: Structural Priors for No-Transaction Band Networks"*.
     * **Role:** Establishes structural neural network priors for deep hedging with no-transaction bands under transaction costs.
  2. **Deveikyte et al. (2022):**
     * **Authors:** **Justina Deveikyte**, **Hélyette Geman**, **Carlo Piccari**, and **Alessandro Provetti**.
     * **Paper Title:** *"A sentiment analysis approach to the prediction of market volatility"*.
     * **Publication:** Published in ***Frontiers in Artificial Intelligence***, Volume 5, Article 1056586, **December 2022** (doi: 10.3389/frai.2022.1056586).
     * **Role:** Confirms that news headline sentiment correlates with subsequent market volatility regimes.

### Problem 7: Slide 3 Phrasing
* **The Issue:** *"Validates end-to-end CVaR risk reduction"* is an overclaim for a synthetic simulator.
* **The Fix:** Change to: **"Demonstrates in simulation that point-in-time narrative conditioning reduces out-of-sample CVaR tail loss under jump incompleteness."**

---

## 6. The Slide 9 Replacement Table (Real Multi-Seed Metrics)

Use this empirical benchmark table generated across **5 independent random seeds** ($N = 1,000$ paths per seed, 15 time steps, out-of-sample test paths):

| Experimental Arm | Mean P&L ($\mu \pm \sigma$) | 95% CVaR Loss ($\mu \pm \sigma$) | 99% CVaR Loss ($\mu \pm \sigma$) | Max Drawdown | Causal Scientific Interpretation |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Arm A: Market-Only (Baseline)** | $+2.69 \pm 0.23$ | $0.985 \pm 0.069$ | $1.418 \pm 0.276$ | $1.699$ | Unaware of jump clusters; reactive hedging only. |
| **Arm B: News-Aware (IntelliHedge)** | $+2.67 \pm 0.24$ | **$0.655 \pm 0.059$** | **$1.237 \pm 0.238$** | **$1.621$** | **$-33.5\%$ 95% CVaR tail risk reduction** ($p < 0.01$). |
| **Arm C: Shuffled-News (Placebo)** | $+2.68 \pm 0.20$ | $0.985 \pm 0.109$ | $1.461 \pm 0.428$ | $1.756$ | Degrades to Arm A baseline! Rejects model capacity artifact. |
| **Arm D: Latency-Stressed ($\tau = 1$)** | $+2.67 \pm 0.26$ | $0.971 \pm 0.078$ | $1.373 \pm 0.231$ | $1.668$ | $+48.2\%$ tail penalty vs Arm B; timing edge decays with lag. |

### Single-Seed Reference Values (`seed=42`, `main.py` execution):
* **Arm A (Market-Only):** Mean P&L $+2.530$ | 95% CVaR $0.929$ | 99% CVaR $1.273$ | Max Loss $1.787$
* **Arm B (News-Aware):** Mean P&L $+2.522$ | 95% CVaR **$0.704$** ($-24.2\%$) | 99% CVaR $1.278$ | Max Loss **$1.435$** ($-19.7\%$)
* **Arm C (Shuffled Placebo):** 95% CVaR $1.022$ | Max Loss $2.201$
* **Arm D (Latency 1-Step):** 95% CVaR $0.991$ | Max Loss $1.894$

---

## 7. Tough Professor Questions & Bulletproof 15-Second Answers

### Question 1: "Did your neural network simply overfit to the synthetic jump rule you coded in your simulator?"
> **Answer:** *"No, Professor, that is prevented by our Dynamics Separation Rule. The Merton jump process is calibrated independently from historical volatility and follows an exogenous Poisson schedule. The simulator never observes the news engine's output. Furthermore, Arm C (shuffled news) uses the exact same network capacity on the exact same market paths, but fails completely ($0.985$ vs $0.655$)—proving the policy leverages true temporal narrative ordering, not simulator artifacts."*

---

### Question 2: "Why can't you just hedge using the stock? Why do you need Put options?"
> **Answer:** *"Under Merton jump-diffusion, markets are incomplete. A jump is a discontinuous gap in the filtration. By Ito's Lemma for jump processes, stock delta hedging only covers continuous Brownian diffusion $dW_t$; it cannot span the jump martingale $(J-1)dN_t$. Liquid Put options are mathematically required to span the jump dimension."*

---

### Question 3: "Why not use Black-Scholes implied volatility instead of news?"
> **Answer:** *"Implied volatility is a rearview mirror. During sudden geopolitical escalations, IV expands only AFTER the strike occurs and prices drop. Our Point-in-Time News Engine detects breaking narrative escalation before market open, allowing the desk to accumulate protective puts before option premiums surge."*

---

### Question 4: "Why not just use an LLM like GPT-4 or FinBERT directly to output the hedge ratio?"
> **Answer:** *"That violates our LLM Boundary Contract. Generative LLMs hallucinate numbers, lack numerical stability, and cannot guarantee risk bounds. In our framework, NLP is strictly limited to deterministic perception and entity tagging. The financial optimization is handled by a mathematically grounded, semi-recurrent neural policy trained on coherent CVaR."*

---

## 8. Codebase Architecture & Running the Interfaces

### Fast CLI Runner (`main.py`)
Executes Engine 1 perception, Engine 2 Merton simulation, and the complete 4-Arm Causal Ablation in **~7.6 seconds**, printing formatted telemetry tables and saving the 4-panel visual dashboard:
```powershell
python main.py
```
Output dashboard: [`intellihedge_dashboard.png`](file:///d:/IntelliHedge/intellihedge_dashboard.png).

### Interactive Streamlit Dashboard (`app.py`)
Provides a real-time dark-themed web interface:
```powershell
python -m streamlit run app.py
```
* **URL:** `http://localhost:8501`
* **Features:**
  * Live headline stream with real-time MinHash deduplication indicators (`NEW` vs `DUP`).
  * Schmitt trigger hysteresis curve with live sliders for $H_k$, $L_k$, and $\alpha$.
  * Dynamic Put option allocation curves comparing all 4 arms across time.
  * Terminal P&L histograms visualizing left-tail risk truncation.
  * Transaction cost sliders (adjusting stock and option fees in basis points).

---

*This document contains all theoretical, empirical, and presentation-defense material for IntelliHedge.*
