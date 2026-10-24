"""Explain one saved customer-day from verified, immutable inputs."""

from datetime import date

import numpy as np

from load_research.calendar import ResearchCalendar
from load_research.domain.config import RunConfig
from load_research.importers.catalog import Catalog
from load_research.infrastructure.store import IntervalStore
from load_research.quality import repair_month
from load_research.workspace import Workspace, file_hash


def inspect_day(workspace: Workspace, run_id: str, customer_id: str, day: date) -> dict:
    result = workspace.load_artifact(run_id, "result.json")
    config = RunConfig.from_dict(result["config"])
    period = day.strftime("%Y-%m")
    if period not in config.periods:
        raise ValueError("date is outside the saved research periods")
    catalog = Catalog.from_dict(workspace.load_artifact(run_id, "catalog.json"))
    imported = result["import"]
    database = workspace.safe_path(f"cache/{imported['key']}.duckdb")
    if file_hash(database) != imported["database_hash"]:
        raise ValueError("canonical cache is missing or changed")
    with IntervalStore(
        database,
        memory_limit_mb=config.memory_limit_mb,
        threads=config.worker_threads,
        read_only=True,
    ) as store:
        store.validate()
        grid = store.customer_month(
            period, customer_id, config.interval_minutes, catalog
        )
    calendar = ResearchCalendar.from_dict(result["calendar"])
    month = repair_month(grid, calendar, config)
    index = day.day - 1
    repaired = month.days[index]
    events = {event["slot_index"]: event for event in repaired.adjustments}
    rows = []
    for slot, (original, value) in enumerate(
        zip(grid.values[index], repaired.values, strict=True), 1
    ):
        rows.append(
            {
                "slot_index": slot,
                "original_kwh": float(original) if np.isfinite(original) else None,
                "repaired_kwh": float(value) if np.isfinite(value) else None,
                "estimated": bool(repaired.estimated[slot - 1]),
                "repair_blocked": bool(grid.repair_blocked[index, slot - 1])
                if grid.repair_blocked is not None
                else False,
                "method": events.get(slot, {}).get("method", "source"),
                "donor_dates": ", ".join(events.get(slot, {}).get("donor_dates", [])),
            }
        )
    return {
        "run_id": run_id,
        "customer_id": customer_id,
        "date": day.isoformat(),
        "day_type": calendar.classify(day).value,
        "interval_minutes": config.interval_minutes,
        "eligible": repaired.eligible,
        "original_month_coverage": month.original_coverage,
        "rows": rows,
    }
