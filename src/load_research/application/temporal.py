"""Read only selected months, then send bounded aggregate/customer curves to Qt."""

from collections.abc import Callable
from dataclasses import replace

from load_research.application.components import load_components
from load_research.application.daily import load_daily
from load_research.application.inspection import inspect_customer
from load_research.components import apply_component_catalog
from load_research.customer_view import build_customer_view
from load_research.result_range import build_range_view, range_dates
from load_research.result_view import ResultSelection
from load_research.workspace import Workspace


def load_temporal_view(
    workspace: Workspace, payload: dict, *, check: Callable[[], None] = lambda: None
) -> dict:
    result = workspace.load_artifact(payload["run_id"], "result.json")
    if payload.get("customer_id"):
        return build_customer_view(
            inspect_customer(
                workspace,
                payload["run_id"],
                payload["customer_id"],
                payload["date_start"],
                payload["date_end"],
                check=check,
            )
        )
    if payload.get("component_catalog_revision") is not None:
        result = apply_component_catalog(
            result, load_components(workspace, payload["component_catalog_revision"])
        )
    selection = ResultSelection(**payload["selection"])
    canonical = replace(
        selection,
        interval_minutes=result["config"]["interval_minutes"],
        unit="kWh",
        normalization=None,
    )
    periods = sorted(
        {
            day[:7]
            for day in range_dates(
                result, payload["date_start"], payload["date_end"], canonical.day_types
            )
        }
    )
    daily = {}
    for period in periods:
        check()
        daily[period] = load_daily(
            workspace,
            result,
            period,
            () if canonical.level == "organization" else canonical.industry_codes,
            check=check,
        )
    check()
    return build_range_view(
        result,
        canonical,
        daily,
        payload["date_start"],
        payload["date_end"],
        method=payload["method"],
        check=check,
    )
