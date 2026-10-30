"""
IntelliHedge — Engine 2 (Policy): Semi-Recurrent Deep Hedging Policy + 4-Arm Causal Ablation
Authors: Krishiv Wahi, Kamya Aggarwal, Sarthak Shandiliya

Policy maps:
  M_t = [S_t/S0, tau, iv_t, prev_stock_delta, prev_put_weight, Q_t^news (4-dim)]
  → a_t = [delta_stock ∈ [0,1],  weight_put ∈ [0,1.25]]

Training objective (coherent tail-risk):
  L(theta) = 0.25 * E[L_T] + 0.75 * CVaR_0.95(L_T) + 0.10 * E[TC]

4-Arm Causal Ablation:
  Arm A — Market-Only Baseline      (Q_t^news = 0)
  Arm B — News-Aware Treatment      (real point-in-time Q_t^news)
  Arm C — Shuffled-News Placebo     (temporally permuted Q_t^news)
  Arm D — Latency-Stressed          (1-step delayed Q_t^news)
"""

import math
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from merton_env import bs_put_price_and_delta

SEED = 42

# Optimize CPU parallelism: avoid thread barrier synchronization overhead on small matrix rollouts
if torch.get_num_threads() > 2:
    torch.set_num_threads(2)


# -------------------------------------------------------------------------
# Policy Network
# -------------------------------------------------------------------------
class DeepHedgingPolicy(nn.Module):
    """
    Semi-recurrent policy network.

    Input  : M_t ∈ R^9  = [S_t/S0, tau, iv_t, prev_delta, prev_put, Q_t^news(4)]
    Output : a_t ∈ R^2  = [delta_stock, weight_put]
    """

    def __init__(self, in_dim: int = 9, hidden_dim: int = 48):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.SiLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.SiLU(),
            nn.Linear(hidden_dim, 2),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        raw         = self.net(x)
        delta_stock = torch.sigmoid(raw[:, 0:1])           # ∈ [0, 1]
        weight_put  = torch.sigmoid(raw[:, 1:2]) * 1.25    # ∈ [0, 1.25]
        return torch.cat([delta_stock, weight_put], dim=1)


# -------------------------------------------------------------------------
# CVaR loss (coherent, tail-sensitive)
# -------------------------------------------------------------------------
def cvar_loss(losses: torch.Tensor, alpha: float = 0.95) -> torch.Tensor:
    """
    Conditional Value-at-Risk at level alpha on a batch of scalar losses.
    Targets the average of the worst (1-alpha) fraction of outcomes.
    """
    k       = max(1, int(math.ceil((1.0 - alpha) * losses.shape[0])))
    top_k, _ = torch.topk(losses, k=k)
    return torch.mean(top_k)


