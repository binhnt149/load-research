"""Prepare the same selected views used on screen, inside the export worker."""

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from load_research.application.daily import load_daily
from load_research.calendar import ResearchCalendar, month_days
from load_research.result_reporting import export_views
from load_research.result_view import (
    ResultSelection,
    build_daily_view,
    build_result_view,
)
from load_research.workspace import Workspace


def export_selection(
    workspace: Workspace,
    result: dict,
    destination: Path,
    options: dict,
    check: Callable[[], None],
) -> Path:
    selection = ResultSelection(**options["view_selection"])
    periods = (
        [selection.period]
        if selection.period
        else sorted({cell["year_month"] for cell in result["cells"]})
    )
    views = []
    for period in periods:
        check()
        selected = replace(selection, period=period)
        if options.get("daily_method"):
            daily = load_daily(
                workspace,
                result,
                period,
                () if selected.level == "organization" else selected.industry_codes,
                check=check,
            )
            dates = options.get("dates") or [
                day.isoformat()
                for day in month_days(period)
                if not selected.day_types
                or ResearchCalendar.from_dict(result.get("calendar", {}))
                .classify(day)
                .value
                in selected.day_types
            ]
            for day in dates:
                check()
                views.append(
                    build_daily_view(
                        result, selected, daily, day, method=options["daily_method"]
                    )
                )
        else:
            views.append(build_result_view(result, selected))
    if options.get("cluster_ids"):
        for view in views:
            view["cluster_ids"] = options["cluster_ids"]
            view["series"] = [
                row
                for row in view["series"]
                if row["kind"] != "behavior"
                or row.get("cluster_id") in options["cluster_ids"]
            ]
    return export_views(
        result,
        views,
        destination,
        include_xlsx=options.get("include_xlsx", True),
        chart_formats=options.get("chart_formats", ()),
        layout=options.get("layout", "wide"),
        include_members=options.get("include_members", False),
        check=check,
    )
