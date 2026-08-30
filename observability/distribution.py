from __future__ import annotations

from typing import Any, Iterable

import numpy as np


def detect_distribution_shift(
    current_values: Iterable[float],
    baseline_values: Iterable[float],
    *,
    ratio_threshold: float = 3.0,
) -> dict[str, Any]:
    """Detect location and shape drift using empirical KS plus mean ratio."""
    cur = np.asarray(list(current_values), dtype=float)
    base = np.asarray(list(baseline_values), dtype=float)
    if cur.size == 0 or base.size == 0:
        return {"is_anomaly": False, "score": 0.0, "method": "mean_ratio", "reason": "empty_input"}
    if not np.isfinite(cur).all() or not np.isfinite(base).all():
        return {"is_anomaly": True, "score": float("inf"), "method": "empirical_ks", "reason": "non_finite_values"}

    # Two-sample Kolmogorov-Smirnov statistic, implemented locally to keep the
    # lab dependency-free. It catches shape drift even when both means match.
    points = np.sort(np.unique(np.concatenate([cur, base])))
    cur_sorted = np.sort(cur)
    base_sorted = np.sort(base)
    cur_cdf = np.searchsorted(cur_sorted, points, side="right") / cur.size
    base_cdf = np.searchsorted(base_sorted, points, side="right") / base.size
    statistic = float(np.max(np.abs(cur_cdf - base_cdf)))
    critical = float(1.36 * np.sqrt((cur.size + base.size) / (cur.size * base.size)))
    # The old mean-ratio signal remains useful for very small samples where a
    # distribution test has low power.
    cur_mean = float(np.mean(cur))
    base_mean = float(np.mean(base))
    if cur_mean == 0 or base_mean == 0:
        mean_ratio = float("inf") if cur_mean != base_mean else 1.0
    else:
        mean_ratio = max(abs(cur_mean / base_mean), abs(base_mean / cur_mean))
    anomaly = statistic > critical or mean_ratio >= ratio_threshold
    return {
        "is_anomaly": bool(anomaly),
        "score": statistic,
        "method": "empirical_ks+mean_ratio",
        "reason": (
            f"ks={statistic:.4f}, critical={critical:.4f}; "
            f"mean_ratio={mean_ratio:.4f}"
        ),
    }
