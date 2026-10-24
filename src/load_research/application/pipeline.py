"""One reproducible pipeline for desktop, CLI and integration tests."""

import itertools
import json
import os
import platform
import shutil
from collections import Counter, defaultdict
from collections.abc import Callable, Iterator
from datetime import UTC, date, datetime, time, timedelta
from importlib import import_module
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

from load_research import METHOD_VERSION
from load_research.application.models import StudyRequest
from load_research.calendar import DayType, ResearchCalendar, month_days
from load_research.clustering import cluster_profiles
from load_research.domain.config import content_hash
from load_research.importers.catalog import Catalog, load_billing, load_catalog
from load_research.importers.metering import canonicalize
from load_research.importers.tables import read_rows
from load_research.infrastructure.store import IntervalStore
from load_research.profiles import select_profiles
from load_research.quality import repair_month
from load_research.scaling import scale_industry
from load_research.workspace import Workspace, atomic_json, file_hash


class ResearchCancelled(RuntimeError):
    """A cooperative cancellation, never a completed result."""


def runtime_versions() -> dict[str, str]:
    versions = {}
    for distribution, module in {
        "numpy": "numpy",
        "scikit-learn": "sklearn",
        "duckdb": "duckdb",
        "pyarrow": "pyarrow",
        "PySide6": "PySide6",
    }.items():
        try:
            versions[distribution] = version(distribution)
        except PackageNotFoundError:
            versions[distribution] = str(import_module(module).__version__)
    return versions


class IssueLog(list):
    """Keep a bounded preview in memory and every rejected row on disk."""

    def __init__(self, path: Path) -> None:
        super().__init__()
        self.total = 0
        self.path = path
        self.stream = path.open("x", encoding="utf-8")

    def append(self, issue: dict) -> None:
        self.total += 1
        self.stream.write(json.dumps(issue, ensure_ascii=False) + "\n")
        if len(self) < 1000:
            super().append(issue)

    def close(self) -> None:
        self.stream.close()


def _calendar(request: StudyRequest) -> ResearchCalendar:
    calendar = ResearchCalendar.from_dict(request.calendar.to_dict())
    for path in request.calendar_paths:
        for row in read_rows(Path(path), delimiter=request.table_delimiter):
            day = date.fromisoformat(row["date"])
            calendar.overrides[day] = DayType(row["day_type"])
    zone = ZoneInfo(request.config.timezone)
    for period in request.config.periods:
        for day in month_days(period):
            start = datetime.combine(day, time.min, tzinfo=zone)
            end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=zone)
            if start.utcoffset() != end.utcoffset():
                raise ValueError(
                    "DST transition days require a separate calendar policy"
                )
    return calendar


def _catalog(request: StudyRequest) -> Catalog:
    rows = itertools.chain.from_iterable(
        read_rows(
            Path(path),
            mapping=request.cmis_mapping,
            sheet=request.cmis_sheet,
            delimiter=request.table_delimiter,
        )
        for path in request.cmis_paths
    )
    return load_catalog(rows, request.config.scope)


