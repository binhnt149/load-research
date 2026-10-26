"""Source coordinates accompany validation failures without changing raw messages."""

from collections.abc import Iterator
from contextlib import contextmanager


class InputDataError(ValueError):
    def __init__(self, message: str, source_context: dict) -> None:
        super().__init__(message)
        self.source_context = source_context


@contextmanager
def source_row(row: dict) -> Iterator[None]:
    try:
        yield
    except InputDataError:
        raise
    except (ValueError, TypeError, KeyError, OverflowError) as error:
        if "_source_path" not in row:
            raise
        raise InputDataError(
            str(error),
            {
                "path": row.get("_source_path"),
                "row": row.get("_source_row"),
                "sheet": row.get("_source_sheet"),
            },
        ) from error
