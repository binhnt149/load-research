"""Read-only Qt table models; no per-cell QWidget allocation."""

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from load_research.presentation import field_label, format_value

EMPTY_INDEX = QModelIndex()


class RecordsModel(QAbstractTableModel):
    def __init__(self, parent=None, *, localized: bool = True) -> None:
        super().__init__(parent)
        self.localized = localized
        self.records: list[dict] = []
        self.columns: list[str] = []

    def set_records(
        self, records: list[dict], columns: list[str] | None = None
    ) -> None:
        self.beginResetModel()
        self.records = records
        self.columns = columns or list(
            dict.fromkeys(key for row in records for key in row)
        )
        self.endResetModel()

    def rowCount(self, parent=EMPTY_INDEX) -> int:
        return 0 if parent.isValid() else len(self.records)

    def columnCount(self, parent=EMPTY_INDEX) -> int:
        return 0 if parent.isValid() else len(self.columns)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self.records):
            return None
        value = self.records[index.row()].get(self.columns[index.column()])
        if role == Qt.ItemDataRole.DisplayRole:
            if self.localized:
                return format_value(self.columns[index.column()], value)
            if value is None:
                return "N/A"
            return f"{value:,.6g}" if isinstance(value, float) else str(value)
        if role == Qt.ItemDataRole.TextAlignmentRole and isinstance(
            value, (int, float)
        ):
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        return (
            (
                field_label(self.columns[section])
                if self.localized
                else self.columns[section]
            )
            if orientation == Qt.Orientation.Horizontal
            else section + 1
        )

    def sort(self, column, order=Qt.SortOrder.AscendingOrder) -> None:
        if not 0 <= column < len(self.columns):
            return
        key = self.columns[column]
        self.layoutAboutToBeChanged.emit()
        self.records.sort(
            key=lambda row: (
                row.get(key) is None,
                0 if isinstance(row.get(key), (int, float)) else 1,
                row[key]
                if isinstance(row.get(key), (int, float))
                else str(row.get(key, "")),
            ),
            reverse=order == Qt.SortOrder.DescendingOrder,
        )
        self.layoutChanged.emit()
