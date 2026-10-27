"""Customer readings and conversions contain no sampling or expansion factors."""

import numpy as np

from load_research.daily import nullable
from load_research.domain.energy import convert_curve
from load_research.result_range import concatenate_views
from load_research.result_view import ResultSelection


def build_customer_view(details: dict) -> dict:
    source = details["interval_minutes"]
    selection = ResultSelection(
        details["date_start"][:7], interval_minutes=source, unit="kWh"
    )
    views = []
    for day in details["days"]:
        rows = [r for r in details["rows"] if r["date"] == day["date"]]
        if len(rows) != 1440 // source or [r["slot_index"] for r in rows] != list(
            range(1, 1440 // source + 1)
        ):
            raise ValueError("Chu kỳ khách hàng thiếu hoặc không đúng thứ tự.")
        processed = [r["repaired_kwh"] for r in rows]
        complete = all(v is not None for v in processed)
        views.append(
            {
                "run_id": details["run_id"],
                "customer_id": details["customer_id"],
                "organization_scope": details["organization_scope"],
                "date": day["date"],
                "year_month": day["date"][:7],
                "industry_codes": day.get("industry_codes", [day["industry_code"]]),
                "day_types": [day["day_type"]],
                "day_count": 1,
                "interval_minutes": source,
                "unit": "kWh",
                "physical_unit": "kWh",
                "normalization": None,
                "scope": "customer",
                "level": "customer",
                "method": "customer",
                "quality_statuses": [
                    "valid"
                    if day["eligible"]
                    and all(
                        r.get("quality_known", False) and not r.get("estimated", False)
                        for r in rows
                    )
                    else "valid_with_warnings"
                ],
                "factors": [],
                "missing": []
                if complete
                else [{"reason": "missing_customer_intervals", "date": day["date"]}],
                "billing_kwh": None,
                "complete": complete,
                "energy_selected_kwh": sum(processed) if complete else None,
                "series": [
                    {
                        "id": kind,
                        "kind": kind,
                        "label": label,
                        "values": [r[field] for r in rows],
                    }
                    for kind, label, field in [
                        ("source", "Khách hàng trước VEE", "original_kwh"),
                        ("processed", "Khách hàng sau VEE", "repaired_kwh"),
                    ]
                ],
            }
        )
    view = concatenate_views(
        views, selection, details["date_start"], details["date_end"]
    )
    by_date = {day["date"]: day for day in details["days"]}
    view["inspection_rows"] = [
        {
            **r,
            "eligible": by_date[r["date"]]["eligible"],
            "original_month_coverage": by_date[r["date"]].get(
                "original_month_coverage"
            ),
        }
        for r in details["rows"]
    ]
    return view


def convert_temporal_view(view: dict, selection: ResultSelection) -> dict:
    if view["unit"] != "kWh" or view["normalization"] is not None:
        raise ValueError(
            "Dữ liệu nền khoảng ngày phải là điện năng kWh chưa chuẩn hóa."
        )
    source = view["interval_minutes"]
    curves = []
    for row in view["series"]:
        values = row["values"]
        if values is None or (
            selection.normalization and any(v is None for v in values)
        ):
            converted = None
        else:
            converted = convert_curve(
                values,
                source,
                selection.interval_minutes,
                selection.unit,
                selection.normalization,
            )
        curves.append(
            {
                **row,
                "values": None
                if converted is None
                else nullable(np.asarray(converted)),
            }
        )
    factor = selection.interval_minutes // source
    # convert_curve validates resolution even when every curve is unavailable.
    convert_curve(
        [0] * (1440 // source), source, selection.interval_minutes, selection.unit
    )
    return {
        **view,
        "series": curves,
        "timestamps": view["timestamps"][::factor],
        "interval_minutes": selection.interval_minutes,
        "physical_unit": selection.unit,
        "unit": "p.u." if selection.normalization else selection.unit,
        "normalization": selection.normalization,
    }
