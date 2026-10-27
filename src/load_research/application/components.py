"""Versioned project component catalogs, separate from immutable study snapshots."""

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from load_research.components import parse_components
from load_research.importers.tables import read_rows
from load_research.workspace import Workspace


def _digest(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def import_components(
    workspace: Workspace,
    path: Path,
    *,
    sheet: str | None = None,
    delimiter: str = ",",
    check: Callable[[], None] = lambda: None,
) -> dict:
    check()

    def checked_rows():
        for row in read_rows(path, sheet=sheet, delimiter=delimiter):
            check()
            yield row

    rows = parse_components(checked_rows())
    payload = json.dumps(rows, ensure_ascii=False, sort_keys=True, allow_nan=False)
    check()
    with workspace.writer(), workspace.connection() as database:
        database.execute(
            "CREATE TABLE IF NOT EXISTS component_catalogs ("
            "revision INTEGER PRIMARY KEY AUTOINCREMENT, checksum TEXT NOT NULL, "
            "payload TEXT NOT NULL, source_name TEXT NOT NULL, created_at TEXT NOT NULL)"
        )
        check()
        cursor = database.execute(
            "INSERT INTO component_catalogs(checksum,payload,source_name,created_at) VALUES(?,?,?,?)",
            (_digest(payload), payload, path.name, datetime.now(UTC).isoformat()),
        )
        revision = cursor.lastrowid
    saved = load_components(workspace, revision)
    if saved is None:
        raise ValueError("Không đọc được danh mục vừa lưu.")
    return saved


def load_components(workspace: Workspace, revision: int | None = None) -> dict | None:
    with workspace.connection() as database:
        if not database.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='component_catalogs'"
        ).fetchone():
            if revision is not None:
                raise ValueError(
                    "Không tìm thấy phiên bản danh mục thành phần đã chọn."
                )
            return None
        row = (
            database.execute(
                "SELECT * FROM component_catalogs WHERE revision=?", (revision,)
            ).fetchone()
            if revision is not None
            else database.execute(
                "SELECT * FROM component_catalogs ORDER BY revision DESC LIMIT 1"
            ).fetchone()
        )
    if row is None:
        if revision is not None:
            raise ValueError("Không tìm thấy phiên bản danh mục thành phần đã chọn.")
        return None
    if _digest(row["payload"]) != row["checksum"]:
        raise ValueError("Danh mục thành phần thay đổi hoặc hỏng checksum.")
    return {
        "revision": row["revision"],
        "checksum": row["checksum"],
        "source_name": row["source_name"],
        "created_at": row["created_at"],
        "rows": parse_components(json.loads(row["payload"])),
    }
