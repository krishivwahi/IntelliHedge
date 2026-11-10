"""
Evaluation harness: every arm is trained on `seeds` independent training sets and scored
on one shared, large test set, so arm differences are paired path-by-path.

    python -m intellihedge.eval.harness            # prototype epochs, then converged epochs
    python -m intellihedge.eval.harness --epochs 45
"""

import argparse
import contextlib
import io
import math

import numpy as np

from intellihedge import load_config
from intellihedge.hedge.policy import run_causal_ablation
from intellihedge.news.regime import PointInTimeNewsEngine, build_crisis_news_stream
from intellihedge.sim.merton import MertonJumpEnv

ALPHAS = (0.95, 0.99)


def cvar(losses: np.ndarray, alpha: float) -> np.ndarray:
    """Mean of the worst (1 - alpha) fraction along the last axis."""
    k = max(1, math.ceil((1.0 - alpha) * losses.shape[-1]))
    return np.partition(losses, -k, axis=-1)[..., -k:].mean(axis=-1)


def paired_bootstrap(loss_x: np.ndarray, loss_y: np.ndarray, n_boot: int, rng) -> dict:
    """
    CI for mean-over-seeds CVaR(x) - CVaR(y). Inputs are (n_seeds, n_test) losses on the
    SAME test paths. Each replicate resamples training seeds and test paths, using the same
    indices for both arms, so training-seed and test-sampling noise are both in the interval.
    """
    n_seeds, n_test = loss_x.shape
    reps = {a: np.empty(n_boot) for a in ALPHAS}
    for b in range(n_boot):
        s = rng.integers(n_seeds, size=n_seeds)[:, None]
        p = rng.integers(n_test, size=n_test)[None, :]
        x, y = loss_x[s, p], loss_y[s, p]
        for a in ALPHAS:
            reps[a][b] = (cvar(x, a) - cvar(y, a)).mean()
    return {
        a: ((cvar(loss_x, a) - cvar(loss_y, a)).mean(), *np.percentile(reps[a], [2.5, 97.5]))
        for a in ALPHAS
    }


def run(cfg: dict, epochs: int) -> None:
    ev = cfg["eval"]
    engine = PointInTimeNewsEngine(**cfg["news"])
    Q_real = np.stack([engine.step(t, b)["Q_vec"] for t, b in enumerate(build_crisis_news_stream())])
    test = MertonJumpEnv(n_paths=ev["n_test"], seed=ev["test_seed"], **cfg["sim"]).simulate()

    losses, pnl = {}, {}
    for seed in ev["seeds"]:
        train = MertonJumpEnv(n_paths=ev["n_train"], seed=seed, **cfg["sim"]).simulate()
        with contextlib.redirect_stdout(io.StringIO()):
            res = run_causal_ablation(*train, Q_real, epochs=epochs, lr=cfg["train"]["lr"], seed=seed, test=test)
        for arm, r in res.items():
            losses.setdefault(arm[:5], []).append(r["loss"])
            pnl.setdefault(arm[:5], []).append(r["mean_pnl"])
    losses = {k: np.stack(v) for k, v in losses.items()}

    print(f"\n### epochs = {epochs} · {len(ev['seeds'])} training seeds x {ev['n_train']:,} train paths · "
          f"{ev['n_test']:,} shared test paths\n")
    print("| Arm | Mean P&L | CVaR95 (mean ± SD over seeds) | CVaR99 (mean ± SD over seeds) |")
    print("|---|---|---|---|")
    for arm, L in losses.items():
        c95, c99 = cvar(L, 0.95), cvar(L, 0.99)
        print(f"| {arm} | {np.mean(pnl[arm]):+.3f} | {c95.mean():.3f} ± {c95.std(ddof=1):.3f} "
              f"| {c99.mean():.3f} ± {c99.std(ddof=1):.3f} |")

    rng = np.random.default_rng(0)
    print("\n| Difference (negative = first arm has less tail loss) | ΔCVaR95 [95% CI] | ΔCVaR99 [95% CI] |")
    print("|---|---|---|")
    for x, y in (("Arm B", "Arm A"), ("Arm C", "Arm A"), ("Arm D", "Arm A"), ("Arm B", "Arm C"), ("Arm B", "Arm D")):
        ci = paired_bootstrap(losses[x], losses[y], ev["n_boot"], rng)
        print(f"| {x} − {y} | " + " | ".join(f"{d:+.3f} [{lo:+.3f}, {hi:+.3f}]" for d, lo, hi in ci.values()) + " |",
              flush=True)


if __name__ == "__main__":
    cfg = load_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, nargs="*",
                    default=[cfg["train"]["epochs"], cfg["eval"]["epochs_converged"]])
    for e in ap.parse_args().epochs:
        run(cfg, e)