def _prepare_cache(
    workspace: Workspace,
    request: StudyRequest,
    catalog: Catalog,
    run_id: str,
    check: Callable[[], None],
    progress: Callable[[dict], None],
) -> tuple[Path, dict]:
    source_paths = {str(Path(path).resolve()) for path in request.cmis_paths} | {
        str(Path(source.path).resolve()) for source in request.mdms_sources
    }
    manifest = [
        source
        for source in workspace.read_run(run_id)["sources"]
        if source["path"] in source_paths
    ]
    key = content_hash(
        {
            "schema": 3,
            "canonicalizer": "active-import-v3",
            "scope": request.config.scope,
            "periods": list(request.config.periods),
            "sources": manifest,
            "mapping": request.cmis_mapping,
            "sheet": request.cmis_sheet,
            "delimiter": request.table_delimiter,
            "mdms": [source.to_dict() for source in request.mdms_sources],
        }
    )
    database = workspace.safe_path(f"cache/{key}.duckdb")
    metadata = workspace.safe_path(f"cache/{key}.json")
    if metadata.exists():
        workspace.verify_sources(run_id)
        cached = json.loads(metadata.read_text())
        if (
            cached["key"] != key
            or not database.is_file()
            or file_hash(database) != cached["database_hash"]
        ):
            raise ValueError("canonical cache is missing or changed")
        log = workspace.safe_path(cached["issues_path"])
        if not log.is_file() or file_hash(log) != cached["issues_hash"]:
            raise ValueError("import issue journal is missing or changed")
        progress({"stage": "cache", "message": "Đã xác minh và dùng lại dữ liệu chuẩn"})
        return database, cached
    scratch = workspace.safe_path(f"temp/{run_id}.duckdb")
    issues_path = workspace.safe_path(f"runs/{run_id}/artifacts/import-issues.jsonl")
    issues = IssueLog(issues_path)
    source_ids = {source["path"]: source["sha256"] for source in manifest}
    try:
        with IntervalStore(
            scratch,
            memory_limit_mb=request.config.memory_limit_mb,
            threads=request.config.worker_threads,
        ) as store:
            for index, source in enumerate(request.mdms_sources):
                check()
                options = source.options
                rows = read_rows(
                    Path(source.path),
                    mapping=options.mapping,
                    sheet=options.sheet,
                    delimiter=options.delimiter,
                )

                def checked_rows(source_rows=rows) -> Iterator[dict]:
                    for number, row in enumerate(source_rows):
                        if number % 20000 == 0:
                            check()
                        yield row

                records = canonicalize(
                    checked_rows(),
                    catalog,
                    options,
                    source_id=source_ids[str(Path(source.path).resolve())],
                    issues=issues,
                )
                store.append(
                    record
                    for record in records
                    if record.start.strftime("%Y-%m") in request.config.periods
                )
                progress(
                    {
                        "stage": "import",
                        "completed": index + 1,
                        "total": len(request.mdms_sources),
                    }
                )
            check()
            store.validate()
            row_count = store.raw_count
    finally:
        issues.close()
    check()
    workspace.verify_sources(run_id)
    os.link(scratch, database)
    scratch.unlink()
    cached = {
        "key": key,
        "database_hash": file_hash(database),
        "raw_intervals": row_count,
        "issues_count": issues.total,
        "issues_preview": list(issues),
        "issues_path": str(issues_path.relative_to(workspace.root)),
        "issues_hash": file_hash(issues_path),
    }
    atomic_json(metadata, cached)
    return database, cached


