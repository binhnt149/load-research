"""Small result controls with explicit selection and chart-point feedback."""

import numpy as np
from PySide6.QtCore import QPoint, Signal
from PySide6.QtWidgets import QComboBox, QMenu

from load_research.presentation import format_value


class MultiSelectCombo(QComboBox):
    selectionChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._selected: tuple = ()
        self.setEditable(True)
        editor = self.lineEdit()
        assert editor is not None
        editor.setReadOnly(True)
        self.setMinimumWidth(80)
        self.currentIndexChanged.connect(self._single)

    def _single(self) -> None:
        self._selected = (self.currentData(),) if self.currentIndex() >= 0 else ()

    def selected_data(self) -> tuple:
        available = {self.itemData(index) for index in range(self.count())}
        return tuple(value for value in self._selected if value in available)

    def set_selected(self, values: tuple) -> None:
        selected = tuple(dict.fromkeys(values))
        if not selected or any(self.findData(value) < 0 for value in selected):
            raise ValueError("select at least one available item")
        blocked = self.blockSignals(True)
        self.setCurrentIndex(self.findData(selected[0]))
        self._selected = selected
        labels = [self.itemText(self.findData(value)) for value in selected]
        editor = self.lineEdit()
        assert editor is not None
        editor.setText(labels[0] if len(labels) == 1 else f"{len(labels)} lựa chọn")
        self.setToolTip(", ".join(labels))
        self.blockSignals(blocked)
        if not blocked:
            self.selectionChanged.emit()

    def showPopup(self) -> None:
        menu = QMenu(self)
        all_action = menu.addAction("Chọn tất cả")
        all_action.triggered.connect(
            lambda: self.set_selected(
                tuple(self.itemData(i) for i in range(self.count()))
            )
        )
        menu.addSeparator()
        for index in range(self.count()):
            value = self.itemData(index)
            action = menu.addAction(self.itemText(index))
            action.setCheckable(True)
            action.setChecked(value in self.selected_data())
            action.triggered.connect(
                lambda checked, item=value: self._toggle(item, checked)
            )
        menu.exec(self.mapToGlobal(QPoint(0, self.height())))

    def _toggle(self, value, checked: bool) -> None:
        selected = tuple(item for item in self.selected_data() if item != value)
        if checked:
            selected += (value,)
        if selected:
            self.set_selected(selected)


def chart_point_text(event, canvas, *, minutes: int, unit: str) -> str | None:
    if event.inaxes is None or event.xdata is None or event.button != 1:
        return None
    index = max(0, min(1440 // minutes - 1, int(round(event.xdata * 60 / minutes))))
    values = []
    for line in event.inaxes.lines:
        y = line.get_ydata()
        if len(y) > index and np.isfinite(y[index]):
            values.append(
                f"{line.get_label()}: {format_value('value', float(y[index]))} {unit}"
            )
    start, end = index * minutes, (index + 1) * minutes
    return (
        f"Chu kỳ {index + 1} · {start // 60:02}:{start % 60:02}–{end // 60:02}:{end % 60:02} · "
        + " | ".join(values)
    )
