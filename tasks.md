# Tasks — Load Research

Spec: `load-research.md`. Kế hoạch: `tasks/plan.md`. `[x]` chỉ có nghĩa task đã được thực hiện và kiểm chứng; không đồng nghĩa mọi điều kiện phát hành ngoài môi trường đều đạt.

## Nền tảng và tính toán

- [x] **T01 — Môi trường và package.** Phụ thuộc: không. Nghiệm thu: Python 3.12 venv, package cài được, pytest/lint hoạt động, dependency lock. Verify: smoke import + `pytest tests/unit/test_package.py`. Files: `pyproject.toml`, package init, test, lock/config.
- [x] **T02 — Đại lượng và chuyển chu kỳ.** Phụ thuộc: T01. Nghiệm thu: kWh/kW đúng, không tăng độ phân giải, giữ năng lượng. Verify: `pytest tests/unit/test_energy.py`. Files: `domain/energy.py`, test.
- [x] **T03 — Lịch nghiên cứu.** Phụ thuộc: T01. Nghiệm thu: ưu tiên override/lễ/cuối tuần; năm nhuận; đếm N đúng. Verify: `pytest tests/unit/test_calendar.py`. Files: `calendar.py`, test.
- [x] **T04 — Cấu hình có kiểm tra.** Phụ thuộc: T02/T03. Nghiệm thu: tham số đầy đủ, miền hợp lệ, JSON roundtrip/hash ổn định. Verify: `pytest tests/unit/test_config.py`. Files: `domain/config.py`, test.
- [x] **T05 — Workspace và run bất biến.** Phụ thuộc: T04. Nghiệm thu: tạo/mở, snapshot/checksum, khoá ghi, artifact atomic, từ chối path traversal. Verify: `pytest tests/unit/test_workspace.py`. Files: `workspace.py`, test.
- [x] **T06 — Đọc bảng theo batch.** Phụ thuộc: T01. Nghiệm thu: CSV/XLSX/Parquet, giữ mã chuỗi, ánh xạ/sheet, từ chối công thức không có giá trị và tệp lỗi. Verify: `pytest tests/unit/test_tables.py`. Files: `importers/tables.py`, test.
- [x] **T07 — Danh mục mẫu và thương phẩm.** Phụ thuộc: T04/T06. Nghiệm thu: khoá/phạm vi/hiệu lực, trọng số, bảng A không trùng, đơn vị và kỳ rõ. Verify: `pytest tests/unit/test_catalog.py`. Files: `importers/catalog.py`, test.
- [x] **T08 — Chuẩn hoá MDMS.** Phụ thuộc: T02/T06/T07. Nghiệm thu: dạng dài/rộng, dấu cuối chu kỳ, hệ số một lần, kênh, duplicate conflict và công tơ ghép đúng. Verify: `pytest tests/unit/test_metering.py`. Files: `importers/metering.py`, test.
- [x] **T09 — Lưu chu kỳ lớn trên đĩa.** Phụ thuộc: T08. Nghiệm thu: append batch giao dịch, query theo tháng, tổng hợp công tơ không đếm đôi, không nạp toàn nguồn vào RAM. Verify: `pytest tests/integration/test_store.py`. Files: `infrastructure/store.py`, test.
- [x] **T10 — VEE trong ngày.** Phụ thuộc: T02/T04. Nghiệm thu: giữ 0/đỉnh thật; nội suy có hai đầu đúng giới hạn; nhật ký bù và điều kiện ngày. Verify: `pytest tests/unit/test_quality.py`. Files: `quality.py`, test.
- [x] **T11 — Bù ngày tương đồng.** Phụ thuộc: T10. Nghiệm thu: >=3 ngày gốc cùng tháng/loại; giới hạn tỷ lệ/hệ số; không bù cả ngày hoặc dùng bù làm nguồn. Verify: `pytest tests/unit/test_like_days.py`. Files: `quality.py`, test.
- [x] **T12 — Tập chung và đường cong khách hàng.** Phụ thuộc: T03/T09/T11. Nghiệm thu: điều kiện 80%/số ngày; cùng cohort giữa loại ngày; trung bình từng khách hàng. Verify: `pytest tests/unit/test_profiles.py`. Files: `profiles.py`, test.
- [x] **T13 — Chuẩn hoá và phân cụm.** Phụ thuộc: T12. Nghiệm thu: Q/U/V; inactive; K-Means chọn K và fallback; DBSCAN giữ noise; seed ổn định. Verify: `pytest tests/unit/test_clustering.py`. Files: `clustering.py`, test.
- [x] **T14 — Tổng hợp và suy rộng.** Phụ thuộc: T12/T13. Nghiệm thu: trọng số, chênh lệch loại ngày, cân bằng A, cộng cụm/noise và mọi trường hợp A/S=0/thiếu. Verify: `pytest tests/unit/test_scaling.py`. Files: `scaling.py`, test.

