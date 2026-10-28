"""Physical units and resolution changes that preserve interval energy."""

import math
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
from numpy.typing import ArrayLike, NDArray

FloatArray = NDArray[np.float64]
ENERGY_UNITS = {"Wh": 0.001, "kWh": 1.0, "MWh": 1000.0}
POWER_UNITS = {"W": 0.001, "kW": 1.0, "MW": 1000.0}


def positive_finite(value: float, name: str) -> float:
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive")
    return value


def average_power_kw(energy_kwh: float, interval_hours: float) -> float:
    if not math.isfinite(energy_kwh) or energy_kwh < 0:
        raise ValueError("energy_kwh must be finite and non-negative")
    return energy_kwh / positive_finite(interval_hours, "interval_hours")


def energy_from_value(
    value: float,
    unit: str,
    measurement_kind: str,
    minutes: int,
    already_scaled: bool,
    multiplier: float,
) -> float:
    if minutes not in (15, 30, 60):
        raise ValueError("interval must be 15, 30 or 60 minutes")
    if not isinstance(already_scaled, bool):
        raise ValueError("scaling must be declared")
    positive_finite(multiplier, "multiplier")
    if not math.isfinite(value) or value < 0:
        raise ValueError("measurement must be finite and non-negative")
    if measurement_kind == "interval_energy" and unit in ENERGY_UNITS:
        energy = value * ENERGY_UNITS[unit]
    elif measurement_kind == "interval_average_power" and unit in POWER_UNITS:
        energy = value * POWER_UNITS[unit] * minutes / 60
    else:
        raise ValueError("measurement kind and unit are incompatible")
    result = energy if already_scaled else energy * multiplier
    if not math.isfinite(result):
        raise ValueError("measurement overflow")
    return result


def resample_energy(
    values: ArrayLike, source_minutes: int, target_minutes: int
) -> FloatArray:
    if source_minutes not in (15, 30, 60) or target_minutes not in (15, 30, 60):
        raise ValueError("unsupported resolution")
    if target_minutes < source_minutes or target_minutes % source_minutes:
        raise ValueError("cannot increase temporal resolution")
    vector = np.asarray(values, dtype=np.float64)
    factor = target_minutes // source_minutes
    if vector.ndim != 1 or len(vector) % factor:
        raise ValueError("incomplete resolution block")
    if np.isinf(vector).any() or (vector < 0).any():
        raise ValueError("invalid interval energy")
    return vector.reshape(-1, factor).sum(axis=1)


def normalize(values: ArrayLike, kind: str = "share") -> FloatArray | None:
    vector = np.asarray(values, dtype=np.float64)
    if (
        vector.ndim != 1
        or not len(vector)
        or not np.isfinite(vector).all()
        or (vector < 0).any()
    ):
        raise ValueError("shape must be a non-negative finite vector")
    if kind not in ("share", "mean", "peak"):
        raise ValueError("unknown normalization")
    total = float(vector.sum())
    if total == 0:
        return None
    denominator = {
        "share": total,
        "mean": total / len(vector),
        "peak": float(vector.max()),
    }[kind]
    return vector / denominator


def interval_start(
    timestamp: str | datetime,
    minutes: int,
    convention: str = "start",
    timezone: str = "Asia/Ho_Chi_Minh",
    timestamp_format: str | None = None,
    *,
    alignment: str = "strict",
) -> datetime:
    return interval_times(
        timestamp, minutes, convention, timezone, timestamp_format, alignment=alignment
    )[0]


def interval_times(
    timestamp: str | datetime,
    minutes: int,
    convention: str = "start",
    timezone: str = "Asia/Ho_Chi_Minh",
    timestamp_format: str | None = None,
    *,
    alignment: str = "strict",
) -> tuple[datetime, datetime, datetime]:
    if (
        minutes not in (15, 30, 60)
        or convention not in ("start", "end")
        or alignment not in ("strict", "floor")
    ):
        raise ValueError("invalid interval convention")
    if isinstance(timestamp, datetime):
        parsed = timestamp
    else:
        parsed = (
            datetime.strptime(timestamp, timestamp_format)
            if timestamp_format
            else datetime.fromisoformat(timestamp)
        )
    zone = ZoneInfo(timezone)
    parsed = (
        parsed.replace(tzinfo=zone)
        if parsed.tzinfo is None
        else parsed.astimezone(zone)
    )
    original = parsed
    if alignment == "strict" and (
        parsed.second or parsed.microsecond or parsed.minute % minutes
    ):
        raise ValueError("timestamp must be aligned to interval boundaries")
    if alignment == "floor":
        parsed = parsed.replace(
            minute=parsed.minute // minutes * minutes, second=0, microsecond=0
        )
    start = parsed - timedelta(minutes=minutes) if convention == "end" else parsed
    return start, original, parsed


def convert_curve(
    values,
    source_minutes: int,
    target_minutes: int,
    unit: str,
    normalization: str | None = None,
) -> np.ndarray | None:
    energy = resample_energy(values, source_minutes, target_minutes)
    if normalization is not None:
        return normalize(energy, normalization)
    if unit not in ("kW", "kWh"):
        raise ValueError("physical output unit must be kW or kWh")
    return energy * 60 / target_minutes if unit == "kW" else energy
