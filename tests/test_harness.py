import numpy as np
from scipy.stats import norm

from intellihedge.eval.harness import cvar, paired_bootstrap


def test_cvar_matches_normal_closed_form():
    x = np.random.default_rng(0).standard_normal(2_000_000)
    for a in (0.95, 0.99):
        assert abs(cvar(x, a) - norm.pdf(norm.ppf(a)) / (1 - a)) < 0.01


def test_bootstrap_ci_covers_zero_for_identical_arms_and_detects_a_shift():
    rng = np.random.default_rng(1)
    x = rng.standard_normal((4, 20_000))
    noise = 0.01 * rng.standard_normal(x.shape)
    _, lo, hi = paired_bootstrap(x + noise, x, 200, rng)[0.95]
    assert lo < 0 < hi
    _, lo, hi = paired_bootstrap(x - 0.2, x, 200, rng)[0.95]
    assert hi < 0
