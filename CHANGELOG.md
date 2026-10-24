# Changelog

## 0.1.0 — 2026-10-24

Bản phát hành thử nghiệm đầu tiên, dành cho kiểm tra phương pháp và UAT với dữ liệu của đơn vị.

- Desktop PySide6 và CLI xử lý cục bộ từ CMIS/MDMS CSV, XLSX, Parquet.
- Ghép công tơ/khách hàng, VEE có nhật ký, bù ngày tương đồng, tập mẫu chung và cấu hình lưu theo lần nghiên cứu.
- Chuẩn hoá Q/U/V, K-Means/DBSCAN, tổng hợp biểu đồ ngành-tháng-loại ngày và thành phần hành vi; suy rộng cân bằng thương phẩm tháng.
- Xem/xuất 24 hoặc 48 chu kỳ, kW/kWh; CSV/XLSX và hình PNG/SVG.
- Lịch sử bất biến, so sánh run, truy vết ngày, nhãn nhóm có lịch sử, sao lưu và xác minh nguồn bằng checksum.
- 133 test pass; Ruff/mypy pass. Benchmark thực 7.000 khách hàng × một tháng: 565,675 giây xử lý/xuất, RSS đỉnh 0,960 GiB.

Chưa nghiệm thu dữ liệu thực (E01), bộ cài độc lập trên Windows/macOS sạch (E02), hoặc benchmark đủ 12 tháng/UAT (E03). Chi tiết: [ghi chú phát hành](docs/releases/v0.1.0.md).
