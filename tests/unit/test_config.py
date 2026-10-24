from dataclasses import replace

import pytest

from load_research.domain.config import RunConfig, SourceOptions


def test_run_config_roundtrip_and_hash_are_stable():
    config = RunConfig(periods=("2024-02",), scope="NPC")
    assert RunConfig.from_dict(config.to_dict()) == config
    assert replace(config).content_hash == config.content_hash
    assert (
        replace(config, max_estimated_fraction=0.2).content_hash != config.content_hash
    )
    assert config.interval_minutes == 30


@pytest.mark.parametrize(
    "changes",
    [
        {"max_estimated_fraction": -0.1},
        {"min_original_coverage": 1.1},
        {"min_customers": 0},
        {"interval_minutes": 20},
        {"algorithm": "unknown"},
        {"algorithm": "dbscan", "eps": None},
        {"eps": float("nan")},
        {"periods": ("2024-13",)},
        {"scope": ""},
        {"k_min": 8, "k_max": 2},
    ],
)
def test_invalid_configuration_is_rejected(changes):
    with pytest.raises((ValueError, TypeError)):
        replace(RunConfig(periods=("2024-02",), scope="NPC"), **changes)


def test_unknown_config_fields_are_not_silently_ignored():
    with pytest.raises((ValueError, TypeError)):
        RunConfig.from_dict(
            {"periods": ["2024-02"], "scope": "NPC", "arbitrary_code": "x"}
        )


def test_measurement_semantics_and_scaling_must_be_declared():
    with pytest.raises(ValueError):
        SourceOptions(values_already_scaled=None)
    with pytest.raises(ValueError):
        SourceOptions(values_already_scaled=False, multiplier=0)
    assert SourceOptions(values_already_scaled=True).unit == "kWh"
