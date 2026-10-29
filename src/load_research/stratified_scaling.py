"""Scale each declared industry stratum independently, then combine physical curves."""

import math
from dataclasses import dataclass

import numpy as np

from load_research.calendar import DayType
from load_research.clustering import ClusterResult
from load_research.profiles import CustomerProfile
from load_research.scaling import ScaleResult, scale_industry


@dataclass
class StratifiedScaleResult:
    status: str
    strata: dict[str, ScaleResult]
    energy: dict[DayType, np.ndarray]


def allocate_monthly_by_reference(
    monthly_kwh: float, reference_kwh: dict[str, float]
) -> dict[str, float]:
    """Estimate stratum totals using the supplied reference-period energy shares."""
    if not math.isfinite(monthly_kwh) or monthly_kwh < 0:
        raise ValueError("invalid industry monthly energy")
    if not reference_kwh or set(reference_kwh) - set("ABCDE"):
        raise ValueError("invalid or empty reference strata")
    if any(not math.isfinite(value) or value < 0 for value in reference_kwh.values()):
        raise ValueError("invalid reference energy")
    total = math.fsum(reference_kwh.values())
    if not math.isfinite(total) or total <= 0:
        raise ValueError("reference energy must have positive total")
    return {key: monthly_kwh * (value / total) for key, value in reference_kwh.items()}


def scale_strata(
    samples: dict[str, tuple[list[CustomerProfile], dict[DayType, ClusterResult]]],
    monthly_totals: dict[str, float | None],
    day_counts: dict[DayType, int],
    *,
    min_customers: int,
) -> StratifiedScaleResult:
    """Every populated/required stratum must be explicitly included in the inputs."""
    keys = set(samples) | set(monthly_totals)
    if not keys or keys - set("ABCDE"):
        raise ValueError("invalid or empty consumption strata")
    owners: dict[str, str] = {}
    cells = set()
    for stratum, (profiles, _groups) in samples.items():
        for profile in profiles:
            identifier = profile.customer.customer_id
            if identifier in owners and owners[identifier] != stratum:
                raise ValueError("customer is assigned to multiple strata")
            owners[identifier] = stratum
            cells.add((profile.customer.industry_code, profile.period))
    if len(cells) > 1:
        raise ValueError("strata must belong to one industry-month")
    results = {}
    for key in sorted(keys):
        profiles, clusters = samples.get(key, ([], {}))
        results[key] = scale_industry(
            profiles,
            clusters,
            day_counts,
            monthly_totals.get(key),
            min_customers=min_customers,
        )
    if any(not result.energy for result in results.values()):
        return StratifiedScaleResult("incomplete", results, {})
    energy = {
        kind: np.stack([result.energy[kind] for result in results.values()]).sum(axis=0)
        for kind, count in day_counts.items()
        if count > 0
    }
    status = (
        "preview_insufficient_samples"
        if any(
            result.status == "preview_insufficient_samples"
            for result in results.values()
        )
        else "valid_with_warnings"
        if any(result.status == "valid_with_warnings" for result in results.values())
        else "valid"
    )
    return StratifiedScaleResult(status, results, energy)


def scale_stratified_industry(
    profiles: list[CustomerProfile],
    clusters: dict[DayType, ClusterResult],
    day_counts: dict[DayType, int],
    monthly_kwh: float | None,
    population: dict,
    *,
    min_customers: int,
) -> tuple[ScaleResult, dict]:
    """Keep industry behavior groups while applying a separate factor to each stratum."""
    base = scale_industry(
        profiles, clusters, day_counts, monthly_kwh, min_customers=min_customers
    )
    reference = {key: value.reference_energy_kwh for key, value in population.items()}
    if not reference or math.fsum(reference.values()) <= 0:
        base.status, base.energy, base.contributions, base.alpha = (
            "missing_stratum_config",
            {},
            {},
            None,
        )
        return base, {"method": "reference_energy_share", "strata": {}}
    allocations: dict[str, float | None] = {key: None for key in reference}
    if monthly_kwh is not None:
        allocations.update(allocate_monthly_by_reference(monthly_kwh, reference))
    samples = {}
    for key in reference:
        selected = [
            profile
            for profile in profiles
            if profile.customer.consumption_stratum == key
        ]
        by_day = {
            kind: ClusterResult(
                {
                    profile.customer.customer_id: clusters[kind].assignments[
                        profile.customer.customer_id
                    ]
                    for profile in selected
                    if profile.day_type == kind
                },
                {},
                {},
            )
            for kind, count in day_counts.items()
            if count > 0
        }
        samples[key] = (selected, by_day)
    result = scale_strata(samples, allocations, day_counts, min_customers=min_customers)
    base.alpha = None
    base.energy = result.energy
    base.status = (
        "incomplete_strata" if result.status == "incomplete" else result.status
    )
    base.diagnostics.setdefault("warnings", []).append(
        "reference_share_assumes_monthly_stability"
    )
    if base.status == "valid":
        base.status = "valid_with_warnings"
    base.contributions = {}
    if result.energy:
        for kind in result.energy:
            vectors: dict[str, np.ndarray] = {}
            for subresult in result.strata.values():
                for label, vector in subresult.contributions[kind].items():
                    vectors[label] = vectors.get(label, np.zeros_like(vector)) + vector
            base.contributions[kind] = vectors
        balance = abs(
            math.fsum(day_counts[k] * float(v.sum()) for k, v in result.energy.items())
            - (monthly_kwh or 0)
        )
        base.diagnostics["balance_error_kwh"] = balance
        base.diagnostics["component_error_kwh"] = max(
            float(np.max(np.abs(sum(base.contributions[k].values()) - v)))
            for k, v in result.energy.items()
        )
    else:
        base.diagnostics["balance_error_kwh"] = None
        base.diagnostics["component_error_kwh"] = None
    details = {
        "method": "reference_energy_share",
        "strata": {
            key: {
                "population_count": population[key].population_count,
                "reference_energy_kwh": reference[key],
                "allocated_billing_kwh": allocations[key],
                "cohort_size": len({p.customer.customer_id for p in samples[key][0]}),
                "result": subresult.to_dict(),
            }
            for key, subresult in result.strata.items()
        },
    }
    return base, details
