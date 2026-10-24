"""Process-owned writable caches shared with the application's child workers."""

import os
import tempfile
from pathlib import Path

_cache: tempfile.TemporaryDirectory | None = None


def prepare_runtime_cache() -> None:
    global _cache
    if "MPLCONFIGDIR" not in os.environ:
        if _cache is None:
            _cache = tempfile.TemporaryDirectory(prefix="load-research-runtime-")
        os.environ["MPLCONFIGDIR"] = str(Path(_cache.name) / "matplotlib")