def _analyse_month(
    store: IntervalStore,
    catalog: Catalog,
    request: StudyRequest,
    calendar: ResearchCalendar,
    period: str,
    billing: dict,
    check: Callable[[], None],
    journal,
    run_id: str,
) -> tuple[list[dict], dict]:
    quality: Counter[str] = Counter()
    reconciliation: dict = {}
    config_hash = request.config.content_hash

    def customer_months():
        for grid in store.iter_customer_months(
            period, request.config.interval_minutes, catalog
        ):
            check()
            month = repair_month(grid, calendar, request.config)
            quality["expected_intervals"] += grid.values.size
            quality["original_valid"] += sum(day.original_valid for day in month.days)
            quality["estimated_intervals"] += sum(
                int(day.estimated.sum()) for day in month.days
            )
            quality["unknown_source_quality"] += sum(
                day.unknown_count for day in month.days
            )
            quality["valid_days"] += sum(day.eligible for day in month.days)
            quality["adjustments"] += len(month.adjustments)
            for diagnostics in month.diagnostics.values():
                for name in ("mad_outliers", "zero_days", "flat_days"):
                    quality[name] += diagnostics[name]
            sample = catalog.sample_billing.get((grid.customer.customer_id, period))
            if sample:
                original_kwh = float(np.nansum(grid.values))
                available = (
                    sample.basis == "calendar_month" and np.isfinite(grid.values).all()
                )
                reconciliation[grid.customer.customer_id] = {
                    "status": "comparable" if available else "N/A",
                    "basis": sample.basis,
                    "cmis_kwh": sample.energy_kwh,
                    "mdms_original_kwh": original_kwh,
                    "coverage": month.original_coverage,
                    "difference_kwh": original_kwh - sample.energy_kwh
                    if available
                    else None,
                    "reason": None
                    if available
                    else "period_basis_unconfirmed_or_incomplete_mdms",
                }
            for event in month.adjustments:
                journal.write(
                    json.dumps(
                        {
                            **event,
                            "run_id": run_id,
                            "config_hash": config_hash,
                            "actor": "application",
                            "recorded_at": datetime.now(UTC).isoformat(),
                            "old_quality": "missing",
                            "new_quality": "application_estimated",
                        },
                        ensure_ascii=False,
                        allow_nan=False,
                    )
                    + "\n"
                )
            yield month

    selection = select_profiles(customer_months(), calendar, request.config)
    _eligible, catalog_excluded = catalog.month_customers(period)
    excluded = {**catalog_excluded, **selection.excluded}
    grouped = defaultdict(list)
    for profile in selection.profiles:
        grouped[profile.customer.industry_code].append(profile)
    industries = {link.customer.industry_code for link in catalog.links} | {
        industry for industry, month in billing if month == period
    }
    if request.selected_industries:
        industries &= set(request.selected_industries)
    counts = calendar.counts(period)
    cells: list[dict] = []
    for industry in sorted(industries):
        check()
        profiles = grouped[industry]
        by_kind = {
            kind: [profile for profile in profiles if profile.day_type == kind]
            for kind in counts
            if counts[kind]
        }
        total = billing.get((industry, period))
        try:
            groups = {
                kind: cluster_profiles(group, request.config)
                for kind, group in by_kind.items()
            }
            scaled = scale_industry(
                profiles,
                groups,
                counts,
                total.energy_kwh if total else None,
                min_customers=request.config.min_customers,
            )
        except ValueError as error:
            cells.append(
                {
                    "industry_code": industry,
                    "year_month": period,
                    "day_counts": {kind.value: count for kind, count in counts.items()},
                    "billing_basis": total.basis if total else None,
                    "clusters": {},
                    "members": [],
                    "error": {
                        "code": "CELL_METHOD_ERROR",
                        "message": str(error),
                        "action": "Review parameters and create a new run.",
                    },
                    "result": {
                        "status": "needs_review",
                        "sample": {},
                        "energy": {},
                        "contributions": {},
                        "sample_contributions": {},
                        "alpha": None,
                        "background_kwh": None,
                        "billing_kwh": total.energy_kwh if total else None,
                        "diagnostics": {},
                    },
                }
            )
            continue
        members = [
            {
                "customer_id": profile.customer.customer_id,
                "day_type": profile.day_type.value,
                "cluster_id": groups[profile.day_type].assignments[
                    profile.customer.customer_id
                ],
                "weight": profile.customer.weight,
                "days_used": profile.days_used,
                "estimated_fraction": profile.estimated_fraction,
                "unknown_fraction": profile.unknown_fraction,
            }
            for profile in profiles
        ]
        cells.append(
            {
                "industry_code": industry,
                "year_month": period,
                "day_counts": {kind.value: count for kind, count in counts.items()},
                "billing_basis": total.basis if total else None,
                "result": scaled.to_dict(),
                "clusters": {
                    kind.value: {
                        "diagnostics": group.diagnostics,
                        "centroids": group.centroids,
                        "assignments": group.assignments,
                    }
                    for kind, group in groups.items()
                },
                "members": members,
            }
        )
    for cell in cells:
        cell["industry_name"] = catalog.industry_names.get(cell["industry_code"], "")
    return cells, {
        "period": period,
        **quality,
        "excluded": excluded,
        "cmis_reconciliation": {
            "status": "available"
            if any(item["status"] == "comparable" for item in reconciliation.values())
            else "N/A",
            "customers": reconciliation,
            "reason": "Original MDMS compared only for complete calendar-month observations; never forced to match CMIS.",
        },
    }


