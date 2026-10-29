from dataclasses import replace

import pytest

from load_research.domain.config import RunConfig, SourceOptions


def test_new_source_floors_timestamps_but_old_saved_request_keeps_strict_alignment():
    from load_research.application.models import SourceInput, StudyRequest

    source = SourceOptions(values_already_scaled=True)
    assert source.timestamp_alignment == "floor"
    request = StudyRequest(
        RunConfig(periods=("2026-01",), scope="NPC"),
        ("cmis.csv",),
        (SourceInput("mdms.csv", source),),
    )
    assert (
        StudyRequest.from_dict(request.to_dict())
        .mdms_sources[0]
        .options.timestamp_alignment
        == "floor"
    )
    old = request.to_dict()
    del old["mdms_sources"][0]["options"]["timestamp_alignment"]
    del old["meter_key_policy"]
    assert (
        StudyRequest.from_dict(old).mdms_sources[0].options.timestamp_alignment
        == "strict"
    )
    assert StudyRequest.from_dict(old).meter_key_policy == "legacy"
    assert StudyRequest.from_dict(request.to_dict()).meter_key_policy == "trimmed"


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


def test_stratum_configuration_source_roundtrips_and_is_part_of_manifest(tmp_path):
    from dataclasses import replace

    from load_research.application.models import SourceInput, StudyRequest
    from load_research.domain.config import RunConfig, SourceOptions

    source = tmp_path / "strata.xlsx"
    request = StudyRequest(
        RunConfig(periods=("2026-01",), scope="NPC"),
        (str(tmp_path / "cmis.xlsx"),),
        (
            SourceInput(
                str(tmp_path / "mdms.csv"), SourceOptions(values_already_scaled=True)
            ),
        ),
        strata_paths=(str(source),),
    )
    assert StudyRequest.from_dict(request.to_dict()).to_dict() == request.to_dict()
    assert source.resolve() in request.all_paths()
    with pytest.raises(ValueError):
        replace(request, strata_paths=(str(source), str(tmp_path / "other.xlsx")))


def test_old_study_configuration_preserves_conflict_rejection_policy():
    config = RunConfig(periods=("2026-01",), scope="NPC")
    assert config.collision_policy == "prefer_nearest"
    old = config.to_dict()
    old.pop("collision_policy")
    assert RunConfig.from_dict(old).collision_policy == "reject"
