"""
IntelliHedge — CLI Runner
Authors: Krishiv Wahi, Kamya Aggarwal, Sarthak Shandiliya

Runs the full pipeline in <15 seconds:
  1. Engine 1  — Point-in-Time News Regime (15-step crisis stream)
  2. Engine 2  — Merton Jump-Diffusion simulation + 4-Arm Causal Ablation
  3. Telemetry — formatted tables for both engines printed to stdout
  4. Dashboard — saves intellihedge_dashboard.png (4-panel, dark-themed)
"""

import time
import os
import numpy as np
import sys

# Force UTF-8 output on Windows so Unicode in matplotlib labels doesn't crash
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import matplotlib
matplotlib.use("Agg")   # non-interactive backend — safe for CLI
import matplotlib.pyplot as plt

from intellihedge.news.regime import PointInTimeNewsEngine, build_crisis_news_stream
from intellihedge.sim.merton import MertonJumpEnv
from intellihedge.hedge.policy import run_causal_ablation
from intellihedge import load_config

CFG = load_config()
SEED = CFG["demo"]["seed"]
np.random.seed(SEED)


# -------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------
DIVIDER_WIDE   = "=" * 92
DIVIDER_NARROW = "-" * 92


def _banner(text: str) -> None:
    print(f"\n{DIVIDER_WIDE}")
    print(f"  {text}")
    print(DIVIDER_WIDE)


# -------------------------------------------------------------------------
# Engine 1 — News Regime
# -------------------------------------------------------------------------
def run_engine1() -> tuple[list, np.ndarray]:
    """Run the news engine over the 15-step stream and return logs + Q_real matrix."""
    engine = PointInTimeNewsEngine(**CFG["news"])
    stream = build_crisis_news_stream()

    regime_logs = []
    for t, batch in enumerate(stream):
        res = engine.step(t, batch)
        regime_logs.append(res)

    # Pretty-print Engine 1 telemetry table
    print("\n[ENGINE 1] Point-in-Time News Regime Trajectory (US-Iran Hormuz Replay)")
    print(f"{'Step':<6} | {'S_k(t)':<10} | {'State':<10} | {'Trend':<8} "
          f"| {'Novelty':<10} | Event Note")
    print(DIVIDER_NARROW)
    for r in regime_logs:
        if r["reignited"]:
            note = "** REIGNITION **"
        elif r["S"] >= 0.75:
            note = "SHOCK CLUSTER"
        elif r["S"] <= 0.30:
            note = "QUIET"
        else:
            note = ""
        print(
            f"t={r['t']:<4} | {r['S']:<10.3f} | {r['state']:<10} | {r['trend']:<8} "
            f"| {r['novelty_mass']:<10.3f} | {note}"
        )

    Q_real = np.stack([r["Q_vec"] for r in regime_logs], axis=0)  # (15, 4)
    return regime_logs, Q_real


