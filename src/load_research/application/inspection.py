"""Explain saved customer days from verified inputs, one customer-month at a time."""

from collections.abc import Callable
from datetime import date, datetime, timedelta

import numpy as np

from load_research.calendar import ResearchCalendar
from load_research.domain.config import RunConfig
from load_research.importers.catalog import Catalog
from load_research.infrastructure.store import IntervalStore
from load_research.quality import repair_month
from load_research.result_range import range_dates
from load_research.workspace import Workspace, file_hash


def inspect_customer(
    workspace: Workspace,
    run_id: str,
    customer_id: str,
    start: str,
    end: str,
    *,
    check: Callable[[], None] = lambda: None,
) -> dict:
    check()
    result = workspace.load_artifact(run_id, "result.json")
    dates = range_dates(result, start, end)
    config = RunConfig.from_dict(result["config"])
    catalog = Catalog.from_dict(workspace.load_artifact(run_id, "catalog.json"))
    if customer_id not in catalog.by_customer:
        raise ValueError(
            "Mã khách hàng không có trong danh mục mẫu của lần nghiên cứu."
        )
    imported = result["import"]
    database = workspace.safe_path(f"cache/{imported['key']}.duckdb")
    if not database.is_file() or file_hash(database) != imported["database_hash"]:
        raise ValueError("canonical cache is missing or changed")
    check()
    calendar = ResearchCalendar.from_dict(result["calendar"])
    rows, days = [], []
    with IntervalStore(
        database,
        memory_limit_mb=config.memory_limit_mb,
        threads=config.worker_threads,
        read_only=True,
    ) as store:
        store.validate()
        for period in sorted({day[:7] for day in dates}):
            check()
            grid = store.inspection_month(
                period, customer_id, config.interval_minutes, catalog
            )
            month = repair_month(grid, calendar, config)
            for day in (d for d in dates if d[:7] == period):
                check()
                index = date.fromisoformat(day).day - 1
                repaired = month.days[index]
                events = {event["slot_index"]: event for event in repaired.adjustments}
                day_start = datetime.combine(
                    date.fromisoformat(day), datetime.min.time()
                )
                day_end = day_start + timedelta(days=1)
                industries = sorted(
                    {
                        link.customer.industry_code
                        for link in catalog.by_customer[customer_id]
                        if link.valid_from < day_end and link.valid_to > day_start
                    }
                )
                days.append(
                    {
                        "date": day,
                        "day_type": calendar.classify(date.fromisoformat(day)).value,
                        "eligible": repaired.eligible,
                        "industry_code": grid.customer.industry_code,
                        "industry_codes": industries,
                        "original_month_coverage": month.original_coverage,
                    }
                )
                for slot, (original, value) in enumerate(
                    zip(grid.values[index], repaired.values, strict=True), 1
                ):
                    rows.append(
                        {
                            "customer_id": customer_id,
                            "date": day,
                            "slot_index": slot,
                            "original_kwh": float(original)
                            if np.isfinite(original)
                            else None,
                            "repaired_kwh": float(value)
                            if np.isfinite(value)
                            else None,
                            "estimated": bool(repaired.estimated[slot - 1]),
                            "quality_known": bool(grid.quality_known[index, slot - 1]),
                            "repair_blocked": bool(grid.repair_blocked[index, slot - 1])
                            if grid.repair_blocked is not None
                            else False,
                            "method": events.get(slot, {}).get("method", "source"),
                            "donor_dates": ", ".join(
                                events.get(slot, {}).get("donor_dates", [])
                            ),
                        }
                    )
    check()
    return {
        "run_id": run_id,
        "customer_id": customer_id,
        "date_start": start,
        "date_end": end,
        "interval_minutes": config.interval_minutes,
        "days": days,
        "rows": rows,
        "organization_scope": config.scope,
    }


def inspect_day(workspace: Workspace, run_id: str, customer_id: str, day: date) -> dict:
    details = inspect_customer(
        workspace, run_id, customer_id, day.isoformat(), day.isoformat()
    )
    return {**details, **details["days"][0]}
