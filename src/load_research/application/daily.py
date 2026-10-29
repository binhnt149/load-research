"""Read saved daily sums, or reconstruct legacy runs from verified canonical data."""

from collections.abc import Callable

import numpy as np

from load_research.calendar import ResearchCalendar, month_days
from load_research.daily import DailyAccumulator
from load_research.domain.config import RunConfig
from load_research.importers.catalog import Catalog
from load_research.infrastructure.store import IntervalStore
from load_research.quality import repair_month
from load_research.workspace import Workspace, file_hash


def load_daily(
    workspace: Workspace,
    result: dict,
    period: str,
    codes: tuple[str, ...],
    *,
    check: Callable[[], None] = lambda: None,
) -> dict:
    config = RunConfig.from_dict(result["config"])
    if period not in config.periods:
        raise ValueError("date is outside the saved research periods")
    cells = [
        cell
        for cell in result["cells"]
        if cell["year_month"] == period
        and (not codes or cell["industry_code"] in codes)
    ]
    output: dict = {}
    legacy = []
    for cell in cells:
        check()
        if "daily_artifact" in cell:
            output[cell["industry_code"]] = workspace.load_artifact(
                result["run_id"], cell["daily_artifact"]
            )
        else:
            legacy.append(cell)
    if not legacy:
        return output
    imported = result["import"]
    database = workspace.safe_path(f"cache/{imported['key']}.duckdb")
    if not database.is_file() or file_hash(database) != imported["database_hash"]:
        raise ValueError("canonical cache is missing or changed")
    catalog = Catalog.from_dict(
        workspace.load_artifact(result["run_id"], "catalog.json")
    )
    calendar = ResearchCalendar.from_dict(result["calendar"])
    dates = month_days(period)
    with IntervalStore(
        database,
        memory_limit_mb=config.memory_limit_mb,
        threads=config.worker_threads,
        read_only=True,
    ) as store:
        store.validate(collision_policy=config.collision_policy)
        for cell in legacy:
            accumulator = DailyAccumulator(len(dates), 1440 // config.interval_minutes)
            members = {row["customer_id"]: row["weight"] for row in cell["members"]}
            for identifier, weight in sorted(members.items()):
                check()
                grid = store.customer_month(
                    period, identifier, config.interval_minutes, catalog
                )
                month = repair_month(grid, calendar, config)
                accumulator.add(
                    grid.values,
                    np.stack([day.values for day in month.days]),
                    [day.eligible for day in month.days],
                    weight,
                )
            if members:
                output[cell["industry_code"]] = accumulator.to_dict(
                    [day.isoformat() for day in dates],
                    [calendar.classify(day).value for day in dates],
                )
    check()
    return output
