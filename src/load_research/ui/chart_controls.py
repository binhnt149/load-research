"""Named series visibility; plotting changes never mutate the numerical view."""

from PySide6.QtWidgets import QMenu, QToolButton


class SeriesVisibility(QToolButton):
    def __init__(self, canvas, clear_point, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.clear_point = clear_point
        self.setText("Đường dữ liệu…")
        self.setObjectName("seriesVisibility")
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.setMenu(QMenu(self))

    def reset(self) -> None:
        menu = self.menu()
        menu.clear()
        artists = []
        if self.canvas.figure.axes:
            axes = self.canvas.figure.axes[0]
            artists = [*axes.lines, *axes.collections]
        for label, checked in (("Hiện tất cả", True), ("Ẩn tất cả", False)):
            menu.addAction(label).triggered.connect(
                lambda _value=False, show=checked: self.set_all(show)
            )
        menu.addSeparator()
        for artist in artists:
            if not artist.get_gid():
                continue
            action = menu.addAction(artist.get_label())
            action.setCheckable(True)
            action.setData(artist.get_gid())
            action.setChecked(artist.get_visible())
            action.toggled.connect(
                lambda checked, item=artist: self.set_series_visible(item, checked)
            )
        self.setEnabled(any(action.isCheckable() for action in menu.actions()))

    def set_all(self, visible: bool) -> None:
        for action in self.menu().actions():
            if action.isCheckable():
                action.setChecked(visible)

    def hidden_ids(self) -> list[str]:
        return [
            action.data()
            for action in self.menu().actions()
            if action.isCheckable() and not action.isChecked()
        ]

    def set_series_visible(self, artist, visible: bool) -> None:
        from load_research.result_reporting import autoscale_visible

        artist.set_visible(visible)
        axes = self.canvas.figure.axes[0]
        handles, labels = axes.get_legend_handles_labels()
        shown = [
            (a, label)
            for a, label in zip(handles, labels, strict=True)
            if a.get_visible()
        ]
        old = axes.get_legend()
        if old:
            old.remove()
        if shown:
            legend = axes.legend(
                [a for a, _ in shown[:8]],
                [" ".join(label.split())[:70] for _, label in shown[:8]],
                loc="upper right",
                fontsize=7,
                ncols=2,
            )
            for text in legend.get_texts():
                text.set_parse_math(False)
        autoscale_visible(axes)
        self.clear_point()
        self.canvas.draw_idle()
