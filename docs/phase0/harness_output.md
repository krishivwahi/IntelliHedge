
### epochs = 45 · 10 training seeds x 20,000 train paths · 100,000 shared test paths

| Arm | Mean P&L | CVaR95 (mean ± SD over seeds) | CVaR99 (mean ± SD over seeds) |
|---|---|---|---|
| Arm A | +2.685 | 0.968 ± 0.042 | 1.353 ± 0.173 |
| Arm B | +2.691 | 0.673 ± 0.035 | 1.168 ± 0.054 |
| Arm C | +2.671 | 0.870 ± 0.129 | 1.302 ± 0.139 |
| Arm D | +2.628 | 0.946 ± 0.025 | 1.264 ± 0.100 |

| Difference (negative = first arm has less tail loss) | ΔCVaR95 [95% CI] | ΔCVaR99 [95% CI] |
|---|---|---|
| Arm B − Arm A | -0.294 [-0.333, -0.260] | -0.184 [-0.313, -0.069] |
| Arm C − Arm A | -0.098 [-0.173, -0.027] | -0.051 [-0.163, +0.059] |
| Arm D − Arm A | -0.022 [-0.050, +0.001] | -0.089 [-0.201, +0.007] |
| Arm B − Arm C | -0.197 [-0.264, -0.132] | -0.134 [-0.223, -0.059] |
| Arm B − Arm D | -0.272 [-0.299, -0.248] | -0.095 [-0.170, -0.030] |

### epochs = 400 · 10 training seeds x 20,000 train paths · 100,000 shared test paths

| Arm | Mean P&L | CVaR95 (mean ± SD over seeds) | CVaR99 (mean ± SD over seeds) |
|---|---|---|---|
| Arm A | +3.969 | 0.254 ± 0.050 | 1.060 ± 0.103 |
| Arm B | +4.725 | 0.307 ± 0.056 | 1.088 ± 0.113 |
| Arm C | +4.338 | 0.321 ± 0.102 | 1.068 ± 0.146 |
| Arm D | +3.811 | 0.360 ± 0.250 | 1.068 ± 0.119 |

| Difference (negative = first arm has less tail loss) | ΔCVaR95 [95% CI] | ΔCVaR99 [95% CI] |
|---|---|---|
| Arm B − Arm A | +0.054 [+0.014, +0.095] | +0.027 [-0.049, +0.110] |
| Arm C − Arm A | +0.067 [+0.013, +0.134] | +0.008 [-0.089, +0.111] |
| Arm D − Arm A | +0.107 [-0.005, +0.277] | +0.008 [-0.086, +0.078] |
| Arm B − Arm C | -0.014 [-0.058, +0.037] | +0.019 [-0.066, +0.125] |
| Arm B − Arm D | -0.053 [-0.203, +0.049] | +0.019 [-0.080, +0.120] |
