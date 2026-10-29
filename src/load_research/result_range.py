"""Inclusive calendar ranges retain each industry's monthly expansion model."""

from collections.abc import Callable
from dataclasses import replace
from datetime import date, datetime, time, timedelta

import numpy as np

from load_research.calendar import ResearchCalendar
from load_research.domain.energy import normalize
from load_research.result_view import ResultSelection, build_daily_view


def range_dates(result: dict, start: str, end: str, day_types=()) -> list[str]:
    try:
        first, last = date.fromisoformat(start), date.fromisoformat(end)
    except ValueError as error:
        raise ValueError("Ngày phải có định dạng YYYY-MM-DD.") from error
    if first > last:
        raise ValueError("Từ ngày phải nhỏ hơn hoặc bằng đến ngày.")
    periods = set(result["config"].get("periods", ())) or {
        cell["year_month"] for cell in result["cells"]
    }
    if (
        not periods
        or first.strftime("%Y-%m") not in periods
        or last.strftime("%Y-%m") not in periods
    ):
        raise ValueError("Khoảng ngày nằm ngoài các tháng nghiên cứu đã lưu.")
    calendar = ResearchCalendar.from_dict(result.get("calendar", {}))
    days = []
    for index in range((last - first).days + 1):
        day = first + timedelta(days=index)
        if day.strftime("%Y-%m") not in periods:
            raise ValueError("Khoảng ngày bao gồm tháng chưa được nghiên cứu.")
        if not day_types or calendar.classify(day).value in day_types:
            days.append(day.isoformat())
    if not days:
        raise ValueError("Khoảng ngày không có loại ngày đã chọn.")
    return days


def concatenate_views(
    views: list[dict], selection: ResultSelection, start: str, end: str
) -> dict:
    if not views:
        raise ValueError("Khoảng ngày không có dữ liệu.")
    slots = 1440 // selection.interval_minutes
    ids = dict.fromkeys(row["id"] for view in views for row in view["series"])
    curves = []
    for identifier in ids:
        template = next(
            row for view in views for row in view["series"] if row["id"] == identifier
        )
        values: list[float | None] = []
        for view in views:
            row = next((r for r in view["series"] if r["id"] == identifier), None)
            values.extend(
                row["values"]
                if row is not None and row["values"] is not None
                else [None] * slots
            )
        if selection.normalization:
            shape = (
                normalize(np.asarray(values, dtype=float), selection.normalization)
                if all(v is not None for v in values)
                else None
            )
            vector = None if shape is None else shape.tolist()
        else:
            vector = values
        curves.append({**template, "values": vector})
    factors = {
        (r.get("year_month", v["year_month"]), r["industry_code"]): r
        for v in views
        for r in v["factors"]
    }
    strata_factors = {
        (r["industry_code"], r.get("year_month", v["year_month"]), r["stratum"]): {
            **r,
            "date": v["date"],
            "daily_method": v.get("method"),
        }
        for v in views
        for r in v.get("strata_factors", [])
    }
    billing = [r["billing_kwh"] for r in factors.values()]
    month_scopes = {}
    for period in sorted({v["year_month"] for v in views}):
        monthly = [v for v in views if v["year_month"] == period]
        month_scopes[period] = {
            "industry_codes": sorted(
                {code for v in monthly for code in v["industry_codes"]}
            ),
            "day_types": list(
                dict.fromkeys(kind for v in monthly for kind in v["day_types"])
            ),
        }
    return {
        **views[0],
        "industry_codes": sorted({code for v in views for code in v["industry_codes"]}),
        "month_scopes": month_scopes,
        "series": curves,
        "date": start if start == end else f"{start} → {end}",
        "date_start": start,
        "date_end": end,
        "timestamps": [
            (
                datetime.combine(date.fromisoformat(v["date"]), time())
                + timedelta(minutes=k * selection.interval_minutes)
            ).isoformat()
            for v in views
            for k in range(slots)
        ],
        "periods": sorted({v["year_month"] for v in views}),
        "day_types": list(dict.fromkeys(t for v in views for t in v["day_types"])),
        "day_count": len(views),
        "quality_statuses": sorted({s for v in views for s in v["quality_statuses"]}),
        "complete": all(v["complete"] for v in views),
        "missing": [{**r, "date": v["date"]} for v in views for r in v["missing"]],
        "factors": list(factors.values()),
        "strata_factors": list(strata_factors.values()),
        "daily_factors": [
            {**r, "date": v["date"], "year_month": v["year_month"]}
            for v in views
            for r in v.get("daily_factors", [])
        ],
        "billing_kwh": sum(billing)
        if billing and all(a is not None for a in billing)
        else None,
        "energy_selected_kwh": sum(v["energy_selected_kwh"] for v in views)
        if all(v["energy_selected_kwh"] is not None for v in views)
        else None,
        "normalization": selection.normalization,
        "unit": "p.u." if selection.normalization else selection.unit,
        "physical_unit": selection.unit,
    }


def build_range_view(
    result: dict,
    selection: ResultSelection,
    daily_by_period: dict,
    start: str,
    end: str,
    *,
    method: str,
    check: Callable[[], None] = lambda: None,
) -> dict:
    dates = range_dates(result, start, end, selection.day_types)
    views = []
    for day in dates:
        check()
        views.append(
            build_daily_view(
                result,
                replace(selection, period=day[:7], normalization=None),
                daily_by_period.get(day[:7], {}),
                day,
                method=method,
            )
        )
    return concatenate_views(views, selection, start, end)
