
import torch
import numpy as np
from scipy.stats import norm

from deep_hedger import cvar_loss


def test_cvar_simple_example():
    losses = torch.tensor([2.0, 5.0, 8.0, 10.0])

    result = cvar_loss(losses, alpha=0.5)

    # Worst 50% losses are 8 and 10.
    expected = torch.tensor(9.0)

    assert torch.isclose(result, expected)


def test_cvar_against_normal_distribution():
    mu = 5.0
    sigma = 2.0
    alpha = 0.95

    # Generate a deterministic sample from a normal distribution.
    probabilities = np.linspace(0.0001, 0.9999, 100000)
    losses = mu + sigma * norm.ppf(probabilities)

    losses_tensor = torch.tensor(losses, dtype=torch.float32)

    result = cvar_loss(losses_tensor, alpha=alpha)

    # Theoretical upper-tail CVaR for a normal distribution.
    z = norm.ppf(alpha)
    expected = mu + sigma * norm.pdf(z) / (1 - alpha)

    assert abs(result.item() - expected) < 0.15
