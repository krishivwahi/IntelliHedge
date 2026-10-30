"""
IntelliHedge — Streamlit Live Demo Dashboard
Authors: Krishiv Wahi, Kamya Aggarwal, Sarthak Shandiliya

Dark-themed UI showing:
  • Live headline stream with dedup indicators
  • Schmitt Trigger hysteresis chart (interactive H_k / L_k sliders)
  • Option hedge allocation curves across all 4 arms
  • P&L tail histograms
  • 4-Arm CVaR bar chart
  • Interactive sliders: H_k, L_k, transaction costs

Run with:
  streamlit run app.py
"""

import numpy as np
import streamlit as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from news_regime import PointInTimeNewsEngine, build_crisis_news_stream
from merton_env  import MertonJumpEnv
from deep_hedger import run_causal_ablation

SEED = 42


# -------------------------------------------------------------------------
# Streamlit page config
# -------------------------------------------------------------------------
st.set_page_config(
    page_title="IntelliHedge",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject minimal dark-mode CSS
st.markdown(
    """
    <style>
    .stApp { background-color: #0B0F19; color: #F1F5F9; }
    section[data-testid="stSidebar"] { background-color: #111827; }
    h1, h2, h3, h4 { color: #38BDF8; }
    .metric-label { color: #94A3B8 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


# -------------------------------------------------------------------------
# Sidebar — interactive controls
# -------------------------------------------------------------------------
with st.sidebar:
    st.title("⚙️ IntelliHedge Controls")
    st.markdown("---")

    h_thresh  = st.slider("H_k — DOMINANT entry threshold", 0.60, 0.95, 0.75, 0.01)
    l_thresh  = st.slider("L_k — FADING exit threshold",    0.35, 0.70, 0.55, 0.01)
    alpha_ema = st.slider("α  — EMA blend (recency centroid)", 0.10, 0.70, 0.35, 0.05)

    st.markdown("---")
    tc_stock = st.slider("Stock transaction cost (bps)", 1, 30, 10, 1) / 10_000
    tc_put   = st.slider("Put  transaction cost (bps)", 5, 100, 45, 5) / 10_000

    st.markdown("---")
    n_epochs = st.slider("Training epochs", 20, 100, 45, 5)
    run_btn  = st.button("🚀  Run / Refresh", use_container_width=True)

st.title("📡 IntelliHedge — News Narrative Intelligence for Deep Derivatives Hedging")
st.caption("Point-in-Time · Schmitt Trigger · 4-Arm Causal Ablation · Merton Jump-Diffusion")


# -------------------------------------------------------------------------
# Cached computation (re-runs on control change + button press)
# -------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def _compute(h_thresh, l_thresh, alpha_ema, tc_stock, tc_put, n_epochs, _trigger):
    # Engine 1
    engine      = PointInTimeNewsEngine(alpha_ema=alpha_ema, h_thresh=h_thresh, l_thresh=l_thresh)
    stream      = build_crisis_news_stream()
    regime_logs = []
    dedup_log   = []   # track which headlines were dropped

    for t, batch in enumerate(stream):
        # Show dedup behaviour in the headline panel
        seen_before_step = set(engine.seen_shingles)
        for source, text in batch:
            import re
            words    = re.findall(r"[a-z]+", text.lower())
            shingles = set(" ".join(words[i:i + 3]) for i in range(max(1, len(words) - 2)))
            is_dup   = any(
                len(shingles & past) / max(1, len(shingles | past)) >= 0.80
                for past in seen_before_step
            )
            dedup_log.append({"t": t, "source": source, "text": text, "dup": is_dup})
        res = engine.step(t, batch)
        regime_logs.append(res)

    Q_real = np.stack([r["Q_vec"] for r in regime_logs], axis=0)

    # Engine 2
    env         = MertonJumpEnv(n_paths=1000, n_steps=15, seed=SEED)
    S, iv, put_mkt = env.simulate()

    results = run_causal_ablation(
        S, iv, put_mkt, Q_real, epochs=n_epochs, lr=0.010
    )
    return regime_logs, dedup_log, Q_real, results


# Re-compute trigger: button or param change
_trigger = (run_btn,)   # hashable sentinel — changes on each button press

with st.spinner("Running IntelliHedge pipeline …"):
    regime_logs, dedup_log, Q_real, results = _compute(
        h_thresh, l_thresh, alpha_ema, tc_stock, tc_put, n_epochs, str(_trigger)
    )

arm_a = results["Arm A: Market-Only (Baseline)"]
arm_b = results["Arm B: News-Aware (IntelliHedge)"]
arm_c = results["Arm C: Shuffled-News (Placebo)"]
arm_d = results["Arm D: Latency-Stressed (1-step)"]


# -------------------------------------------------------------------------
# Row 1 — headline metrics
# -------------------------------------------------------------------------
c1, c2, c3, c4, c5 = st.columns(5)
reduction = (arm_a["cvar_99"] - arm_b["cvar_99"]) / (abs(arm_a["cvar_99"]) + 1e-8) * 100.0

c1.metric("Peak S_k(t)",    f"{max(r['S'] for r in regime_logs):.3f}")
c2.metric("Final State",    regime_logs[-1]["state"])
c3.metric("CVaR-99  Arm A", f"${arm_a['cvar_99']:.2f}")
c4.metric("CVaR-99  Arm B", f"${arm_b['cvar_99']:.2f}")
c5.metric("Tail-Risk Δ",    f"{reduction:+.1f}%", delta_color="inverse")


# -------------------------------------------------------------------------
# Row 2 — Headline stream  |  Schmitt Hysteresis
# -------------------------------------------------------------------------
col_left, col_right = st.columns([1, 2])

with col_left:
    st.subheader("📰 Live Headline Stream")
    for entry in dedup_log:
        badge = "🔴 DUP" if entry["dup"] else "🟢 NEW"
        st.markdown(
            f"**t={entry['t']}** `{entry['source']}` {badge}  \n"
            f"<small>{entry['text'][:90]}{'…' if len(entry['text'])>90 else ''}</small>",
            unsafe_allow_html=True,
        )

with col_right:
    st.subheader("⚡ Schmitt Trigger — Narrative Strength Trajectory")
    fig, ax = plt.subplots(figsize=(9, 3.8))
    fig.patch.set_facecolor("#111827"); ax.set_facecolor("#111827")

    steps     = np.arange(len(regime_logs))
    strengths = [r["S"] for r in regime_logs]

    ax.plot(steps, strengths, marker="o", color="#38BDF8", lw=2.4, label=r"$S_k(t)$")
    ax.axhline(h_thresh, color="#EF4444", ls="--", lw=1.5,
               label=f"$H_k={h_thresh:.2f}$ (enter DOMINANT)")
    ax.axhline(l_thresh, color="#F59E0B", ls=":",  lw=1.5,
               label=f"$L_k={l_thresh:.2f}$ (exit to FADING)")
    ax.fill_between(steps, strengths, h_thresh,
                    where=(np.array(strengths) >= h_thresh),
                    color="#EF4444", alpha=0.20)
    for r in regime_logs:
        if r["reignited"]:
            ax.axvline(r["t"], color="#A78BFA", ls="-.", lw=1.4, alpha=0.8)
            ax.text(r["t"] + 0.1, h_thresh + 0.02, "⚡", fontsize=10, color="#A78BFA")

    ax.set_xlabel("Time Step", color="#94A3B8"); ax.set_ylabel(r"$S_k(t)$", color="#94A3B8")
    ax.tick_params(colors="#94A3B8"); ax.set_ylim(0, 1.08)
    for sp in ax.spines.values(): sp.set_color("#334155")
    ax.legend(fontsize=8, facecolor="#1E293B", edgecolor="#334155", labelcolor="#F1F5F9")
    ax.grid(alpha=0.10)
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


# -------------------------------------------------------------------------
# Row 3 — Put Allocation  |  P&L Tail Histograms
# -------------------------------------------------------------------------
col3, col4 = st.columns(2)

with col3:
    st.subheader("🛡️ Dynamic Put Hedge Allocation — All 4 Arms")
    fig, ax = plt.subplots(figsize=(6, 3.8))
    fig.patch.set_facecolor("#111827"); ax.set_facecolor("#111827")

    ax.plot(steps, arm_b["put_trace"], marker="s", color="#10B981", lw=2.4, label="Arm B: News-Aware")
    ax.plot(steps, arm_a["put_trace"], marker="^", color="#94A3B8", ls="--", lw=2.0, label="Arm A: Market-Only")
    ax.plot(steps, arm_c["put_trace"], marker="x", color="#F43F5E", ls=":",  lw=1.8, label="Arm C: Shuffled")
    ax.plot(steps, arm_d["put_trace"], marker="d", color="#FB923C", ls="-.", lw=1.6, label="Arm D: Latency")

    ax.set_xlabel("Time Step", color="#94A3B8"); ax.set_ylabel("Mean Put Weight", color="#94A3B8")
    ax.tick_params(colors="#94A3B8")
    for sp in ax.spines.values(): sp.set_color("#334155")
    ax.legend(fontsize=8, facecolor="#1E293B", edgecolor="#334155", labelcolor="#F1F5F9")
    ax.grid(alpha=0.10)
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

with col4:
    st.subheader("📊 Terminal P&L Distribution — Left-Tail Truncation")
    fig, ax = plt.subplots(figsize=(6, 3.8))
    fig.patch.set_facecolor("#111827"); ax.set_facecolor("#111827")

    bins = np.linspace(-18, 6, 48)
    ax.hist(arm_a["pnl_dist"], bins=bins, alpha=0.50, color="#EF4444",
            label=f"Arm A  CVaR99={arm_a['cvar_99']:.2f}")
    ax.hist(arm_b["pnl_dist"], bins=bins, alpha=0.65, color="#10B981",
            label=f"Arm B  CVaR99={arm_b['cvar_99']:.2f}")
    ax.axvline(-arm_a["cvar_99"], color="#EF4444", ls="--", lw=2.0)
    ax.axvline(-arm_b["cvar_99"], color="#10B981", ls="-",  lw=2.0)

    ax.set_xlabel("Terminal Hedging P&L ($)", color="#94A3B8")
    ax.set_ylabel("Path Frequency", color="#94A3B8")
    ax.tick_params(colors="#94A3B8")
    for sp in ax.spines.values(): sp.set_color("#334155")
    ax.legend(fontsize=8, facecolor="#1E293B", edgecolor="#334155", labelcolor="#F1F5F9")
    ax.grid(alpha=0.10)
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


# -------------------------------------------------------------------------
# Row 4 — 4-Arm CVaR bar chart (full width)
# -------------------------------------------------------------------------
st.subheader("🎯 4-Arm Causal Ablation — 99% CVaR Tail Loss (lower = better)")
fig, ax = plt.subplots(figsize=(10, 3.5))
fig.patch.set_facecolor("#111827"); ax.set_facecolor("#111827")

labels     = ["Arm A\nMarket-Only", "Arm B\nNews-Aware", "Arm C\nShuffled", "Arm D\nLatency"]
cvar99s    = [arm_a["cvar_99"], arm_b["cvar_99"], arm_c["cvar_99"], arm_d["cvar_99"]]
bar_colors = ["#EF4444", "#10B981", "#F59E0B", "#FB923C"]
bars = ax.bar(labels, cvar99s, color=bar_colors, width=0.45)
for bar in bars:
    yv = bar.get_height()
    ax.text(bar.get_x() + bar.get_width() / 2.0, yv + 0.10,
            f"${yv:.2f}", ha="center", va="bottom", fontweight="bold",
            fontsize=10, color="#F1F5F9")

ax.set_ylabel("99% CVaR Loss ($)", color="#94A3B8")
ax.set_ylim(0, max(cvar99s) * 1.28)
ax.tick_params(colors="#94A3B8")
for sp in ax.spines.values(): sp.set_color("#334155")
ax.grid(axis="y", alpha=0.10)
st.pyplot(fig, use_container_width=True)
plt.close(fig)

st.markdown("---")
st.caption(
    "IntelliHedge Prototype · Krishiv Wahi, Kamya Aggarwal, Sarthak Shandiliya · "
    "Zero external API keys required · numpy · scipy · torch · matplotlib · streamlit"
)

