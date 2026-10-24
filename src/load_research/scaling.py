"""Energy-conserving industry expansion using a common calendar-weighted base."""

import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field

import numpy as np

from load_research.calendar import DayType
from load_research.clustering import ClusterResult
from load_research.profiles import CustomerProfile


@dataclass
class ScaleResult:
    status: str
    sample: dict[DayType, np.ndarray]
    energy: dict[DayType, np.ndarray]
    contributions: dict[DayType, dict[str, np.ndarray]]
    sample_contributions: dict[DayType, dict[str, np.ndarray]]
    alpha: float | None
    background_kwh: float
    billing_kwh: float | None
    diagnostics: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "alpha": self.alpha,
            "background_kwh": self.background_kwh,
            "billing_kwh": self.billing_kwh,
            "diagnostics": self.diagnostics,
            "sample": {
                kind.value: value.tolist() for kind, value in self.sample.items()
            },
            "energy": {
                kind.value: value.tolist() for kind, value in self.energy.items()
            },
            "contributions": {
                kind.value: {label: vector.tolist() for label, vector in groups.items()}
                for kind, groups in self.contributions.items()
            },
            "sample_contributions": {
                kind.value: {label: vector.tolist() for label, vector in groups.items()}
                for kind, groups in self.sample_contributions.items()
            },
        }


def scale_industry(
    profiles: list[CustomerProfile],
    clusters: dict[DayType, ClusterResult],
    day_counts: dict[DayType, int],
    billing_kwh: float | None,
    *,
    min_customers: int = 10,
) -> ScaleResult:
    if billing_kwh is not None and (not math.isfinite(billing_kwh) or billing_kwh < 0):
        raise ValueError("industry billing must be finite and non-negative")
    if any(type(count) is not int or count < 0 for count in day_counts.values()):
        raise ValueError("invalid calendar counts")
    present = {DayType(kind) for kind, count in day_counts.items() if count > 0}
    if not present:
        raise ValueError("calendar has no days")
    if not profiles:
        return ScaleResult("no_eligible_samples", {}, {}, {}, {}, None, 0, billing_kwh)
    if (
        len({(profile.customer.industry_code, profile.period) for profile in profiles})
        != 1
    ):
        raise ValueError("scaling requires a single industry-month")
    grouped: dict[DayType, list[CustomerProfile]] = defaultdict(list)
    for profile in profiles:
        grouped[profile.day_type].append(profile)
    if set(grouped) != present:
        raise ValueError("cohort does not cover every present day type")
    reference = None
    samples, components = {}, {}
    for kind in sorted(present):
        group = grouped[kind]
        cohort = {
            profile.customer.customer_id: profile.customer.weight for profile in group
        }
        if len(cohort) != len(group) or (reference is not None and cohort != reference):
            raise ValueError("cohort or weights differ between day types")
        reference = cohort
        labels = clusters[kind].assignments
        if set(labels) != set(cohort):
            raise ValueError("cluster assignments do not cover cohort exactly")
        cluster_vectors: dict[str, np.ndarray] = {}
        for profile in group:
            vector = np.asarray(profile.values, float)
            if (
                len(vector) not in (24, 48)
                or not np.isfinite(vector).all()
                or (vector < 0).any()
            ):
                raise ValueError("invalid physical profile")
            if (
                not math.isfinite(profile.customer.weight)
                or profile.customer.weight <= 0
            ):
                raise ValueError("invalid sampling weight")
            label = labels[profile.customer.customer_id]
            if label not in cluster_vectors:
                cluster_vectors[label] = np.zeros_like(vector)
            cluster_vectors[label] += profile.customer.weight * vector
        components[kind] = cluster_vectors
        samples[kind] = np.stack(list(cluster_vectors.values())).sum(axis=0)
    background = math.fsum(
        day_counts[kind] * float(vector.sum()) for kind, vector in samples.items()
    )
    if not math.isfinite(background):
        raise ValueError("sample energy overflow")
    n = len(reference or {})
    diagnostics: dict = {
        "cohort_size": n,
        "warnings": [],
        "balance_error_kwh": None,
        "component_error_kwh": None,
    }
    statistics = {}
    for kind, vectors in components.items():
        counts = Counter(clusters[kind].assignments.values())
        total_energy = float(samples[kind].sum())
        statistics[kind.value] = {
            label: {
                "customers": counts[label],
                "sample_daily_kwh": float(vector.sum()),
                "sample_energy_share": float(vector.sum()) / total_energy
                if total_energy
                else None,
                "peak_slot": int(vector.argmax()) + 1 if vector.max() > 0 else None,
                "load_factor": float(vector.mean() / vector.max())
                if vector.max() > 0
                else None,
            }
            for label, vector in vectors.items()
        }
    diagnostics["cluster_statistics"] = statistics
    if n < min_customers:
        diagnostics["warnings"].append("insufficient_samples")
    if billing_kwh is None:
        return ScaleResult(
            "missing_billing",
            samples,
            {},
            {},
            components,
            None,
            background,
            None,
            diagnostics,
        )
    if background == 0 and billing_kwh > 0:
        return ScaleResult(
            "no_positive_shape",
            samples,
            {},
            {},
            components,
            None,
            background,
            billing_kwh,
            diagnostics,
        )
    alpha = billing_kwh / background if background else None
    if alpha is not None and not math.isfinite(alpha):
        raise ValueError("expansion factor overflow")
    multiplier = alpha if alpha is not None else 0.0
    energy = {kind: vector * multiplier for kind, vector in samples.items()}
    contributions = {
        kind: {label: vector * multiplier for label, vector in groups.items()}
        for kind, groups in components.items()
    }
    if any(not np.isfinite(vector).all() for vector in energy.values()):
        raise ValueError("scaled energy overflow")
    total = math.fsum(
        day_counts[kind] * float(vector.sum()) for kind, vector in energy.items()
    )
    error = abs(total - billing_kwh)
    component_error = max(
        float(
            np.max(
                np.abs(
                    np.stack(list(contributions[kind].values())).sum(axis=0) - vector
                )
            )
        )
        for kind, vector in energy.items()
    )
    if error > max(1e-6, 1e-9 * abs(billing_kwh)) or component_error > max(
        1e-6, 1e-9 * abs(billing_kwh)
    ):
        raise ValueError("energy conservation check failed")
    diagnostics.update(balance_error_kwh=error, component_error_kwh=component_error)
    status = "valid"
    if billing_kwh == 0 and background > 0:
        diagnostics["warnings"].append("zero_billing_with_positive_sample")
        status = "valid_with_warnings"
    if n < min_customers:
        status = "preview_insufficient_samples"
    return ScaleResult(
        status,
        samples,
        energy,
        contributions,
        components,
        alpha,
        background,
        billing_kwh,
        diagnostics,
    )
