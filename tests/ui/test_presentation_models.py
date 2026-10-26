from PySide6.QtCore import Qt

from load_research.ui.models import RecordsModel
from load_research.ui.template_dialog import TemplateDialog


def test_result_model_localizes_display_without_changing_records(qtbot):
    model = RecordsModel()
    records = [{"day_type": "saturday", "estimated_fraction": 0.1}]
    model.set_records(records)
    assert model.headerData(0, Qt.Orientation.Horizontal) == "Loại ngày"
    assert model.data(model.index(0, 0)) == "Thứ Bảy"
    assert model.data(model.index(0, 1)) == "10%"
    assert model.records == records


def test_source_preview_model_preserves_source_headers_and_strings(qtbot):
    model = RecordsModel(localized=False)
    model.set_records([{"day_type": "saturday"}])
    assert model.headerData(0, Qt.Orientation.Horizontal) == "day_type"
    assert model.data(model.index(0, 0)) == "saturday"


def test_template_examples_show_the_actual_import_column_names(qtbot):
    dialog = TemplateDialog(category="cmis")
    qtbot.addWidget(dialog)
    assert (
        dialog.example_model.headerData(0, Qt.Orientation.Horizontal) == "customer_id"
    )
