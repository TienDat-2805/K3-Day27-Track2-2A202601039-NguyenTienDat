"""Simple Z-score plus robust context-aware anomaly detection."""
from __future__ import annotations

from typing import Any, Iterable

import numpy as np


def zscore_detector(current: float, history: Iterable[float], threshold: float = 3.0) -> dict[str, Any]:
    values = np.asarray(list(history), dtype=float)
    if values.size < 3:
        return {"is_anomaly": False, "score": 0.0, "method": "zscore", "reason": "insufficient_history"}
    mean = float(np.mean(values))
    std = float(np.std(values))
    if std == 0:
        score = float("inf") if float(current) != mean else 0.0
    else:
        score = abs(float(current) - mean) / std
    return {
        "is_anomaly": bool(score > threshold),
        "score": float(score),
        "method": "zscore",
        "reason": f"mean={mean:.3f}, std={std:.3f}, threshold={threshold}",
    }


def mad_detector(current: float, history: Iterable[float], threshold: float = 3.5) -> dict[str, Any]:
    """Outlier-resistant detector with explicit zero-MAD behavior."""
    values = np.asarray(list(history), dtype=float)
    if values.size < 5:
        return {"is_anomaly": False, "score": 0.0, "method": "mad", "reason": "insufficient_history"}
    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median)))
    if mad == 0:
        score = float("inf") if float(current) != median else 0.0
        return {
            "is_anomaly": bool(score > threshold),
            "score": score,
            "method": "mad",
            "reason": f"median={median:.3f}, mad=0; exact_baseline=true",
        }
    modified_z = 0.6745 * abs(float(current) - median) / mad
    return {
        "is_anomaly": bool(modified_z > threshold),
        "score": float(modified_z),
        "method": "mad",
        "reason": f"median={median:.3f}, mad={mad:.3f}, threshold={threshold}",
    }


def detect_anomaly(
    current: float,
    history: Iterable[float],
    *,
    method: str = "auto",
    threshold: float = 3.0,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Stable lab API.

    Supported behavior:
    - `zscore`: basic z-score.
    - `mad`: outlier-resistant median/MAD detector.
    - `auto`: prefers caller-provided same-segment history, uses MAD with a
      z-score fallback for short history, and suppresses declared known events.
    """
    if method == "mad":
        return mad_detector(current, history, threshold=max(3.5, threshold))
    if method == "zscore":
        result = zscore_detector(current, history, threshold=threshold)
        return result
    if method == "auto":
        context = context or {}
        if context.get("known_event"):
            return {
                "is_anomaly": False,
                "score": 0.0,
                "method": "auto:known_event",
                "reason": f"suppressed_known_event={context['known_event']}",
            }
        segmented = context.get("same_segment_history")
        values = list(segmented) if segmented is not None else list(history)
        result = mad_detector(current, values, threshold=max(3.5, threshold))
        if result["reason"] == "insufficient_history":
            result = zscore_detector(current, values, threshold=threshold)
        result["method"] = "auto:same-segment-mad" if segmented is not None else f"auto:{result['method']}"
        metric = context.get("metric_name")
        if metric:
            result["reason"] += f"; metric={metric}"
        return result
    raise ValueError(f"Unsupported method: {method}")
