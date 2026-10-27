"""Shared light desktop theme with native typography and explicit contrast states."""

from PySide6.QtGui import QColor, QFontDatabase, QPalette
from PySide6.QtWidgets import QWidget

BACKGROUND = "#F2F5FA"
SURFACE = "#FFFFFF"
TEXT = "#1B2E45"
MUTED = "#516278"
BORDER = "#C8D4E3"
ACCENT = "#155CA2"
ACCENT_HOVER = "#104B85"
SELECTION = "#DCEBFA"
STRIPE = "#F6F8FC"
DISABLED = "#E9EEF4"
DANGER = "#B42318"

STYLESHEET = f"""
QMainWindow, QDialog {{ background: {BACKGROUND}; }}
QWidget#researchForm, QWidget#configForm {{ background: {BACKGROUND}; }}
QWidget {{ color: {TEXT}; font-size: 14px; }}
QLabel#heading {{ font-size: 28px; font-weight: 700; }}
QLabel#sectionTitle {{ font-size: 17px; font-weight: 600; }}
QLabel#hint {{ color: {MUTED}; font-size: 13px; }}
QLabel[tone="danger"] {{ color: {DANGER}; }}
QPushButton {{ background: {SURFACE}; border: 1px solid {BORDER};
    border-radius: 6px; padding: 8px 12px; min-height: 18px; }}
QPushButton:hover {{ background: {STRIPE}; border-color: {ACCENT}; }}
QPushButton:pressed {{ background: {SELECTION}; }}
QPushButton:focus, QToolButton:focus {{ border: 2px solid {ACCENT}; }}
QPushButton:disabled {{ background: {DISABLED}; color: {MUTED}; border-color: {BORDER}; }}
QPushButton#primary {{ background: {ACCENT}; color: {SURFACE};
    border-color: {ACCENT}; font-weight: 600; }}
QPushButton#primary:hover, QPushButton#primary:focus {{ background: {ACCENT_HOVER}; }}
QPushButton#primary:disabled {{ background: {DISABLED}; color: {MUTED}; border-color: {BORDER}; }}
QToolButton {{ border: 1px solid transparent; border-radius: 4px;
    padding: 8px; color: {ACCENT}; text-align: left; }}
QToolButton:hover {{ background: {SELECTION}; }}
QLineEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QComboBox {{ background: {SURFACE};
    color: {TEXT}; border: 1px solid {BORDER}; border-radius: 5px;
    padding: 7px 8px; min-height: 18px; selection-background-color: {SELECTION};
    selection-color: {TEXT}; }}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QComboBox:focus {{ border-color: {ACCENT}; }}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QDateEdit:disabled,
QComboBox:disabled {{ color: {MUTED}; background: {DISABLED}; }}
QComboBox QAbstractItemView {{ background: {SURFACE}; color: {TEXT};
    selection-background-color: {SELECTION}; selection-color: {TEXT}; }}
QGroupBox {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 8px;
    font-weight: 600; margin-top: 12px; padding: 12px 8px 8px; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 4px; }}
QScrollArea {{ border: 0; background: transparent; }}
QTabWidget::pane {{ border: 1px solid {BORDER}; background: {SURFACE}; }}
QTabBar::tab {{ background: {BACKGROUND}; color: {MUTED};
    padding: 12px 18px; border-bottom: 2px solid transparent; }}
QTabBar::tab:selected {{ color: {ACCENT}; background: {SURFACE};
    border-bottom-color: {ACCENT}; font-weight: 600; }}
QTabBar::tab:hover {{ background: {SELECTION}; }}
QTableView, QListWidget, QPlainTextEdit {{ background: {SURFACE}; color: {TEXT};
    alternate-background-color: {STRIPE}; border: 1px solid {BORDER};
    border-radius: 4px; selection-background-color: {SELECTION}; selection-color: {TEXT}; }}
QListWidget::item {{ padding: 5px 8px; }}
QListWidget::item:selected, QTableView::item:selected {{ background: {SELECTION}; color: {TEXT}; }}
QHeaderView::section {{ background: {STRIPE}; color: {TEXT};
    padding: 8px; border: 0; border-bottom: 1px solid {BORDER}; font-weight: 600; }}
QTableView {{ gridline-color: {BORDER}; }}
QTableCornerButton::section {{ background: {STRIPE}; border: 0; }}
QCheckBox {{ spacing: 8px; padding: 4px 0; }}
QSplitter::handle:vertical {{ background: {BORDER}; height: 6px; margin: 2px 24px; }}
QProgressBar {{ background: {DISABLED}; color: {TEXT}; border: 1px solid {BORDER};
    border-radius: 5px; text-align: center; min-height: 20px; }}
QProgressBar::chunk {{ background: {SELECTION}; border: 1px solid {ACCENT}; border-radius: 4px; }}
QScrollBar:vertical {{ background: {BACKGROUND}; width: 12px; margin: 0; }}
QScrollBar:horizontal {{ background: {BACKGROUND}; height: 12px; margin: 0; }}
QScrollBar::handle {{ background: #9EADC0; border-radius: 5px; min-height: 28px; min-width: 28px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QToolTip {{ background: {TEXT}; color: {SURFACE}; padding: 6px; border: 0; }}
"""


def apply_theme(widget: QWidget) -> None:
    font = QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont)
    font.setPointSizeF(11)
    widget.setFont(font)
    palette = QPalette()
    for role, value in (
        (QPalette.ColorRole.Window, BACKGROUND),
        (QPalette.ColorRole.WindowText, TEXT),
        (QPalette.ColorRole.Base, SURFACE),
        (QPalette.ColorRole.AlternateBase, STRIPE),
        (QPalette.ColorRole.Text, TEXT),
        (QPalette.ColorRole.Button, SURFACE),
        (QPalette.ColorRole.ButtonText, TEXT),
        (QPalette.ColorRole.Highlight, SELECTION),
        (QPalette.ColorRole.HighlightedText, TEXT),
        (QPalette.ColorRole.PlaceholderText, MUTED),
        (QPalette.ColorRole.ToolTipBase, TEXT),
        (QPalette.ColorRole.ToolTipText, SURFACE),
    ):
        palette.setColor(role, QColor(value))
    for role in (
        QPalette.ColorRole.Text,
        QPalette.ColorRole.ButtonText,
        QPalette.ColorRole.WindowText,
    ):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(MUTED))
    widget.setPalette(palette)
    widget.setStyleSheet(STYLESHEET)
