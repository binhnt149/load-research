import copy

from test_results import result_data

from load_research.ui.results import ResultsView


def test_component_catalog_selects_members_and_blocks_missing_industry(qtbot):
    result = result_data()
    second = copy.deepcopy(result["cells"][0])
    second["industry_code"] = "02"
    result["cells"].append(second)
    view = ResultsView()
    qtbot.addWidget(view)
    view.set_result(result)
    catalog = {
        "revision": 1,
        "checksum": "test",
        "rows": [
            {
                "industry_code": c,
                "industry_name": "Ngành " + c,
                "component_code": "CN",
                "component_name": "Công nghiệp",
            }
            for c in ("01", "02", "03")
        ],
    }
    view.set_component_catalog(catalog)
    view.component_selector.setCurrentIndex(view.component_selector.findData("CN"))
    assert view.industry.selected_data() == ("01", "02", "03")
    assert view.selection().name == "Công nghiệp"
    assert view.selection().component_code == "CN"
    assert not view.current_view["complete"]
    assert view.export_options(selected=True)["component_catalog_revision"] == 1
    view.show()
    assert not view.group.isVisible()


def test_component_with_no_measured_industry_never_keeps_previous_total(qtbot):
    view = ResultsView()
    qtbot.addWidget(view)
    view.set_result(result_data())
    view.set_component_catalog(
        {
            "revision": 1,
            "checksum": "h",
            "rows": [
                {
                    "industry_code": "99",
                    "industry_name": "Chưa có mẫu",
                    "component_code": "DV",
                    "component_name": "Dịch vụ",
                }
            ],
        }
    )
    view.component_selector.setCurrentIndex(view.component_selector.findData("DV"))
    assert view.current_view["industry_codes"] == ["99"]
    assert not view.current_view["complete"]
    assert all(row["Chung"] is None for row in view.table_model.records)


def test_group_rename_still_works_without_a_visible_group_combo(qtbot, monkeypatch):
    view = ResultsView()
    qtbot.addWidget(view)
    view.set_result(result_data())
    monkeypatch.setattr(
        "load_research.ui.results.QInputDialog.getItem",
        lambda parent, title, label, items, **kwargs: (items[0], True),
    )
    values = iter(["Ca sản xuất", "Hồ sơ đối chiếu"])
    monkeypatch.setattr(
        "load_research.ui.results.QInputDialog.getText",
        lambda *args, **kwargs: (next(values), True),
    )
    events = []
    view.rename_requested.connect(events.append)
    view.rename_dialog()
    assert events[0]["cluster_id"] == "group_1"
    assert events[0]["label"] == "Ca sản xuất"


def test_catalog_names_survive_reloading_a_run_and_missing_industry_cannot_be_renamed(
    qtbot,
):
    view = ResultsView()
    qtbot.addWidget(view)
    result = result_data()
    view.set_result(result)
    catalog = {
        "revision": 1,
        "checksum": "h",
        "rows": [
            {
                "industry_code": "01",
                "industry_name": "Cơ khí",
                "component_code": "CN",
                "component_name": "Công nghiệp",
            },
            {
                "industry_code": "99",
                "industry_name": "Chưa có mẫu",
                "component_code": "DV",
                "component_name": "Dịch vụ",
            },
        ],
    }
    view.set_component_catalog(catalog)
    view.set_result(result)
    assert "Cơ khí" in view.industry.itemText(view.industry.findData("01"))
    view.set_component_catalog(catalog)
    view.component_selector.setCurrentIndex(view.component_selector.findData("DV"))
    assert not view.rename_button.isEnabled()
