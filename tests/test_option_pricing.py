
import numpy as np
from scipy.stats import norm

from merton_env import bs_put_price_and_delta


def test_put_call_parity():
    S = np.array([90.0, 100.0, 110.0])
    K = 100.0
    T = 1.0
    r = 0.05
    sigma = 0.2

    put_price, _ = bs_put_price_and_delta(S, K, T, r, sigma)

    d1 = (
        np.log(S / K) + (r + 0.5 * sigma**2) * T
    ) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    call_price = (
        S * norm.cdf(d1)
        - K * np.exp(-r * T) * norm.cdf(d2)
    )

    # Put-call parity: C - P = S - K * exp(-rT)
    assert np.allclose(
        call_price - put_price,
        S - K * np.exp(-r * T),
        atol=1e-8
    )


def test_put_price_limiting_cases():
    S = np.array([1.0, 500.0])
    K = 100.0
    T = 1.0
    r = 0.05
    sigma = 0.2

    put_price, _ = bs_put_price_and_delta(S, K, T, r, sigma)

    # Deep in-the-money put should have a high value.
    assert put_price[0] > 90.0

    # Deep out-of-the-money put should be close to zero.
    assert put_price[1] < 1e-6


def test_put_price_at_expiry():
    S = np.array([80.0, 100.0, 120.0])
    K = 100.0
    T = 0.0
    r = 0.05
    sigma = 0.2

    put_price, _ = bs_put_price_and_delta(S, K, T, r, sigma)

    expected_price = np.array([20.0, 0.0, 0.0])

    assert np.allclose(put_price, expected_price)
