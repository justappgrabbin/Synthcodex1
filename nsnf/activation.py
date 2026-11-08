import numpy as np
from .schema import TIERS
from .components import MLP


def select(features, tier=1, candidates=None):
    if type(tier) is not int or tier not in TIERS:
        raise ValueError("tier must be 1..5")
    x = np.asarray(features, dtype=float)
    if x.shape != (8,) or not np.isfinite(x).all():
        raise ValueError("eight finite features required")
    candidates = list(range(320)) if candidates is None else candidates
    if len(set(candidates)) != len(candidates) or any(type(n) is not int or not 0 <= n < 320 for n in candidates):
        raise ValueError("candidate slot indices must be unique and in 0..319")
    # Explicit synthetic router; no Human Design interpretation is attached.
    scores = [(float(abs(x[(n // 64) % 8]) + abs(x[n % 8]) + (n % 64) / 6400), n) for n in candidates]
    scores.sort(key=lambda p: (-p[0], p[1]))
    budget = TIERS[tier]
    count = min(budget.max_components, budget.max_macs // (MLP.macs * budget.rounds), len(scores))
    return [{"index": n, "component_id": f"d{n // 64}:g{n % 64}", "score": score,
             "reason": "synthetic feature salience under explicit compute budget",
             "router_version": "synthetic-salience-v1"} for score, n in scores[:count]]
