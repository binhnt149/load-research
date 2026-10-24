from dataclasses import replace

import numpy as np
import pytest

from load_research.calendar import DayType
from load_research.clustering import cluster_profiles
from load_research.domain.config import RunConfig
from load_research.importers.catalog import Customer
from load_research.profiles import CustomerProfile


def profile(identifier, vector):
    return CustomerProfile(
        Customer(str(identifier), "01"),
        "2024-02",
        DayType.WEEKDAY,
        np.asarray(vector, float),
    )


def shapes():
    first = np.r_[np.ones(24), np.zeros(24)]
    second = np.r_[np.zeros(24), np.ones(24)]
    return [profile(index, first * (index + 1)) for index in range(20)] + [
        profile(index + 20, second) for index in range(20)
    ]


def test_kmeans_is_scale_invariant_and_reproducible():
    config = RunConfig(periods=("2024-02",), scope="NPC")
    first = cluster_profiles(shapes(), config)
    second = cluster_profiles(list(reversed(shapes())), config)
    assert first.assignments == second.assignments
    assert len(set(first.assignments.values())) == 2
    assert first.assignments["0"] == first.assignments["19"]
    assert first.assignments["0"] != first.assignments["20"]
    assert first.diagnostics["silhouette"] == pytest.approx(1)


def test_inactive_and_small_cohort_do_not_produce_fake_silhouette():
    config = RunConfig(periods=("2024-02",), scope="NPC")
    result = cluster_profiles(
        [profile("zero", np.zeros(48)), profile("one", np.ones(48))], config
    )
    assert result.assignments == {"one": "not_segmented", "zero": "inactive"}
    assert result.diagnostics["silhouette"] is None


def test_dbscan_keeps_noise_as_a_contribution_group():
    config = replace(
        RunConfig(periods=("2024-02",), scope="NPC"),
        algorithm="dbscan",
        eps=0.02,
        min_samples=5,
    )
    result = cluster_profiles(
        shapes() + [profile("noise", np.r_[1, np.zeros(47)])], config
    )
    assert result.assignments["noise"] == "unclassified"
    assert len(result.assignments) == 41
    assert result.diagnostics["noise_count"] == 1


def test_dbscan_resource_limit_is_enforced_before_fitting():
    config = replace(
        RunConfig(periods=("2024-02",), scope="NPC"),
        algorithm="dbscan",
        eps=0.02,
        max_dbscan_vectors=35,
    )
    with pytest.raises(ValueError, match="resource"):
        cluster_profiles(shapes(), config)


def test_manual_cluster_count_is_explicit_and_reports_small_groups():
    config = replace(RunConfig(periods=("2024-02",), scope="NPC"), manual_k=2)
    result = cluster_profiles(shapes()[:2] + [shapes()[-1]], config)
    assert len(set(result.assignments.values())) == 2
    assert result.diagnostics["manual"]
    assert "small_clusters" in result.diagnostics["warnings"]


def test_k_selection_uses_global_maximum_for_silhouette_ties(monkeypatch):
    rng = np.random.default_rng(42)
    profiles = [profile(index, rng.uniform(1, 2, 48)) for index in range(100)]
    scores = iter([0.260, 0.275, 0.285])
    monkeypatch.setattr(
        "load_research.clustering._silhouette", lambda *args: next(scores)
    )
    config = replace(
        RunConfig(periods=("2024-02",), scope="NPC"),
        k_max=4,
        min_cluster_size=1,
        min_cluster_fraction=0,
    )
    result = cluster_profiles(profiles, config)
    assert len(set(result.assignments.values())) == 3
    assert result.diagnostics["silhouette"] == 0.275


def test_roundoff_in_proportional_vectors_does_not_create_behavioural_groups(
    monkeypatch,
):
    rng = np.random.default_rng(9)
    base = np.arange(48) % 7 + 1
    profiles = [
        profile(index, base * factor)
        for index, factor in enumerate(rng.uniform(0.1, 10, 50))
    ]

    def unexpected_fit(**kwargs):
        raise AssertionError("KMeans must not split numerical roundoff into behaviours")

    monkeypatch.setattr("load_research.clustering.KMeans", unexpected_fit)
    result = cluster_profiles(profiles, RunConfig(periods=("2024-02",), scope="NPC"))
    assert set(result.assignments.values()) == {"not_segmented"}
