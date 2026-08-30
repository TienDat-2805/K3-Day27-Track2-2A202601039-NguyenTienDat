from __future__ import annotations

from typing import Any, Iterable

import numpy as np

from observability.anomaly import zscore_detector


def approximate_token_lengths(texts: Iterable[str]) -> list[int]:
    # Deliberately simple proxy; no tokenizer/model download needed.
    return [len(str(t).split()) for t in texts]


def detect_text_length_shift(
    current_texts: Iterable[str],
    baseline_batch_means: Iterable[float],
    *,
    threshold: float = 3.0,
) -> dict[str, Any]:
    lengths = approximate_token_lengths(current_texts)
    current_mean = float(np.mean(lengths)) if lengths else 0.0
    result = zscore_detector(current_mean, baseline_batch_means, threshold=threshold)
    result["metric"] = "mean_text_length"
    result["current_mean"] = current_mean
    return result


def detect_embedding_norm_shift(
    current_norms: Iterable[float], baseline_norms: Iterable[float]
) -> dict[str, Any]:
    current = np.asarray(list(current_norms), dtype=float)
    baseline = np.asarray(list(baseline_norms), dtype=float)
    if current.size == 0 or baseline.size < 3:
        return {"is_anomaly": False, "score": 0.0, "method": "robust_norm_shift", "reason": "insufficient_data"}
    if not np.isfinite(current).all() or not np.isfinite(baseline).all():
        return {"is_anomaly": True, "score": float("inf"), "method": "robust_norm_shift", "reason": "non_finite_embedding_norm"}
    center = float(np.median(baseline))
    mad = float(np.median(np.abs(baseline - center)))
    current_center = float(np.median(current))
    if mad == 0:
        score = float("inf") if current_center != center else 0.0
    else:
        score = 0.6745 * abs(current_center - center) / mad
    return {
        "is_anomaly": bool(score > 3.5),
        "score": float(score),
        "method": "robust_norm_shift",
        "reason": f"baseline_median={center:.4f}, current_median={current_center:.4f}, mad={mad:.4f}",
    }