# -------------------------------------------------------------------------
# Engine 2 — Market Simulation + Ablation
# -------------------------------------------------------------------------
def run_engine2(Q_real: np.ndarray) -> dict:
    """Simulate Merton paths and run 4-arm causal ablation."""
    env = MertonJumpEnv(n_paths=CFG["demo"]["n_paths"], seed=SEED, **CFG["sim"])
    S, iv, put_mkt = env.simulate()

    results = run_causal_ablation(S, iv, put_mkt, Q_real, **CFG["train"])

    # Pretty-print Engine 2 telemetry table
    print("\n[ENGINE 2] Causal Ablation Benchmark — Out-of-Sample Test Paths")
    print(f"{'Arm':<36} | {'Mean P&L':>9} | {'95% CVaR':>9} | {'99% CVaR':>9} | {'Max Loss':>9}")
    print(DIVIDER_NARROW)
    for res in results.values():
        print(
            f"{res['arm']:<36} | {res['mean_pnl']:>+9.3f} | "
            f"{res['cvar_95']:>9.3f} | {res['cvar_99']:>9.3f} | {res['max_loss']:>9.3f}"
        )
    print(DIVIDER_NARROW)

    arm_a = results["Arm A: Market-Only (Baseline)"]
    arm_b = results["Arm B: News-Aware (IntelliHedge)"]
    arm_c = results["Arm C: Shuffled-News (Placebo)"]
    arm_d = results["Arm D: Latency-Stressed (1-step)"]

    red_95 = (arm_a["cvar_95"] - arm_b["cvar_95"]) / (abs(arm_a["cvar_95"]) + 1e-8) * 100.0
    red_99 = (arm_a["cvar_99"] - arm_b["cvar_99"]) / (abs(arm_a["cvar_99"]) + 1e-8) * 100.0
    print(f"  --> Tail-Risk (95% CVaR) reduction -- Arm B vs A : {red_95:+.1f}%")
    print(f"  --> Max Loss reduction        -- Arm B vs A : {((arm_a['max_loss'] - arm_b['max_loss'])/arm_a['max_loss']*100):+.1f}%")
    print(f"  --> Placebo check (Arm C vs B): 95% CVaR {arm_c['cvar_95']:.3f} vs {arm_b['cvar_95']:.3f} (destroys causal timing)")
    print(f"  --> Latency cost  (Arm D vs B): 95% CVaR {arm_d['cvar_95']:.3f} vs {arm_b['cvar_95']:.3f} (1-step delay degrades edge)")

    return results


