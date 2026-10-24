"""Local project snapshots, single writer ownership and immutable artifacts."""

import hashlib
import json
import os
import re
import sqlite3
import tempfile
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path, PureWindowsPath

from load_research import METHOD_VERSION, __version__
from load_research.domain.config import RunConfig

TERMINAL_STATUSES = {
    "completed",
    "completed_with_warnings",
    "partial",
    "failed",
    "cancelled",
}
STATUSES = TERMINAL_STATUSES | {"draft", "running", "needs_review"}


class WorkspaceBusy(RuntimeError):
    """A project already has an active writer."""


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, payload: object, *, replace: bool = False) -> None:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, allow_nan=False
    ).encode()
    descriptor, temporary = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        if replace:
            os.replace(temporary_path, path)
        else:
            os.link(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


class Workspace:
    def __init__(self, root: Path, project_id: str) -> None:
        self.root = root.resolve()
        self.project_id = project_id
        self._writing = False

    @classmethod
    def create(cls, root: Path) -> "Workspace":
        root = Path(root).resolve()
        if root.exists() and any(root.iterdir()):
            raise FileExistsError("project directory must be empty")
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        project_id = uuid.uuid4().hex
        atomic_json(
            root / "project.json", {"schema_version": 1, "project_id": project_id}
        )
        for name in (
            "sources",
            "canonical",
            "quality",
            "cache",
            "runs",
            "exports",
            "temp",
        ):
            (root / name).mkdir()
        workspace = cls(root, project_id)
        with workspace.connection() as database:
            database.executescript("""
                CREATE TABLE runs (
                    id TEXT PRIMARY KEY, config TEXT NOT NULL, sources TEXT NOT NULL,
                    status TEXT NOT NULL, created_at TEXT NOT NULL, details TEXT NOT NULL
                );
                CREATE TABLE artifacts (
                    run_id TEXT NOT NULL, name TEXT NOT NULL, checksum TEXT NOT NULL,
                    PRIMARY KEY (run_id, name), FOREIGN KEY(run_id) REFERENCES runs(id)
                );
            """)
        return workspace

    @classmethod
    def open(cls, root: Path) -> "Workspace":
        root = Path(root).resolve()
        marker = json.loads((root / "project.json").read_text(encoding="utf-8"))
        if marker.get("schema_version") != 1 or not re.fullmatch(
            r"[0-9a-f]{32}", marker.get("project_id", "")
        ):
            raise ValueError("unsupported or invalid project schema")
        workspace = cls(root, marker["project_id"])
        workspace.safe_path("metadata.sqlite")
        return workspace

    def safe_path(self, relative: str) -> Path:
        candidate = (self.root / relative).resolve()
        if candidate == self.root or not candidate.is_relative_to(self.root):
            raise ValueError("path escapes project")
        return candidate

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        database = sqlite3.connect(self.safe_path("metadata.sqlite"), timeout=10)
        database.row_factory = sqlite3.Row
        database.execute("PRAGMA foreign_keys = ON")
        try:
            with database:
                yield database
        finally:
            database.close()

    @contextmanager
    def writer(self) -> Iterator[None]:
        if self._writing:
            yield
            return
        lock = self.safe_path(".writer.lock")
        owner = f"{self.project_id}:{os.getpid()}:{uuid.uuid4().hex}"
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as error:
            raise WorkspaceBusy(
                "project already has a writer; open read-only or verify a stale lock"
            ) from error
        try:
            with os.fdopen(descriptor, "w") as stream:
                stream.write(owner)
            self._writing = True
            yield
        finally:
            self._writing = False
            if lock.exists() and lock.read_text() == owner:
                lock.unlink()

    def create_run(
        self, config: RunConfig, sources: list[Path], extra: dict | None = None
    ) -> str:
        manifest = [
            {
                "path": str(Path(p).resolve()),
                "sha256": file_hash(Path(p)),
                "size": Path(p).stat().st_size,
            }
            for p in sources
        ]
        run_id = uuid.uuid4().hex
        details = {
            "method_version": METHOD_VERSION,
            "app_version": __version__,
            "worker_pid": os.getpid(),
            **(extra or {}),
        }
        with self.writer():
            directory = self.safe_path(f"runs/{run_id}")
            directory.mkdir()
            (directory / "artifacts").mkdir()
            atomic_json(directory / "config.json", config.to_dict())
            atomic_json(directory / "input-manifest.json", manifest)
            with self.connection() as database:
                database.execute(
                    "INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        run_id,
                        json.dumps(config.to_dict()),
                        json.dumps(manifest),
                        "draft",
                        datetime.now(UTC).isoformat(),
                        json.dumps(details),
                    ),
                )
        return run_id

    def read_run(self, run_id: str) -> dict:
        if not re.fullmatch(r"[0-9a-f]{32}", run_id):
            raise ValueError("invalid run id")
        with self.connection() as database:
            row = database.execute(
                "SELECT * FROM runs WHERE id = ?", (run_id,)
            ).fetchone()
        if row is None:
            raise ValueError("unknown run")
        result = dict(row)
        for key in ("config", "sources", "details"):
            result[key] = json.loads(result[key])
        return result

    def list_runs(self) -> list[dict]:
        with self.connection() as database:
            identifiers = database.execute(
                "SELECT id FROM runs ORDER BY created_at DESC"
            ).fetchall()
        return [self.read_run(row["id"]) for row in identifiers]

    def set_status(self, run_id: str, status: str, details: dict | None = None) -> None:
        if status not in STATUSES:
            raise ValueError("invalid run status")
        with self.writer():
            current = self.read_run(run_id)
            if current["status"] in TERMINAL_STATUSES:
                raise ValueError("completed run is immutable")
            merged = {**current["details"], **(details or {})}
            encoded = json.dumps(merged, allow_nan=False)
            with self.connection() as database:
                database.execute(
                    "UPDATE runs SET status = ?, details = ? WHERE id = ?",
                    (status, encoded, run_id),
                )

    def verify_sources(self, run_id: str) -> None:
        for source in self.read_run(run_id)["sources"]:
            path = self.resolve_source(source)
            if not path.is_file() or file_hash(path) != source["sha256"]:
                raise ValueError("source is missing or changed")

    def resolve_source(self, source: dict) -> Path:
        locations = self.safe_path("source-locations.json")
        if locations.is_file():
            relative = json.loads(locations.read_text()).get(source["sha256"])
            if relative:
                return self.safe_path(relative)
        return Path(source["path"])

    def request_for_run(self, run_id: str):
        from load_research.application.models import StudyRequest

        run = self.read_run(run_id)
        payload = json.loads(json.dumps(run["details"]["request"]))
        mapping = {
            source["path"]: str(self.resolve_source(source))
            for source in run["sources"]
        }

        def portable_key(path: str) -> str:
            if len(path) > 1 and path[1] == ":" or path.startswith(("\\\\", "//")):
                return PureWindowsPath(path).as_posix().casefold()
            return path

        aliases: dict[str, str | None] = {}
        for original, destination in mapping.items():
            key = portable_key(original)
            aliases[key] = (
                destination
                if key not in aliases or aliases[key] == destination
                else None
            )

        def relocated(path: str) -> str:
            # Saved Windows paths must be matched before interpreting them on
            # macOS (and vice versa). Original snapshots remain unchanged.
            if path in mapping:
                return mapping[path]
            key = portable_key(path)
            if key in aliases:
                if aliases[key] is None:
                    raise ValueError(
                        "ambiguous saved source path; relocate by checksum"
                    )
                return str(aliases[key])
            return mapping.get(str(Path(path).resolve()), path)

        for key in ("cmis_paths", "billing_paths", "calendar_paths"):
            payload[key] = [relocated(path) for path in payload.get(key, [])]
        for source in payload["mdms_sources"]:
            source["path"] = relocated(source["path"])
        return StudyRequest.from_dict(payload)

    def save_artifact(self, run_id: str, name: str, payload: object) -> Path:
        self.read_run(run_id)
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", name) or name in (".", ".."):
            raise ValueError("invalid artifact name")
        path = self.safe_path(f"runs/{run_id}/artifacts/{name}")
        with self.writer():
            if self.read_run(run_id)["status"] in TERMINAL_STATUSES | {"needs_review"}:
                raise ValueError("completed run is immutable")
            atomic_json(path, payload)
            with self.connection() as database:
                database.execute(
                    "INSERT INTO artifacts VALUES (?, ?, ?)",
                    (run_id, name, file_hash(path)),
                )
        return path

    def load_artifact(self, run_id: str, name: str) -> dict:
        self.read_run(run_id)
        path = self.safe_path(f"runs/{run_id}/artifacts/{name}")
        with self.connection() as database:
            record = database.execute(
                "SELECT checksum FROM artifacts WHERE run_id = ? AND name = ?",
                (run_id, name),
            ).fetchone()
        if (
            record is None
            or not path.is_file()
            or file_hash(path) != record["checksum"]
        ):
            raise ValueError("artifact is missing or changed")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("artifact must contain a JSON object")
        return payload

    def add_cluster_label(
        self,
        run_id: str,
        industry: str,
        period: str,
        day_type: str,
        cluster_id: str,
        label: str,
        reason: str,
    ) -> None:
        if (
            not label.strip()
            or len(label) > 100
            or not reason.strip()
            or len(reason) > 1000
        ):
            raise ValueError(
                "cluster label and reason are required and must have bounded lengths"
            )
        result = self.load_artifact(run_id, "result.json")
        cells = [
            cell
            for cell in result["cells"]
            if cell["industry_code"] == industry and cell["year_month"] == period
        ]
        if len(cells) != 1 or cluster_id not in set(
            cells[0]["clusters"].get(day_type, {}).get("assignments", {}).values()
        ):
            raise ValueError("cluster does not exist in the referenced run")
        with self.writer(), self.connection() as database:
            database.execute("""CREATE TABLE IF NOT EXISTS cluster_labels (
                id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, industry_code TEXT,
                year_month TEXT, day_type TEXT, cluster_id TEXT, label TEXT, reason TEXT, created_at TEXT
            )""")
            database.execute(
                "INSERT INTO cluster_labels (run_id, industry_code, year_month, day_type, cluster_id, label, reason, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    run_id,
                    industry,
                    period,
                    day_type,
                    cluster_id,
                    label.strip(),
                    reason.strip(),
                    datetime.now(UTC).isoformat(),
                ),
            )

    def list_cluster_labels(self, run_id: str) -> list[dict]:
        self.read_run(run_id)
        with self.connection() as database:
            if (
                database.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='cluster_labels'"
                ).fetchone()
                is None
            ):
                return []
            return [
                dict(row)
                for row in database.execute(
                    "SELECT * FROM cluster_labels WHERE run_id = ? ORDER BY id",
                    (run_id,),
                ).fetchall()
            ]
