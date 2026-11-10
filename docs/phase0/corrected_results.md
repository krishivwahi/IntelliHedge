# Corrected Phase-1 Results

Reproduce: `python -m intellihedge.eval.harness` (about 45 minutes on 4 CPU cores). Raw output: `harness_output.md`.

## What changed in the evaluation (and what did not)

Changed: 10 independent training seeds × 20,000 training paths; one shared test set of 100,000 fresh paths; CVaR differences reported with 95% paired-bootstrap intervals (training seeds and test paths both resampled, 1,000 replicates).

**Not changed:** the simulator, the scripted news stream, the option pricing, the network. The design flaws listed in `ROADMAP.md` §0.1 (items 1–3) are still present. These numbers correct the *statistics and the training budget only*.

Loss units are dollars per short put on a $100 underlying. Negative difference = first arm has less tail loss.

## Result 1 — at the prototype's 45 epochs, the effect looks real

| Arm | Mean P&L | CVaR95 | CVaR99 |
|---|---|---|---|
| A market-only | +2.685 | 0.968 ± 0.042 | 1.353 ± 0.173 |
| B news-aware | +2.691 | 0.673 ± 0.035 | 1.168 ± 0.054 |
| C shuffled news | +2.671 | 0.870 ± 0.129 | 1.302 ± 0.139 |
| D lagged news | +2.628 | 0.946 ± 0.025 | 1.264 ± 0.100 |

| Difference | ΔCVaR95 [95% CI] | ΔCVaR99 [95% CI] |
|---|---|---|
| B − A | −0.294 [−0.333, −0.260] | −0.184 [−0.313, −0.069] |
| C − A | −0.098 [−0.173, −0.027] | −0.051 [−0.163, +0.059] |
| B − C | −0.197 [−0.264, −0.132] | −0.134 [−0.223, −0.059] |

B beats A by about 30% on CVaR95, close to the slide's 33.5%. But the shuffled placebo also beats A, which a valid placebo should not.

## Result 2 — train every arm to convergence (400 epochs) and the effect is gone

| Arm | Mean P&L | CVaR95 | CVaR99 |
|---|---|---|---|
| A market-only | +3.969 | 0.254 ± 0.050 | 1.060 ± 0.103 |
| B news-aware | +4.725 | 0.307 ± 0.056 | 1.088 ± 0.113 |
| C shuffled news | +4.338 | 0.321 ± 0.102 | 1.068 ± 0.146 |
| D lagged news | +3.811 | 0.360 ± 0.250 | 1.068 ± 0.119 |

| Difference | ΔCVaR95 [95% CI] | ΔCVaR99 [95% CI] |
|---|---|---|
| B − A | **+0.054 [+0.014, +0.095]** | +0.027 [−0.049, +0.110] |
| C − A | +0.067 [+0.013, +0.134] | +0.008 [−0.089, +0.111] |
| D − A | +0.107 [−0.005, +0.277] | +0.008 [−0.086, +0.078] |
| B − C | −0.014 [−0.058, +0.037] | +0.019 [−0.066, +0.125] |

## What this means

1. **The market-only arm was under-trained.** Its CVaR95 falls from 0.968 to 0.254 with more epochs — a far bigger improvement than news ever gave. In this simulator the shocks happen at fixed steps and the policy sees the time step, so it learns the schedule without news.
2. **Once converged, news does not help.** Arm B is slightly *worse* than Arm A on CVaR95 and indistinguishable on CVaR99. Real and shuffled news are indistinguishable from each other.
3. **The Phase-1 headline was a training-speed effect:** the news vector is a convenient shortcut to the schedule, so Arm B gets there in fewer epochs. That is not evidence that news carries hedging information.
4. **Every arm makes money on average** (+2.6 to +4.7 on a put whose premium is roughly 2.5), and more as training continues. A pure hedge should average near zero. The policies are harvesting the mispriced options and the drift, as flagged in roadmap item 3.

## What can and cannot be said

- Can: "The pipeline runs end to end; a corrected evaluation showed our first result was an artifact, and we identified why."
- Cannot: "News-aware hedging reduces tail loss by 33%", or any p-value from the Phase-1 slides.

This prototype cannot test the hypothesis in either direction, because news here carries no information the time step does not already carry. The test begins with the Phase 3 simulator (randomised event times, news as a noisy observation of hidden jump risk) and the Phase 4 historical replay.

## Caveats

- 400 epochs was chosen as "clearly more than 45", not by a convergence criterion; learning curves are Phase 1 work.
- Full-batch training, one learning rate, no hyper-parameter search per arm.
- Arm D's CVaR95 varies a lot across seeds at 400 epochs (SD 0.250), so its comparisons are loose.
