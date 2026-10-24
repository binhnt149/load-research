"""Shape-only segmentation, deterministic labels and retained noise."""

import os
from dataclasses import dataclass
from math import ceil

import numpy as np
from sklearn.cluster import DBSCAN, KMeans
from sklearn.metrics import silhouette_score
from threadpoolctl import threadpool_limits

from load_research.domain.config import RunConfig
from load_research.domain.energy import normalize
from load_research.profiles import CustomerProfile


@dataclass
class ClusterResult:
    assignments: dict[str, str]
    centroids: dict[str, list[float]]
    diagnostics: dict


def _score_indices(
    candidates: list[np.ndarray], n: int, config: RunConfig
) -> np.ndarray:
    size = min(n, config.silhouette_sample)
    anchors = {
        int(np.flatnonzero(labels == label)[0])
        for labels in candidates
        for label in np.unique(labels)
        if label >= 0
    }
    if len(anchors) > size:
        raise ValueError("silhouette sample budget cannot represent candidate clusters")
    remaining = np.asarray(sorted(set(range(n)) - anchors))
    chosen = np.random.default_rng(config.seed).choice(
        remaining, size - len(anchors), replace=False
    )
    return np.asarray(sorted(anchors | set(chosen.tolist())), dtype=int)


def _silhouette(
    matrix: np.ndarray, labels: np.ndarray, indices: np.ndarray
) -> float | None:
    selected = labels[indices]
    if 2 <= len(np.unique(selected)) < len(selected):
        return float(silhouette_score(matrix[indices], selected))
    return None


def cluster_profiles(
    profiles: list[CustomerProfile], config: RunConfig
) -> ClusterResult:
    os.environ.setdefault("LOKY_MAX_CPU_COUNT", str(config.worker_threads))
    ordered = sorted(profiles, key=lambda profile: profile.customer.customer_id)
    keys = {
        (profile.customer.industry_code, profile.period, profile.day_type)
        for profile in ordered
    }
    identifiers = [profile.customer.customer_id for profile in ordered]
    if len(keys) > 1 or len(set(identifiers)) != len(identifiers):
        raise ValueError("clustering requires one cell with unique customers")
    assignments, positive, shapes = {}, [], []
    for profile in ordered:
        shape = normalize(profile.values)
        if shape is None:
            assignments[profile.customer.customer_id] = "inactive"
        else:
            positive.append(profile)
            shapes.append(shape)
    diagnostics: dict = {
        "algorithm": config.algorithm,
        "silhouette": None,
        "noise_count": 0,
        "positive_vectors": len(positive),
        "manual": config.manual_k is not None,
        "warnings": [],
        "reason": None,
    }
    if not positive:
        diagnostics["reason"] = "no_positive_shapes"
        return ClusterResult(assignments, {}, diagnostics)
    matrix = np.stack(shapes)
    n = len(matrix)
    if n < config.min_cluster_customers and config.manual_k is None:
        diagnostics["reason"] = "insufficient_vectors"
        assignments.update(
            {profile.customer.customer_id: "not_segmented" for profile in positive}
        )
        return ClusterResult(
            assignments, {"not_segmented": matrix.mean(axis=0).tolist()}, diagnostics
        )
    # Count numerical equivalence without rounding the fit or physical totals.
    unique = len(np.unique(matrix.round(12), axis=0))
    diagnostics["shape_equality_decimals"] = 12
    minimum = max(config.min_cluster_size, ceil(config.min_cluster_fraction * n))
    labels = np.zeros(n, dtype=int)
    with threadpool_limits(limits=config.worker_threads):
        if config.algorithm == "dbscan":
            if n > config.max_dbscan_vectors:
                raise ValueError("DBSCAN exceeds configured resource vector limit")
            labels = DBSCAN(
                eps=config.eps,
                min_samples=config.min_samples,
                metric="euclidean",
                n_jobs=1,
            ).fit_predict(matrix)
            clustered = np.flatnonzero(labels >= 0)
            if len(clustered):
                subset = _score_indices([labels[clustered]], len(clustered), config)
                diagnostics["silhouette"] = _silhouette(
                    matrix[clustered], labels[clustered], subset
                )
        elif config.manual_k is not None:
            if config.manual_k > min(unique, n):
                raise ValueError(
                    "manual cluster count exceeds distinct available shapes"
                )
            labels = KMeans(
                n_clusters=config.manual_k,
                random_state=config.seed,
                n_init=config.n_init,
                max_iter=config.max_iter,
            ).fit_predict(matrix)
            diagnostics["silhouette"] = _silhouette(
                matrix, labels, _score_indices([labels], n, config)
            )
        else:
            candidates = []
            for k in range(config.k_min, min(config.k_max, n - 1, unique) + 1):
                candidate = KMeans(
                    n_clusters=k,
                    random_state=config.seed,
                    n_init=config.n_init,
                    max_iter=config.max_iter,
                ).fit_predict(matrix)
                if min(np.bincount(candidate)) >= minimum:
                    candidates.append(candidate)
            if candidates:
                indices = _score_indices(candidates, n, config)
                scored = []
                for candidate in candidates:
                    score = _silhouette(matrix, candidate, indices)
                    if score is not None and score >= config.silhouette_min:
                        scored.append((score, candidate))
                if scored:
                    maximum = max(score for score, _candidate in scored)
                    score, labels = next(
                        (score, candidate)
                        for score, candidate in scored
                        if score >= maximum - config.silhouette_tie
                    )
                    diagnostics["silhouette"] = score
                    diagnostics["silhouette_maximum"] = maximum
            if diagnostics["silhouette"] is None:
                diagnostics["reason"] = "no_supported_segmentation"
    actual = sorted(set(labels.tolist()) - {-1})
    centers = {label: matrix[labels == label].mean(axis=0) for label in actual}
    rank = sorted(
        actual,
        key=lambda label: (
            int(centers[label].argmax()),
            tuple(centers[label].round(12)),
        ),
    )
    names = {label: f"group_{index + 1}" for index, label in enumerate(rank)}
    if (
        config.algorithm == "kmeans"
        and config.manual_k is None
        and diagnostics["silhouette"] is None
    ):
        names = {0: "not_segmented"}
    for label in actual:
        if int((labels == label).sum()) < minimum:
            diagnostics["warnings"].append("small_clusters")
            break
    for profile, label in zip(positive, labels, strict=True):
        assignments[profile.customer.customer_id] = (
            "unclassified" if label == -1 else names[int(label)]
        )
    diagnostics["noise_count"] = int((labels == -1).sum())
    return ClusterResult(
        assignments,
        {names[label]: centers[label].tolist() for label in actual},
        diagnostics,
    )