# -------------------------------------------------------------------------
# 4-Panel Dashboard
# -------------------------------------------------------------------------
def save_dashboard(regime_logs: list, results: dict, path: str = "intellihedge_dashboard.png") -> None:
    plt.style.use("dark_background")
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), dpi=140)
    fig.patch.set_facecolor("#0B0F19")
    fig.suptitle(
        "IntelliHedge — Point-in-Time News Narrative Intelligence for Deep Derivatives Hedging",
        fontsize=12, fontweight="bold", color="#F8FAFC", y=0.99,
    )
    for ax in axes.flat:
        ax.set_facecolor("#111827")

    steps     = np.arange(len(regime_logs))
    strengths = [r["S"] for r in regime_logs]

    arm_a = results["Arm A: Market-Only (Baseline)"]
    arm_b = results["Arm B: News-Aware (IntelliHedge)"]
    arm_c = results["Arm C: Shuffled-News (Placebo)"]
    arm_d = results["Arm D: Latency-Stressed (1-step)"]

    # ── Panel 1: Schmitt Trigger & Narrative Strength ──────────────────
    ax1 = axes[0, 0]
    ax1.plot(steps, strengths, marker="o", color="#38BDF8", lw=2.5, label=r"$S_k(t)$")
    ax1.axhline(0.75, color="#EF4444", ls="--", alpha=0.8, label=r"Enter DOMINANT ($H_k=0.75$)")
    ax1.axhline(0.55, color="#F59E0B", ls=":",  alpha=0.8, label=r"Exit to FADING ($L_k=0.55$)")
    ax1.fill_between(
        steps, strengths, 0.75,
        where=(np.array(strengths) >= 0.75),
        color="#EF4444", alpha=0.22,
    )
    # Mark reignition events
    for r in regime_logs:
        if r["reignited"]:
            ax1.axvline(r["t"], color="#A78BFA", ls="-.", lw=1.4, alpha=0.7, label="Reignition")
    ax1.set_title("1. Engine 1 — News Regime Strength & Schmitt Hysteresis",
                  fontsize=10, fontweight="bold", color="#F8FAFC")
    ax1.set_xlabel("Time Step $t$"); ax1.set_ylabel(r"$S_k(t)$")
    ax1.set_ylim(0, 1.05); ax1.legend(loc="lower right", fontsize=7); ax1.grid(alpha=0.12)

    # ── Panel 2: Protective Put Weight Across Time ─────────────────────
    ax2 = axes[0, 1]
    ax2.plot(steps, arm_b["put_trace"], marker="s", color="#10B981", lw=2.5,
             label="Arm B: News-Aware")
    ax2.plot(steps, arm_a["put_trace"], marker="^", color="#94A3B8", ls="--", lw=2.0,
             label="Arm A: Market-Only")
    ax2.plot(steps, arm_c["put_trace"], marker="x", color="#F43F5E", ls=":",  lw=1.8,
             label="Arm C: Shuffled Placebo")
    ax2.plot(steps, arm_d["put_trace"], marker="d", color="#FB923C", ls="-.", lw=1.6,
             label="Arm D: Latency-Stressed")
    ax2.set_title(r"2. Engine 2 — Dynamic Protective Put Weight $q_t^{put}$",
                  fontsize=10, fontweight="bold", color="#F8FAFC")
    ax2.set_xlabel("Time Step $t$"); ax2.set_ylabel("Mean Put Hedge Ratio")
    ax2.legend(loc="upper left", fontsize=7); ax2.grid(alpha=0.12)

    # ── Panel 3: Terminal P&L Tail Histograms ──────────────────────────
    ax3 = axes[1, 0]
    bins = np.linspace(-18, 6, 48)
    ax3.hist(arm_a["pnl_dist"], bins=bins, alpha=0.50, color="#EF4444",
             label=f"Arm A (CVaR99={arm_a['cvar_99']:.2f})")
    ax3.hist(arm_b["pnl_dist"], bins=bins, alpha=0.65, color="#10B981",
             label=f"Arm B (CVaR99={arm_b['cvar_99']:.2f})")
    ax3.axvline(-arm_a["cvar_99"], color="#EF4444", ls="--", lw=2.0)
    ax3.axvline(-arm_b["cvar_99"], color="#10B981", ls="-",  lw=2.0)
    ax3.set_title("3. Out-of-Sample Terminal P&L — Left-Tail Truncation",
                  fontsize=10, fontweight="bold", color="#F8FAFC")
    ax3.set_xlabel("Terminal Hedging P&L ($)"); ax3.set_ylabel("Path Frequency")
    ax3.legend(loc="upper left", fontsize=7); ax3.grid(alpha=0.12)

    # ── Panel 4: 4-Arm CVaR-99 Bar Chart ──────────────────────────────
    ax4 = axes[1, 1]
    labels    = ["Arm A\n(Market-Only)", "Arm B\n(News-Aware)",
                 "Arm C\n(Shuffled)", "Arm D\n(Latency)"]
    cvar99s   = [arm_a["cvar_99"], arm_b["cvar_99"], arm_c["cvar_99"], arm_d["cvar_99"]]
    bar_colors = ["#EF4444", "#10B981", "#F59E0B", "#FB923C"]
    bars = ax4.bar(labels, cvar99s, color=bar_colors, width=0.5)
    for bar in bars:
        yv = bar.get_height()
        ax4.text(
            bar.get_x() + bar.get_width() / 2.0, yv + 0.15,
            f"${yv:.2f}", ha="center", va="bottom", fontweight="bold", fontsize=9,
        )
    ax4.set_title("4. Causal Ablation — 99% CVaR Tail Loss (lower = better)",
                  fontsize=10, fontweight="bold", color="#F8FAFC")
    ax4.set_ylabel("99% CVaR Loss ($)")
    ax4.set_ylim(0, max(cvar99s) * 1.25)
    ax4.grid(axis="y", alpha=0.12)

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.savefig(path, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    print(f"\n[DASHBOARD] Saved → {path}")


# -------------------------------------------------------------------------
# Entry Point
# -------------------------------------------------------------------------
def main():
    t0 = time.perf_counter()

    _banner("INTELLIHEDGE — Point-in-Time News Narrative Intelligence for Deep Derivatives Hedging")

    regime_logs, Q_real = run_engine1()
    results = run_engine2(Q_real)
    save_dashboard(regime_logs, results)

    elapsed = time.perf_counter() - t0
    print(f"\n[OK] Total runtime: {elapsed:.1f}s\n")


if __name__ == "__main__":
    main()

