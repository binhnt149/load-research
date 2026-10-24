"""Complete, validated snapshots of research and input semantics."""

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from zoneinfo import ZoneInfo

from load_research.calendar import month_days
from load_research.domain.energy import energy_from_value


def content_hash(payload: dict) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(encoded.encode()).hexdigest()


@dataclass(frozen=True)
class RunConfig:
    periods: tuple[str, ...]
    scope: str
    timezone: str = "Asia/Ho_Chi_Minh"
    interval_minutes: int = 30
    max_linear_minutes: int = 60
    max_like_minutes: int = 120
    min_donors: int = 3
    donor_scale_min: float = 0.5
    donor_scale_max: float = 2.0
    donor_common_fraction: float = 0.5
    mad_factor: float = 6.0
    mad_min_days: int = 3
    max_estimated_fraction: float = 0.1
    min_original_coverage: float = 0.8
    min_days: tuple[int, ...] = (5, 2, 2, 1)
    min_customers: int = 10
    min_cluster_customers: int = 30
    algorithm: str = "kmeans"
    manual_k: int | None = None
    k_min: int = 2
    k_max: int = 6
    seed: int = 42
    n_init: int = 10
    max_iter: int = 300
    silhouette_sample: int = 2000
    silhouette_min: float = 0.25
    silhouette_tie: float = 0.02
    min_cluster_size: int = 10
    min_cluster_fraction: float = 0.02
    eps: float | None = None
    min_samples: int = 10
    max_dbscan_vectors: int = 10000
    memory_limit_mb: int = 4096
    worker_threads: int = 2

    def __post_init__(self) -> None:
        object.__setattr__(self, "periods", tuple(self.periods))
        object.__setattr__(self, "min_days", tuple(self.min_days))
        if not self.periods or len(set(self.periods)) != len(self.periods):
            raise ValueError("periods must be non-empty and unique")
        for period in self.periods:
            month_days(period)
        if (
            not isinstance(self.scope, str)
            or not self.scope.strip()
            or len(self.scope) > 128
        ):
            raise ValueError("scope must be a non-empty string up to 128 characters")
        ZoneInfo(self.timezone)
        if self.interval_minutes not in (30, 60):
            raise ValueError("analysis interval must be 30 or 60 minutes")
        if self.algorithm not in ("kmeans", "dbscan"):
            raise ValueError("unknown clustering algorithm")
        integer_fields = (
            "min_donors",
            "min_customers",
            "min_cluster_customers",
            "k_min",
            "k_max",
            "n_init",
            "max_iter",
            "silhouette_sample",
            "min_cluster_size",
            "min_samples",
            "max_dbscan_vectors",
            "memory_limit_mb",
            "worker_threads",
            "mad_min_days",
        )
        for name in integer_fields:
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if self.k_min < 2 or self.k_max < self.k_min or self.k_max > 50:
            raise ValueError("invalid cluster range")
        if self.manual_k is not None and (
            type(self.manual_k) is not int or not 1 <= self.manual_k <= 50
        ):
            raise ValueError("manual_k must be an integer from 1 to 50")
        if len(self.min_days) != 4 or any(
            type(n) is not int or n < 1 for n in self.min_days
        ):
            raise ValueError("four positive minimum day counts are required")
        for name in ("max_linear_minutes", "max_like_minutes"):
            value = getattr(self, name)
            if type(value) is not int or value < 0 or value % self.interval_minutes:
                raise ValueError(f"{name} must align with analysis resolution")
        for name in (
            "max_estimated_fraction",
            "min_original_coverage",
            "silhouette_min",
            "silhouette_tie",
            "min_cluster_fraction",
            "donor_common_fraction",
        ):
            value = getattr(self, name)
            if (
                isinstance(value, bool)
                or not math.isfinite(value)
                or not 0 <= value <= 1
            ):
                raise ValueError(f"{name} must be a finite fraction")
        for name in ("donor_scale_min", "donor_scale_max", "mad_factor"):
            value = getattr(self, name)
            if isinstance(value, bool) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        if (
            self.donor_scale_min > self.donor_scale_max
            or self.donor_common_fraction <= 0
        ):
            raise ValueError("invalid donor scaling bounds or common fraction")
        if self.eps is not None and (not math.isfinite(self.eps) or self.eps <= 0):
            raise ValueError("eps must be finite and positive")
        if self.algorithm == "dbscan" and self.eps is None:
            raise ValueError("DBSCAN requires an explicit eps")
        if type(self.seed) is not int or not 0 <= self.seed < 2**32:
            raise ValueError("invalid random seed")

    def to_dict(self) -> dict:
        return json.loads(json.dumps(asdict(self), allow_nan=False))

    @classmethod
    def from_dict(cls, payload: dict) -> "RunConfig":
        return cls(**payload)

    @property
    def content_hash(self) -> str:
        return content_hash(self.to_dict())


@dataclass(frozen=True)
class SourceOptions:
    values_already_scaled: bool | None = None
    multiplier: float = 1.0
    interval_minutes: int = 30
    unit: str = "kWh"
    measurement_kind: str = "interval_energy"
    timestamp_convention: str = "start"
    timestamp_format: str | None = None
    timezone: str = "Asia/Ho_Chi_Minh"
    layout: str = "long"
    channel: str = "import_active"
    mapping: dict[str, str] = field(default_factory=dict)
    sheet: str | None = None
    delimiter: str = ","
    decimal: str = "."
    slot_prefix: str = "slot_"

    def __post_init__(self) -> None:
        if not isinstance(self.values_already_scaled, bool):
            raise ValueError("values_already_scaled must be explicitly declared")
        energy_from_value(
            0.0,
            self.unit,
            self.measurement_kind,
            self.interval_minutes,
            self.values_already_scaled,
            self.multiplier,
        )
        if self.timestamp_convention not in ("start", "end") or self.layout not in (
            "long",
            "wide",
        ):
            raise ValueError("invalid source convention/layout")
        if self.channel != "import_active":
            raise ValueError("only declared active import channel is supported")
        if len(self.delimiter) != 1 or self.decimal not in (".", ","):
            raise ValueError("invalid delimiter/decimal convention")
        if any(
            not isinstance(k, str) or not isinstance(v, str)
            for k, v in self.mapping.items()
        ):
            raise ValueError("mapping must contain string column names")
        ZoneInfo(self.timezone)

    def to_dict(self) -> dict:
        return asdict(self)
