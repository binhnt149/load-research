"""Atomic portable project copies; original run snapshots stay immutable."""

import os
import shutil
import sqlite3
import tempfile
from collections.abc import Callable
from pathlib import Path

from load_research.workspace import Workspace, atomic_json, file_hash


def backup_project(
    workspace: Workspace,
    destination: Path,
    *,
    include_sources: bool,
    check: Callable[[], None] = lambda: None,
) -> Path:
    destination = Path(destination).resolve()
    if destination.is_relative_to(workspace.root) or workspace.root.is_relative_to(
        destination
    ):
        raise ValueError("backup must be outside the project directory")
    if destination.exists():
        raise FileExistsError("backup destination already exists")
    destination.parent.mkdir(parents=True, exist_ok=True)

    def copy_file(source, target):
        with Path(source).open("rb") as reader, Path(target).open("wb") as writer:
            while block := reader.read(1024 * 1024):
                check()
                writer.write(block)
        return str(target)

    with (
        workspace.writer(),
        tempfile.TemporaryDirectory(
            prefix=".load-research-backup-", dir=destination.parent
        ) as temporary,
    ):
        check()
        for path in workspace.root.rglob("*"):
            if path.is_symlink():
                raise ValueError("backup rejects project symlinks; use regular files")
        runs = workspace.list_runs()
        sources = {
            source["sha256"]: source for run in runs for source in run["sources"]
        }
        if include_sources:
            for run in runs:
                workspace.verify_sources(run["id"])
        required = sum(
            path.stat().st_size for path in workspace.root.rglob("*") if path.is_file()
        )
        if include_sources:
            required += sum(source["size"] for source in sources.values())
        if shutil.disk_usage(destination.parent).free < required + 64 * 1024**2:
            raise OSError("insufficient disk for backup")
        staging = Path(temporary)
        shutil.copytree(
            workspace.root,
            staging,
            dirs_exist_ok=True,
            copy_function=copy_file,
            ignore=lambda directory, names: [
                name
                for name in names
                if Path(directory) == workspace.root
                and name
                in (".writer.lock", "metadata.sqlite", "temp", "backup-manifest.json")
            ],
        )
        (staging / "temp").mkdir(exist_ok=True)
        with (
            workspace.connection() as source_db,
            sqlite3.connect(staging / "metadata.sqlite") as target_db,
        ):
            source_db.backup(target_db)
        relocated = {}
        if include_sources:
            for checksum, source in sources.items():
                check()
                relative = f"sources/{checksum}{Path(source['path']).suffix.lower()}"
                path = staging / relative
                path.parent.mkdir(exist_ok=True)
                if not path.exists():
                    copy_file(workspace.resolve_source(source), path)
                if file_hash(path) != checksum:
                    raise ValueError("source changed while creating backup")
                relocated[checksum] = relative
            atomic_json(staging / "source-locations.json", relocated, replace=True)
        files = [
            {
                "path": path.relative_to(staging).as_posix(),
                "sha256": file_hash(path),
                "bytes": path.stat().st_size,
            }
            for path in sorted(staging.rglob("*"))
            if path.is_file()
        ]
        atomic_json(
            staging / "backup-manifest.json",
            {
                "schema_version": 1,
                "project_id": workspace.project_id,
                "includes_sources": include_sources,
                "files": files,
            },
        )
        check()
        if destination.exists():
            raise FileExistsError("backup destination was created by another operation")
        os.rename(staging, destination)
    return destination