# -------------------------------------------------------------------------
# Single-arm train + evaluate
# -------------------------------------------------------------------------
def train_and_evaluate_arm(
    arm_name:  str,
    S:         np.ndarray,
    iv:        np.ndarray,
    put_mkt:   np.ndarray,
    Q_matrix:  np.ndarray,
    epochs:    int   = 45,
    lr:        float = 0.010,
    K_liability: float = 100.0,   # desk is short an ATM Put (K=100)
    tc_stock:  float = 0.0010,
    tc_put:    float = 0.0045,
) -> dict:
    """
    Train a DeepHedgingPolicy for one ablation arm and return out-of-sample metrics.

    Parameters
    ----------
    arm_name  : human-readable label
    S, iv, put_mkt : market paths from MertonJumpEnv.simulate()
    Q_matrix  : (n_steps, 4) point-in-time regime vectors (pre-processed per arm)
    epochs    : SGD epochs
    lr        : Adam learning rate
    """
    torch.manual_seed(SEED)
    device = torch.device("cpu")

    S_t = torch.tensor(S,       dtype=torch.float32, device=device)
    iv_t = torch.tensor(iv,     dtype=torch.float32, device=device)
    P_t  = torch.tensor(put_mkt,dtype=torch.float32, device=device)
    Q_t  = torch.tensor(Q_matrix, dtype=torch.float32, device=device)

    n_total, n_steps_plus = S.shape
    n_steps  = n_steps_plus - 1
    n_train  = int(0.7 * n_total)

    model     = DeepHedgingPolicy(in_dim=9, hidden_dim=48).to(device)
    optimizer = optim.Adam(model.parameters(), lr=lr)

    # Initial premium collected for the short ATM put
    S0_scalar       = float(S[:, 0].mean())
    initial_premium = float(
        bs_put_price_and_delta(S0_scalar, K_liability, 30.0 / 365.0, 0.02, 0.22)[0]
    )

    # ------------------------------------------------------------------
    def rollout(idx_slice: torch.Tensor):
        batch_size = idx_slice.shape[0]
        prev_action  = torch.zeros((batch_size, 2), dtype=torch.float32, device=device)
        pnl          = torch.full((batch_size,), initial_premium, dtype=torch.float32, device=device)
        total_tc     = torch.zeros((batch_size,), dtype=torch.float32, device=device)
        total_turnover = torch.zeros((batch_size,), dtype=torch.float32, device=device)
        put_holdings_trace = []

        for t in range(n_steps):
            tau     = torch.full((batch_size, 1), (n_steps - t) / n_steps, device=device)
            s_norm  = (S_t[idx_slice, t] / S0_scalar).unsqueeze(1)
            iv_curr = iv_t[idx_slice, t].unsqueeze(1)
            q_curr  = Q_t[t].unsqueeze(0).expand(batch_size, -1)

            state_vec = torch.cat([s_norm, tau, iv_curr, prev_action, q_curr], dim=1)
            action    = model(state_vec)   # [delta_stock, weight_put]
            put_holdings_trace.append(action[:, 1].detach().cpu().numpy().mean())

            # Transaction costs from rebalancing
            d_action  = torch.abs(action - prev_action)
            step_tc   = (
                d_action[:, 0] * S_t[idx_slice, t] * tc_stock
                + d_action[:, 1] * P_t[idx_slice, t] * tc_put
            )
            total_tc      = total_tc + step_tc
            total_turnover = total_turnover + d_action.sum(dim=1)

            # Portfolio P&L: short stock delta hedge + long protective put
            dS       = S_t[idx_slice, t + 1] - S_t[idx_slice, t]
            dP       = P_t[idx_slice, t + 1] - P_t[idx_slice, t]
            step_gain = -action[:, 0] * dS + action[:, 1] * dP - step_tc
            pnl       = pnl + step_gain
            prev_action = action

        # Terminal liability: short ATM put payoff
        liability   = torch.clamp(K_liability - S_t[idx_slice, n_steps], min=0.0)
        terminal_pnl  = pnl - liability
        terminal_loss = -terminal_pnl
        return terminal_pnl, terminal_loss, total_tc, total_turnover, np.array(put_holdings_trace)
    # ------------------------------------------------------------------

    train_idx = torch.arange(0, n_train, device=device)
    test_idx  = torch.arange(n_train, n_total, device=device)

    # Training loop — coherent tail-risk objective
    for _ in range(epochs):
        optimizer.zero_grad()
        _, loss_vec, tc_vec, _, _ = rollout(train_idx)
        objective = (
            0.25 * loss_vec.mean()
            + 0.75 * cvar_loss(loss_vec, alpha=0.95)
            + 0.10 * tc_vec.mean()
        )
        objective.backward()
        optimizer.step()

    # Out-of-sample evaluation
    with torch.no_grad():
        test_pnl, test_loss, test_tc, test_turn, put_trace = rollout(test_idx)
        pnl_np   = test_pnl.cpu().numpy()
        loss_np  = test_loss.cpu().numpy()
        cvar_95  = float(np.mean(np.sort(loss_np)[int(0.95 * len(loss_np)):]))
        cvar_99  = float(np.mean(np.sort(loss_np)[int(0.99 * len(loss_np)):]))
        max_dd   = float(np.max(loss_np))

    return {
        "arm":       arm_name,
        "mean_pnl":  float(np.mean(pnl_np)),
        "std_pnl":   float(np.std(pnl_np)),
        "cvar_95":   cvar_95,
        "cvar_99":   cvar_99,
        "max_loss":  max_dd,
        "turnover":  float(test_turn.mean().item()),
        "pnl_dist":  pnl_np,
        "put_trace": put_trace,
    }


# -------------------------------------------------------------------------
# 4-Arm Causal Ablation Runner
# -------------------------------------------------------------------------
def run_causal_ablation(
    S:        np.ndarray,
    iv:       np.ndarray,
    put_mkt:  np.ndarray,
    Q_real:   np.ndarray,
    epochs:   int = 45,
    lr:       float = 0.010,
) -> dict:
    """
    Run all four ablation arms and return a results dict.

    Arms
    ----
    A  Market-Only Baseline   : Q = 0
    B  News-Aware Treatment   : Q = real point-in-time
    C  Shuffled-News Placebo  : Q = temporally permuted (breaks causal ordering)
    D  Latency-Stressed       : Q = 1-step delayed (Arm D per roadmap)
    """
    rng = np.random.default_rng(SEED)

    n_steps = S.shape[1] - 1

    # Arm A: zero-out the news vector entirely
    Q_zero = np.zeros_like(Q_real)

    # Arm C: temporal permutation of rows (destroys causal ordering)
    perm       = rng.permutation(n_steps)
    Q_shuffled = Q_real[perm]

    # Arm D: 1-step latency — row t of the policy sees Q from t-1
    Q_delayed = np.zeros_like(Q_real)
    Q_delayed[1:] = Q_real[:-1]   # shift down by 1; step 0 gets zeros (no prior info)

    print("\n[ENGINE 2] Training DeepHedgingPolicy — 4-Arm Causal Ablation...")

    results = {}
    for arm_name, Q_mat in [
        ("Arm A: Market-Only (Baseline)",     Q_zero),
        ("Arm B: News-Aware (IntelliHedge)",  Q_real),
        ("Arm C: Shuffled-News (Placebo)",    Q_shuffled),
        ("Arm D: Latency-Stressed (1-step)",  Q_delayed),
    ]:
        print(f"  Training {arm_name} ...", end="", flush=True)
        res = train_and_evaluate_arm(arm_name, S, iv, put_mkt, Q_mat, epochs=epochs, lr=lr)
        results[arm_name] = res
        print(f"  CVaR-99 = {res['cvar_99']:.3f}")

    return results

