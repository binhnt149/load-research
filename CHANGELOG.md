# Changelog

## Unreleased

## 0.1.3 — 2026-10-27

Bản thử nghiệm nâng cấp tổng hợp và tra cứu Kết quả; giữ nguyên phương pháp `class-profile-v1` và snapshot nghiên cứu đã lưu.

- Trục Y tự co giãn theo đường đang hiện; chọn riêng từng đường, hiện/ẩn tất cả; xuất hình giữ lựa chọn đường, bảng dữ liệu vẫn đầy đủ.
- Xem/xuất từ ngày đến ngày xuyên tháng, giữ hệ số riêng ngành-tháng; chuẩn hóa toàn khoảng, ngày và phạm vi thành viên đúng từng tháng.
- Nhập danh mục ngành/thành phần từ CSV/XLSX có mẫu/xem trước, lưu phiên bản/checksum tại dự án và đóng băng trong báo cáo.
- Tìm và xem khách hàng mẫu trước/sau VEE theo ngày hoặc khoảng ngày, gồm khách hàng bị loại khỏi cohort; không áp trọng số/suy rộng. Ẩn bộ chọn Nhóm và bộ lọc không áp dụng; sửa nền ô ngày trên macOS.

- Tổng hợp nhiều ngành và loại ngày theo lịch, thành phần phụ tải có tên, kiểm tra đủ phạm vi toàn đơn vị; đường tổng và các đường so sánh dùng chung số liệu với bảng và báo cáo.
- Biểu đồ từng ngày có mẫu nguồn/sau VEE và hai phương pháp suy rộng: lặp ngày đại diện hoặc giữ biến thiên với hệ số tháng riêng. Lưu tổng mẫu ngày kèm checksum, dựng lại lần chạy cũ từ cache đã xác minh.
- Báo cáo GUI bằng tiếng Việt, lựa chọn 24/48 chu kỳ, kW/kWh/chuẩn hóa; biểu đồ phản hồi khi bấm và co giãn theo cửa sổ. Tài liệu tính toán đầy đủ tại `docs/results-calculations.md` và nút “Cách tính…”.
- Lỗi nhập bằng tiếng Việt có vị trí tệp/dòng/trang tính khi xác định được; nhật ký và bảng trình bày theo thuật ngữ điện. Cấu hình Windows dùng console mode `attach` để không tạo command window mới khi mở từ Explorer, vẫn hỗ trợ CLI.

## 0.1.2 — 2026-10-25

Bản thử nghiệm cải thiện giao diện và chuẩn bị dữ liệu đầu vào; giữ nguyên phương pháp `class-profile-v1`.

- Giao diện sáng với màu nhấn xanh, font hệ thống lớn hơn và bố cục bốn nhóm nguồn trong hai cột; đường dẫn đầy đủ giữ ở tooltip, các thao tác vẫn dùng đúng tệp gốc.
- Bổ sung mẫu CMIS, MDMS dài và rộng 24/48/96 chu kỳ, thương phẩm và lịch; lưu CSV/XLSX từ từng nhóm nguồn, kèm hướng dẫn cột và dữ liệu minh hoạ, không ghi đè tệp có sẵn.
- Sửa nút xem trước không phản hồi sau khi thêm tệp; tự chọn tệp hiện tại, hỗ trợ double-click, chọn sheet/dấu phân cách, đọc lại và hiển thị lỗi hoặc bảng chỉ có tiêu đề rõ ràng.

## 0.1.1 — 2026-10-24

Bản thử nghiệm bổ sung gói native macOS Apple Silicon và Windows x64, cùng bản sửa sao lưu trên Windows.

- GitHub Actions kiểm thử Windows/macOS, build DMG/Windows ZIP/wheel và tạo pre-release khi push tag hợp lệ; có chế độ build thử thủ công theo từng nền tảng.
- Đóng gói các module FFT/linalg và backend SVG nhập động; dùng Clang-cl trên Windows để khắc phục lỗi MSVC C1002 khi biên dịch SciPy. Native CLI demo và xuất XLSX/PNG/SVG đã đạt trên hai OS.
- Đóng connection SQLite đích trước khi công bố backup, sửa lỗi Windows không đổi tên/dọn được thư mục sao lưu; thêm regression cho cả nhánh thành công và lỗi.

## 0.1.0 — 2026-10-24

Bản phát hành thử nghiệm đầu tiên, dành cho kiểm tra phương pháp và UAT với dữ liệu của đơn vị.

- Desktop PySide6 và CLI xử lý cục bộ từ CMIS/MDMS CSV, XLSX, Parquet.
- Ghép công tơ/khách hàng, VEE có nhật ký, bù ngày tương đồng, tập mẫu chung và cấu hình lưu theo lần nghiên cứu.
- Chuẩn hoá Q/U/V, K-Means/DBSCAN, tổng hợp biểu đồ ngành-tháng-loại ngày và thành phần hành vi; suy rộng cân bằng thương phẩm tháng.
- Xem/xuất 24 hoặc 48 chu kỳ, kW/kWh; CSV/XLSX và hình PNG/SVG.
- Lịch sử bất biến, so sánh run, truy vết ngày, nhãn nhóm có lịch sử, sao lưu và xác minh nguồn bằng checksum.
- 133 test pass; Ruff/mypy pass. Benchmark thực 7.000 khách hàng × một tháng: 565,675 giây xử lý/xuất, RSS đỉnh 0,960 GiB.

Chưa nghiệm thu dữ liệu thực (E01), bộ cài độc lập trên Windows/macOS sạch (E02), hoặc benchmark đủ 12 tháng/UAT (E03). Chi tiết: [ghi chú phát hành](docs/releases/v0.1.0.md).