### Checkpoint tính toán

- [x] **C01.** T01–T14 pass cùng nhau; công thức có kiểm thử độc lập và không skip.

## Pipeline và ứng dụng

- [x] **T15 — Pipeline nghiên cứu.** Phụ thuộc: T05/T09/T14. Nghiệm thu: nhập→VEE→cohort→cụm→suy rộng, trạng thái từng ô/partial, lưu đủ nguồn và diagnostics. Verify: `pytest tests/integration/test_pipeline.py`. Files: `application/pipeline.py`, `application/models.py`, test.
- [x] **T16 — Bộ xuất bảng và manifest.** Phụ thuộc: T15. Nghiệm thu: CSV/XLSX wide/long 24/48 kW/kWh, công thức injection, không cắt XLSX, ghi atomic và phương pháp. Verify: `pytest tests/integration/test_export.py`. Files: `exports.py`, test.
- [x] **T17 — Hình báo cáo.** Phụ thuộc: T16. Nghiệm thu: PNG/SVG từ kết quả thật, nhãn đúng và tổng thành phần. Verify: `pytest tests/integration/test_charts.py`. Files: `charts.py`, test.
- [x] **T18 — Worker process.** Phụ thuộc: T15. Nghiệm thu: job nền, sự kiện tiến độ, huỷ không làm hỏng run cũ, không IPC toàn dữ liệu thô. Verify: `pytest tests/integration/test_jobs.py`. Files: `application/jobs.py`, test.
- [x] **T19 — Desktop dự án/nguồn/cấu hình.** Phụ thuộc: T15/T18. Nghiệm thu: mở/tạo dự án, chọn tệp/mapping/lịch, kiểm tra cấu hình, chạy/huỷ thật từ UI. Verify: `pytest tests/ui/test_workflow.py`. Files: `ui/window.py`, `ui/forms.py`, `__main__.py`, test.
- [x] **T20 — Desktop kết quả/chất lượng/lịch sử.** Phụ thuộc: T16/T17/T19. Nghiệm thu: lọc, chart/table, 24/48 kW/kWh, nhóm/đổi nhãn, so hai run và xuất. Verify: `pytest tests/ui/test_results.py`. Files: `ui/results.py`, `ui/window.py`, test.
- [x] **T20a — Nhãn nhóm có lịch sử.** Phụ thuộc: T05/T15. Nghiệm thu: ghi nhãn/lý do riêng, không sửa artifact đã hoàn thành; mở lại vẫn còn. Verify: `pytest tests/unit/test_annotations.py`. Files: `workspace.py`, test.
- [x] **T20b — Bộ lọc và bảng/chất lượng/so sánh desktop.** Phụ thuộc: T17/T19/T20a. Nghiệm thu: kết quả thực, bảng 24/48, đổi đơn vị, diagnostics, thành viên, so config/cohort hai run. Verify: `pytest tests/ui/test_results.py`. Files: UI model/results/window và test.
- [x] **T20c — Xuất lựa chọn và xem nguồn.** Phụ thuộc: T16/T20b. Nghiệm thu: xuất đúng bộ lọc, lưu nhãn trong báo cáo, xem trước nguồn có giới hạn. Verify: tests export + UI. Files: exports/charts và UI liên quan.
- [x] **T20d — Sao lưu, xác minh nguồn và truy vết ngày.** Phụ thuộc: T05/T18/T20b. Nghiệm thu: bản sao lưu kèm nguồn tái chạy khi nguồn ngoài mất; worker báo nguồn thay đổi; xem trước/sau bù một ngày từ catalog/cache đã lưu. Verify: `test_backup.py`, `test_inspection.py`, `test_jobs.py`, `test_day_inspection.py`; full suite 133 pass sau review cuối.
- [x] **T21 — Demo/CLI và hướng dẫn nhập.** Phụ thuộc: T15/T16. Nghiệm thu: tạo dữ liệu tổng hợp, chạy CLI và GUI được; có mẫu/schema giải quyết OQ đầu vào. Verify: `pytest tests/integration/test_cli.py`. Files: `demo.py`, `cli.py`, `README.md`, test.

### Checkpoint ứng dụng

- [x] **C02.** Full suite pass; luồng desktop và CLI tạo bộ kết quả cân bằng từ tệp tổng hợp.

## Tối ưu, rà soát và bàn giao

