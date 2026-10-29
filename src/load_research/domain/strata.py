"""Explicit boundary policies for annual customer-consumption groups."""

import math
from bisect import bisect_left, bisect_right


def classify_annual_energy(kwh: float, *, boundary: str) -> str | None:
    if boundary not in {"higher", "lower"}:
        raise ValueError("invalid stratum boundary policy")
    if not math.isfinite(kwh) or kwh < 0:
        raise ValueError("annual energy must be finite and non-negative")
    if kwh < 501:
        return None
    cutpoints = (10000, 100000, 1000000, 10000000)
    index = (bisect_right if boundary == "higher" else bisect_left)(cutpoints, kwh)
    return "ABCDE"[index]
