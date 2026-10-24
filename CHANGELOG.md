# Changelog

## Unreleased

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