- [x] **T22 — Kiểm chứng hiệu năng.** Phụ thuộc: C02. Nghiệm thu: benchmark tái lập có CPU/RAM/OS, thời gian/RSS/disk; kiểm thử batch, giới hạn tài nguyên. Verify: `pytest tests/performance`; lệnh benchmark ghi báo cáo. Files: `benchmark.py`, tests, báo cáo.
- [x] **T23a — Review công thức/nguồn và regression.** Phụ thuộc: C02. Nghiệm thu: 6 finding ban đầu + member filter/MAD/đối soát được tái hiện Red rồi Green; mutation alpha sai bị bắt. Verify: XML T23-*.
- [x] **T23b — Dependency audit và kiểm tra tĩnh.** Phụ thuộc: T23a. Nghiệm thu: audit lock không có vulnerability đã biết; Ruff/mypy pass. Verify: `dependency-audit.json`; Ruff và mypy đã chạy lại sau sửa cuối; full suite 133 pass, không skip.
- [x] **T23c — Review bổ sung backup và worker crash.** Phụ thuộc: T20d. Nghiệm thu: portable lookup khác OS, crash đã kết thúc được thu hồi đúng khoá của worker và trạng thái failed. Verify: regression Red/Green + full suite.
- [x] **T23 — Đơn giản hoá, review và hardening.** Phụ thuộc: C02/T22. Nghiệm thu: áp dụng các skill được yêu cầu, mutation bị test phát hiện, input/path/SQL/export được kiểm tra, audit dependencies có kết quả. Verify: full pytest + lint/type/audit; `docs/review.md`. Files: các module có finding, regression tests, báo cáo.
- [x] **T24 — Build và hướng dẫn kiểm thử.** Phụ thuộc: T23. Nghiệm thu: wheel build, GUI runtime smoke, hướng dẫn hai OS và danh sách giới hạn; full suite pass 100% không skip/xfail. Verify: `pytest`, Ruff, mypy, wheel build, smoke. Files: `README.md`, `packaging/`, `docs/verification/`, báo cáo.
- [ ] **E01 — Xác nhận adapter bằng tệp CMIS/MDMS thực.** Phụ thuộc: tệp/ngữ nghĩa do đơn vị cung cấp. Nghiệm thu: mapping/kênh/hệ số/kỳ được xác nhận; UAT có đối soát.
- [ ] **E02 — AC-23 trên máy sạch Windows và macOS.** Phụ thuộc: môi trường đích/CPU và bộ cài. Nghiệm thu: cài/chạy/nhập/tính/xuất không cần Python trên cả hai OS.
- [ ] **E03 — AC-24 quy mô đầy đủ và UAT.** Phụ thuộc: benchmark 122,64 triệu giá trị, điều kiện máy được chốt và đánh giá chuyên viên. Nghiệm thu: số đo thật so mục tiêu spec; không thay bằng benchmark nhỏ.

## Tự động hoá phát hành

- [x] **T25 — Công cụ kiểm tra gói phát hành.** Phụ thuộc: T24. Nghiệm thu: từ chối tag/metadata khác version, phát hiện thiếu executable, smoke chạy demo và xuất bằng chương trình đóng gói từ thư mục ngoài source. Verify: 17 test helper/manifest Red→Green; compiled executable được kiểm tra thêm trong workflow.
- [ ] **T26 — GitHub Actions.** Phụ thuộc: T25. Nghiệm thu: lint/type/test/audit trên Windows x64 và macOS arm64; build DMG/Windows ZIP khi tag hoặc chạy thủ công; chỉ job publish có quyền ghi; tạo pre-release sau mọi gate đạt, không ghi đè release cũ. Verify: actionlint và kiểm tra workflow trên GitHub.
- [x] **T26a — Sửa lỗi backup lộ ra trên CI Windows.** Phụ thuộc: T26. Nghiệm thu: đóng kết nối SQLite đích trước rename/cleanup, cả khi công bố backup lỗi; giữ kiểm tra bất biến và đối soát nguồn. Verify: 2 regression Red→Green; CI 40062843834 đạt 152/152 trên mỗi OS, không skip.
- [ ] **T26b — Module nhập động trong native bundle.** Phụ thuộc: T26. Nghiệm thu: đóng gói FFT/linalg trong NumPy compatibility vendored của SciPy/scikit-learn; bật cloudpickle compatibility; native smoke demo/xuất đạt. Verify: lỗi thực `scipy._external.array_api_compat.numpy.fft` trong lượt 40062858984, khai báo include-package và chạy lại native; lưu cache compiler cho lượt sau.
- [ ] **T27 — Hướng dẫn và kiểm chứng.** Phụ thuộc: T26. Nghiệm thu: tài liệu tag/chạy thử/tải artifact; full suite pass không skip, cập nhật trạng thái CI và push workflow lên GitHub. E01/E02/E03 giữ điều kiện nghiệm thu riêng.

## Nhật ký kiểm chứng

Bằng chứng Red/Green thô theo task được giữ cục bộ tại `docs/verification/`. Repository chứa báo cáo tổng hợp và JUnit cuối đã bỏ hostname. Kết quả cuối cùng và việc chưa kiểm chứng được ghi trong `docs/verification/final.md`; không thay thế task ngoài môi trường bằng dấu `[x]`.