def run_study(
    workspace: Workspace,
    request: StudyRequest,
    *,
    on_progress: Callable[[dict], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> dict:
    progress = on_progress or (lambda _event: None)
    run_id = workspace.create_run(
        request.config, request.all_paths(), {"request": request.to_dict()}
    )

    def check() -> None:
        if cancelled is not None and cancelled():
            raise ResearchCancelled("research cancelled")

    with workspace.writer():
        try:
            check()
            workspace.set_status(run_id, "running")
            progress({"stage": "started", "run_id": run_id})
            workspace.verify_sources(run_id)
            size = sum(path.stat().st_size for path in request.all_paths())
            if shutil.disk_usage(workspace.root).free < size * 3 + 256 * 1024**2:
                raise OSError(
                    "insufficient free space for source size, canonical data and temporary work"
                )
            calendar, catalog = _calendar(request), _catalog(request)
            workspace.save_artifact(run_id, "catalog.json", catalog.to_dict())
            billing_rows = itertools.chain.from_iterable(
                read_rows(
                    Path(path),
                    mapping=request.billing_mapping,
                    sheet=request.billing_sheet,
                    delimiter=request.table_delimiter,
                )
                for path in request.billing_paths
            )
            billing = load_billing(billing_rows, request.config.scope)
            database, imported = _prepare_cache(
                workspace, request, catalog, run_id, check, progress
            )
            cells, quality = [], []
            journal_path = workspace.safe_path(
                f"runs/{run_id}/artifacts/quality-events.jsonl"
            )
            with (
                journal_path.open("x", encoding="utf-8") as journal,
                IntervalStore(
                    database,
                    memory_limit_mb=request.config.memory_limit_mb,
                    threads=request.config.worker_threads,
                    read_only=True,
                ) as store,
            ):
                store.validate()
                for index, period in enumerate(request.config.periods):
                    check()
                    month_cells, month_quality = _analyse_month(
                        store,
                        catalog,
                        request,
                        calendar,
                        period,
                        billing,
                        check,
                        journal,
                        run_id,
                    )
                    cells.extend(month_cells)
                    quality.append(month_quality)
                    progress(
                        {
                            "stage": "analysis",
                            "completed": index + 1,
                            "total": len(request.config.periods),
                            "period": period,
                        }
                    )
            check()
            workspace.verify_sources(run_id)
            incomplete = not cells or any(
                cell["result"]["status"] not in ("valid", "valid_with_warnings")
                for cell in cells
            )
            warnings = imported["issues_count"] > 0 or any(
                item.get("unknown_source_quality", 0) for item in quality
            )
            warnings |= any(
                cell["result"]["status"] == "valid_with_warnings" for cell in cells
            )
            status = (
                "partial"
                if incomplete
                else "completed_with_warnings"
                if warnings
                else "completed"
            )
            result = {
                "schema_version": 1,
                "run_id": run_id,
                "status": status,
                "method_version": METHOD_VERSION,
                "config": request.config.to_dict(),
                "calendar": calendar.to_dict(),
                "request": request.to_dict(),
                "calendar_hash": calendar.content_hash,
                "import": imported,
                "quality": quality,
                "cells": cells,
                "sources": workspace.read_run(run_id)["sources"],
                "software": {
                    "python": platform.python_version(),
                    "platform": platform.system(),
                    "machine": platform.machine(),
                    "packages": runtime_versions(),
                },
                "quality_journal": {
                    "path": str(journal_path.relative_to(workspace.root)),
                    "sha256": file_hash(journal_path),
                },
            }
            workspace.save_artifact(run_id, "result.json", result)
            workspace.set_status(
                run_id,
                status,
                {"calendar_hash": calendar.content_hash, "cell_count": len(cells)},
            )
            progress({"stage": "finished", "run_id": run_id, "status": status})
            return result
        except ResearchCancelled:
            workspace.set_status(run_id, "cancelled")
            raise
        except Exception as error:
            workspace.set_status(
                run_id,
                "needs_review" if isinstance(error, ValueError) else "failed",
                {"error_type": type(error).__name__, "message": str(error)},
            )
            raise
