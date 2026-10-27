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
    views = _prepare_views(workspace, result, selection, options, check)
    for view in views:
        view["hidden_series_ids"] = options.get("hidden_series_ids", [])
        view["chart_stacked"] = options.get("chart_stacked", False)
        if not options.get("show_components", True):
            view["chart_families"] = []
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


def _prepare_views(workspace, result, selection, options, check):
    if options.get("date_start"):
        from dataclasses import asdict

        from load_research.application.temporal import load_temporal_view
        from load_research.customer_view import convert_temporal_view

        raw = load_temporal_view(
            workspace,
            {
                "run_id": result["run_id"],
                "selection": asdict(selection),
                "date_start": options["date_start"],
                "date_end": options["date_end"],
                "method": options.get("daily_method", "representative"),
                "customer_id": options.get("customer_id", ""),
                "component_catalog_revision": options.get("component_catalog_revision"),
            },
            check=check,
        )
        return [convert_temporal_view(raw, selection)]
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
    return views
