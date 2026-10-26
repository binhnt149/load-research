"""Spawned research workers with small progress events and cooperative cancel."""

import multiprocessing as mp
import os
import queue
import time
from multiprocessing.process import BaseProcess
from pathlib import Path

from load_research.application.models import StudyRequest
from load_research.application.pipeline import ResearchCancelled, run_study
from load_research.backup import backup_project
from load_research.exports import apply_annotations, export_study
from load_research.workspace import Workspace, file_hash


def _worker(root: str, payload: dict, events, cancellation) -> None:
    def progress(event: dict) -> None:
        try:
            events.put(event, timeout=0.2)
        except queue.Full:
            pass  # intermediate progress may be dropped; authoritative state is persisted

    try:
        request = StudyRequest.from_dict(payload)
        os.environ["LOKY_MAX_CPU_COUNT"] = str(request.config.worker_threads)
        run_study(
            Workspace.open(Path(root)),
            request,
            on_progress=progress,
            cancelled=cancellation.is_set,
        )
    except ResearchCancelled:
        progress({"stage": "cancelled"})
    except Exception as error:
        progress(
            {
                "stage": "error",
                "error_type": type(error).__name__,
                "source_context": getattr(error, "source_context", {}),
                "message": str(error),
            }
        )


def _export_worker(
    root: str, run_id: str, destination: str, options: dict, events, cancellation
) -> None:
    try:
        workspace = Workspace.open(Path(root))
        result = apply_annotations(
            workspace.load_artifact(run_id, "result.json"),
            workspace.list_cluster_labels(run_id),
        )
        export_study(
            result, Path(destination), cancelled=cancellation.is_set, **options
        )
        events.put({"stage": "exported", "destination": destination})
    except ResearchCancelled:
        events.put({"stage": "cancelled"})
    except Exception as error:
        events.put(
            {
                "stage": "error",
                "error_type": type(error).__name__,
                "source_context": getattr(error, "source_context", {}),
                "message": str(error),
            }
        )


def _auxiliary_worker(
    root: str, action: str, payload: dict, events, cancellation
) -> None:
    def check() -> None:
        if cancellation.is_set():
            raise ResearchCancelled("task cancelled")

    try:
        workspace = Workspace.open(Path(root))
        if action == "verify":
            sources = {
                (source["path"], source["sha256"]): source
                for run in workspace.list_runs()
                for source in run["sources"]
            }
            changed = 0
            for source in sources.values():
                check()
                path = workspace.resolve_source(source)
                changed += not path.is_file() or file_hash(path) != source["sha256"]
            events.put(
                {
                    "stage": "sources_verified",
                    "source_count": len(sources),
                    "changed_count": changed,
                }
            )
        elif action == "backup":
            backup_project(
                workspace,
                Path(payload["destination"]),
                include_sources=payload["include_sources"],
                check=check,
            )
            events.put({"stage": "backed_up", "destination": payload["destination"]})
        elif action == "inspect":
            from datetime import date

            from load_research.application.inspection import inspect_day

            check()
            details = inspect_day(
                workspace,
                payload["run_id"],
                payload["customer_id"],
                date.fromisoformat(payload["date"]),
            )
            check()
            events.put({"stage": "inspected", "details": details})
    except ResearchCancelled:
        events.put({"stage": "cancelled"})
    except Exception as error:
        events.put(
            {
                "stage": "error",
                "error_type": type(error).__name__,
                "source_context": getattr(error, "source_context", {}),
                "message": str(error),
            }
        )


class ResearchJob:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.context = mp.get_context("spawn")
        self.events = self.context.Queue(maxsize=256)
        self.cancellation = self.context.Event()
        self.process: BaseProcess | None = None
        self.run_id: str | None = None
        self._backlog: list[dict] = []
        self._closed = False

    @property
    def is_running(self) -> bool:
        return self.process is not None and self.process.is_alive()

    def start(self, request: StudyRequest) -> None:
        if self.process is not None:
            raise RuntimeError("create a new job instance for each run")
        self.process = self.context.Process(
            target=_worker,
            args=(str(self.root), request.to_dict(), self.events, self.cancellation),
        )
        self.process.start()

    def start_export(self, run_id: str, destination: Path, options: dict) -> None:
        if self.process is not None:
            raise RuntimeError("create a new job instance for each export")
        self.process = self.context.Process(
            target=_export_worker,
            args=(
                str(self.root),
                run_id,
                str(destination),
                options,
                self.events,
                self.cancellation,
            ),
        )
        self.process.start()

    def start_auxiliary(self, action: str, payload: dict) -> None:
        if self.process is not None or action not in ("verify", "backup", "inspect"):
            raise RuntimeError("invalid auxiliary task or reused job")
        self.process = self.context.Process(
            target=_auxiliary_worker,
            args=(str(self.root), action, payload, self.events, self.cancellation),
        )
        self.process.start()

    def start_verification(self) -> None:
        self.start_auxiliary("verify", {})

    def _drain(self) -> list[dict]:
        result = []
        while True:
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            if event.get("run_id"):
                self.run_id = event["run_id"]
            result.append(event)
        return result

    def poll(self) -> list[dict]:
        result, self._backlog = self._backlog, []
        return result if self._closed else result + self._drain()

    def cancel(self) -> None:
        self.cancellation.set()

    def join(self, timeout: float = 30) -> None:
        if self.process is None or self._closed:
            return
        deadline = time.monotonic() + timeout
        while self.is_running and time.monotonic() < deadline:
            self._backlog.extend(self._drain())
            self.process.join(min(0.05, max(0, deadline - time.monotonic())))
        self._backlog.extend(self._drain())

    def close(self) -> None:
        if self._closed:
            return
        if self.process is None:
            self.events.close()
            self.events.join_thread()
            self._closed = True
            return
        if self.is_running:
            self.cancel()
            self.join(30)
        forced = self.is_running
        if forced:
            self.process.terminate()
            self.process.join(5)
        if self.process.exitcode is not None:
            workspace = Workspace.open(self.root)
            lock = workspace.safe_path(".writer.lock")
            if lock.is_file() and lock.read_text().startswith(
                f"{workspace.project_id}:{self.process.pid}:"
            ):
                lock.unlink()
                for run in workspace.list_runs():
                    if run["status"] in ("draft", "running") and (
                        run["id"] == self.run_id
                        or run["details"].get("worker_pid") == self.process.pid
                    ):
                        workspace.set_status(
                            run["id"],
                            "cancelled" if self.cancellation.is_set() else "failed",
                            {
                                "forced_worker_stop": forced,
                                "worker_exit_code": self.process.exitcode,
                            },
                        )
        self.events.close()
        self.events.join_thread()
        self._closed = True
