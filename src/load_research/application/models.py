"""Serializable requests shared by CLI, desktop and spawned workers."""

import json
from dataclasses import dataclass, field
from pathlib import Path

from load_research.calendar import ResearchCalendar
from load_research.domain.config import RunConfig, SourceOptions


@dataclass(frozen=True)
class SourceInput:
    path: str
    options: SourceOptions

    def to_dict(self) -> dict:
        return {"path": str(self.path), "options": self.options.to_dict()}


@dataclass(frozen=True)
class StudyRequest:
    config: RunConfig
    cmis_paths: tuple[str, ...]
    mdms_sources: tuple[SourceInput, ...]
    billing_paths: tuple[str, ...] = ()
    calendar: ResearchCalendar = field(default_factory=ResearchCalendar)
    calendar_paths: tuple[str, ...] = ()
    cmis_mapping: dict[str, str] = field(default_factory=dict)
    billing_mapping: dict[str, str] = field(default_factory=dict)
    cmis_sheet: str | None = None
    billing_sheet: str | None = None
    table_delimiter: str = ","
    selected_industries: tuple[str, ...] = ()
    meter_key_policy: str = "trimmed"
    strata_paths: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.meter_key_policy not in ("legacy", "trimmed"):
            raise ValueError("invalid meter key policy")
        if len(self.strata_paths) > 1:
            raise ValueError("only one stratum configuration may be supplied")
        if not self.cmis_paths or not self.mdms_sources:
            raise ValueError("CMIS and MDMS sources are required")
        if any(
            source.options.interval_minutes > self.config.interval_minutes
            for source in self.mdms_sources
        ):
            raise ValueError(
                "MDMS resolution cannot produce the requested analysis resolution"
            )
        if len(self.table_delimiter) != 1:
            raise ValueError("invalid table delimiter")
        if any(
            source.options.timezone != self.config.timezone
            for source in self.mdms_sources
        ):
            raise ValueError("source and analysis timezone must agree")

    def all_paths(self) -> list[Path]:
        names = [
            *self.cmis_paths,
            *(source.path for source in self.mdms_sources),
            *self.billing_paths,
            *self.calendar_paths,
            *self.strata_paths,
        ]
        return list(dict.fromkeys(Path(name).resolve() for name in names))

    def to_dict(self) -> dict:
        return {
            "config": self.config.to_dict(),
            "cmis_paths": list(self.cmis_paths),
            "mdms_sources": [source.to_dict() for source in self.mdms_sources],
            "billing_paths": list(self.billing_paths),
            "calendar": self.calendar.to_dict(),
            "calendar_paths": list(self.calendar_paths),
            "cmis_mapping": self.cmis_mapping,
            "billing_mapping": self.billing_mapping,
            "cmis_sheet": self.cmis_sheet,
            "billing_sheet": self.billing_sheet,
            "table_delimiter": self.table_delimiter,
            "selected_industries": list(self.selected_industries),
            "meter_key_policy": self.meter_key_policy,
            "strata_paths": list(self.strata_paths),
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "StudyRequest":
        copied = dict(payload)
        copied.setdefault("meter_key_policy", "legacy")
        copied["config"] = RunConfig.from_dict(copied["config"])
        copied["calendar"] = ResearchCalendar.from_dict(copied.get("calendar", {}))
        copied["mdms_sources"] = tuple(
            SourceInput(
                source["path"],
                SourceOptions(**{"timestamp_alignment": "strict", **source["options"]}),
            )
            for source in copied["mdms_sources"]
        )
        for name in (
            "cmis_paths",
            "billing_paths",
            "calendar_paths",
            "selected_industries",
            "strata_paths",
        ):
            copied[name] = tuple(copied.get(name, ()))
        return cls(**copied)


def load_request(path: Path) -> StudyRequest:
    """Resolve portable source paths relative to the request, never the shell CWD."""
    path = Path(path).resolve()
    payload = json.loads(path.read_text(encoding="utf-8"))
    for field_name in ("cmis_paths", "billing_paths", "calendar_paths", "strata_paths"):
        payload[field_name] = [
            str((path.parent / source).resolve())
            for source in payload.get(field_name, [])
        ]
    for source in payload["mdms_sources"]:
        source["path"] = str((path.parent / source["path"]).resolve())
    return StudyRequest.from_dict(payload)
