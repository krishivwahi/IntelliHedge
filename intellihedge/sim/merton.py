"""
IntelliHedge — Engine 2: Merton Jump-Diffusion Market Simulator
Authors: Krishiv Wahi, Kamya Aggarwal, Sarthak Shandiliya

Implements:
  dS_t / S_{t-} = (mu - lambda*kappa)*dt + sigma*dW_t + (J-1)*dN_t
  with vectorised Black-Scholes pricing for a liquid near-the-money Put
  and proportional transaction costs.

Dynamics Separation (non-negotiable):
  Jump clusters are driven by exogenous crisis windows (shock_steps dict),
  NEVER by the news-regime signal Q_t^news.  The simulator is calibrated
  from historical volatility, not from the live news feature.

Configurable execution-latency delay:
  tau_delay_steps = 0  →  real-time news (Arm B)
  tau_delay_steps = 1  →  1-step lagged news (Arm D)
"""

import math
import numpy as np
from scipy.stats import norm


# -------------------------------------------------------------------------
# Vectorised Black-Scholes Put pricing & delta
# -------------------------------------------------------------------------
def bs_put_price_and_delta(
    S:     np.ndarray,
    K:     float,
    T_rem: np.ndarray | float,
    r:     float,
    sigma: np.ndarray | float,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Vectorised Black-Scholes Put price and delta.

    Parameters
    ----------
    S     : underlying price(s)
    K     : strike
    T_rem : time-to-expiry in years
    r     : risk-free rate
    sigma : implied volatility

    Returns
    -------
    (put_price, put_delta)  — arrays matching the shape of S
    """
    T_safe  = np.maximum(T_rem, 1e-5)
    d1      = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T_safe) / (sigma * np.sqrt(T_safe))
    d2      = d1 - sigma * np.sqrt(T_safe)
    put_p   = K * np.exp(-r * T_safe) * norm.cdf(-d2) - S * norm.cdf(-d1)
    put_d   = norm.cdf(d1) - 1.0
    intrinsic = np.maximum(K - S, 0.0)
    return np.where(T_rem <= 1e-5, intrinsic, put_p), put_d


# -------------------------------------------------------------------------
# Merton Jump-Diffusion Simulator
# -------------------------------------------------------------------------
class MertonJumpEnv:
    """
    Discrete-time Merton Jump-Diffusion market with option pricing.

    Parameters
    ----------
    n_paths        : number of Monte-Carlo paths
    n_steps        : number of discrete time steps
    S0             : initial stock price
    mu             : real-world drift
    sigma          : diffusion volatility
    lambda_jump    : Poisson jump arrival rate (annualised)
    mu_jump        : mean log-jump size
    sigma_jump     : std of log-jump size
    r              : risk-free rate
    K_hedge        : strike of the liquid hedging Put (near-the-money)
    tau_delay_steps: execution latency (0 = real-time, 1 = 1-step delay)
    seed           : random seed for reproducibility
    """

    def __init__(
        self,
        n_paths:         int   = 2000,
        n_steps:         int   = 15,
        S0:              float = 100.0,
        mu:              float = 0.05,
        sigma:           float = 0.20,
        lambda_jump:     float = 1.5,     # ~1.5 jumps/year on average
        mu_jump:         float = -0.065,  # mean log-jump (negative = downside)
        sigma_jump:      float = 0.035,
        r:               float = 0.02,
        K_hedge:         float = 98.0,    # liquid near-the-money Put
        tau_delay_steps: int   = 0,
        seed:            int   = 42,
    ):
        self.n_paths         = n_paths
        self.n_steps         = n_steps
        self.S0              = S0
        self.mu              = mu
        self.sigma           = sigma
        self.lambda_jump     = lambda_jump
        self.mu_jump         = mu_jump
        self.sigma_jump      = sigma_jump
        self.r               = r
        self.K_hedge         = K_hedge
        self.tau_delay_steps = tau_delay_steps
        self.seed            = seed

        # kappa = E[J-1] where J = exp(N(mu_j, sigma_j^2))
        # mean compensator so drift stays at mu under the real-world measure
        self.kappa = math.exp(mu_jump + 0.5 * sigma_jump ** 2) - 1.0

        # Horizon: 30-day rolling window expressed in years
        self.T_horizon = 30.0 / 365.0
        self.dt        = self.T_horizon / n_steps

        # Exogenous crisis schedule — calibrated from historical vol, NOT from news.
        # This is what enforces the Dynamics Separation principle.
        self._shock_steps = {2: 0.35, 3: 0.45, 4: 0.20, 10: 0.50, 11: 0.40}

    # ------------------------------------------------------------------
    def simulate(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Simulate market paths.

        Returns
        -------
        S       : (n_paths, n_steps+1)  stock price paths
        iv      : (n_paths, n_steps+1)  implied-vol paths (rearview expansion)
        put_mkt : (n_paths, n_steps+1)  BS Put prices along each path
        """
        rng = np.random.default_rng(self.seed)

        S       = np.zeros((self.n_paths, self.n_steps + 1), dtype=np.float32)
        iv      = np.zeros((self.n_paths, self.n_steps + 1), dtype=np.float32)
        put_mkt = np.zeros((self.n_paths, self.n_steps + 1), dtype=np.float32)

        S[:, 0]  = self.S0
        iv[:, 0] = self.sigma
        compensated_drift = self.mu - self.lambda_jump * self.kappa

        for t in range(self.n_steps):
            T_rem    = (self.n_steps - t) * self.dt
            put_p, _ = bs_put_price_and_delta(S[:, t], self.K_hedge, T_rem, self.r, iv[:, t])
            put_mkt[:, t] = put_p

            # Exogenous jump probability for this step
            jump_prob = self._shock_steps.get(t, self.lambda_jump * self.dt)
            sigma_t   = self.sigma + (0.28 if jump_prob > 0.1 else 0.0)

            Z           = rng.standard_normal(self.n_paths).astype(np.float32)
            jump_occurs = (rng.uniform(0.0, 1.0, self.n_paths) < jump_prob).astype(np.float32)
            jump_size   = rng.normal(self.mu_jump, self.sigma_jump, self.n_paths).astype(np.float32) * jump_occurs

            # dS/S = (mu - lambda*kappa)*dt + sigma*dW + (J-1)*dN
            S[:, t + 1] = S[:, t] * np.exp(
                (compensated_drift - 0.5 * sigma_t ** 2) * self.dt
                + sigma_t * math.sqrt(self.dt) * Z
                + jump_size
            )
            # IV expands *after* the jump (rearview-mirror effect)
            iv[:, t + 1] = np.clip(
                self.sigma + 0.35 * jump_occurs + 0.5 * (iv[:, t] - self.sigma),
                self.sigma * 0.9,
                0.75,
            )

        # Terminal intrinsic value at expiry
        put_mkt[:, self.n_steps] = np.maximum(self.K_hedge - S[:, self.n_steps], 0.0)
        return S, iv, put_mkt

    # ------------------------------------------------------------------
    def apply_latency(self, Q_matrix: np.ndarray) -> np.ndarray:
        """
        Apply tau_delay_steps to a regime-vector matrix.

        Parameters
        ----------
        Q_matrix : (n_steps, q_dim) point-in-time regime vectors

        Returns
        -------
        Q_delayed : same shape; first tau rows are zeroed (no future info)
        """
        if self.tau_delay_steps == 0:
            return Q_matrix
        Q_delayed = np.zeros_like(Q_matrix)
        Q_delayed[self.tau_delay_steps:] = Q_matrix[: self.n_steps - self.tau_delay_steps + 1]
        return Q_delayed

