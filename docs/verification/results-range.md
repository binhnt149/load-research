# Kiểm chứng khoảng ngày và khách hàng — 27/10/2026

Nhánh `feature/results-range-and-customers`, source `f66c3c5`. Thay đổi sau
v0.1.2; chưa tạo tag hoặc release mới. Chỉnh sửa README có sẵn của người dùng
được giữ nguyên, không đưa vào commit. Không thêm dependency.

## Hành vi đã hoàn thành

- Trục Y tự bám dữ liệu hữu hạn đang hiện; không ép về 0, không cắt dữ liệu âm.
  **Đường dữ liệu…** bật/tắt từng đường, cập nhật chú giải và thông tin điểm bấm.
  Bảng số liệu không đổi. Hình PNG/SVG giữ lựa chọn ẩn; với biểu đồ chồng, vị trí
  các dải còn lại giữ nguyên như trên màn hình, kể cả khi ẩn đường tổng.
- Khoảng ngày bao gồm cả hai đầu, hỗ trợ xuyên tháng và lọc loại ngày. Mỗi tháng
  giữ hệ số suy rộng riêng tính trên đầy đủ tháng. Không suy rộng toàn bộ thương
  phẩm tháng vào riêng khoảng đang xem. Chuẩn hóa trên toàn chuỗi được chọn.
- Nhập/xem trước danh mục ngành → thành phần từ CSV/XLSX/Parquet, có biểu mẫu
  bốn cột tiếng Việt. Giữ mã 0 đầu, từ chối xung đột, lưu phiên bản/checksum và
  giữ trong sao lưu; báo cáo đóng băng đúng danh mục áp dụng. Ngành thiếu không
  bị bỏ khỏi tổng để tạo kết quả giả đầy đủ.
- Tra cứu mã khách hàng mẫu theo một ngày hoặc khoảng ngày, trước/sau VEE,
  kW/kWh, 24/48 chu kỳ. Có bảng chi tiết VEE và `customer-vee.csv`; không nhân
  trọng số hoặc hệ số suy rộng. Phần ngoài hiệu lực công tơ giữ thiếu, không bù.
- Bộ chọn Nhóm được ẩn. Đường đóng góp và chức năng đặt tên nhóm vẫn dùng được.
  Đổi bộ lọc/dự án không nhận câu trả lời nền cũ hoặc giữ biểu đồ khách hàng cũ.

## Kết quả kiểm tra

| Kiểm tra | Kết quả |
|---|---|
| Full suite sau refactor | **331 pass**, 0 fail/error/skip, 39,665 giây |
| Ruff lint/format | Pass |
| mypy | Pass, 59 module source |
| Wheel | Build pass, 59/59 module khớp source; import 59 module ngoài checkout pass |
| Audit lock | 72 gói runtime/dev + 3 gói build, 0 lỗ hổng đã biết khi kiểm tra |
| Mutation | Bỏ guard dự án của worker làm regression thất bại; phục hồi đúng byte, test pass |
| Cocoa thực tế | 9 trạng thái, 1024×768 và 1240×860, worker/import/xuất pass |

[Bằng chứng kiểm tra](results-range-checks.json) ghi SHA-256 của wheel. Wheel là
bản kiểm chứng cục bộ, không phải asset đã phát hành. Các tệp JUnit/log thô nằm
trong `ci-results/` được ignore vì có đường dẫn máy cá nhân.

Kiểm thử Red/Green đã tái hiện lỗi dải trục/toggle, thiếu hợp đồng danh mục,
thiếu API khoảng ngày/khách hàng, báo cáo mất ngày, UI chưa có lựa chọn mới,
khách hàng chỉ có hiệu lực một phần tháng, dữ liệu cũ khi đổi bộ lọc và trường
ngày thiếu tương phản. Kiểm thử bổ sung bằng dữ liệu tính tay xác nhận chọn hai
ngày có 8.000 kWh dùng cùng β = 100.000/7.200 như cả tháng 100.000 kWh; hủy đọc
không sửa snapshot. Không gọi kiểm thử bổ sung sau triển khai là bằng chứng Red.

Rà soát độc lập đã sửa các lỗi: tập ngành không hợp đúng qua nhiều tháng; xuất
thành viên ghép sai cặp tháng/loại ngày; nhận kết quả worker từ dự án cũ; hình
chồng xuất khác màn hình và thiếu chú giải khi chỉ còn dải chồng. Tất cả có
regression; lượt rà soát cuối không còn Critical/Required. Tách so sánh lần
nghiên cứu khỏi widget Kết quả trong commit refactor riêng, giữ test cũ.

Bảo mật kiểm tra validation tệp đầu vào, truy vấn SQLite/DuckDB có tham số,
checksum catalog/cache/artifact, quyền sở hữu tác vụ theo dự án và token/ngữ
cảnh, xuất bảng tính chống công thức/URL và staging không ghi đè báo cáo cũ.
Không tải dữ liệu khách hàng lên dịch vụ ngoài. Đọc khách hàng theo từng tháng,
không tạo khối 7.000 khách hàng × cả năm trong RAM để xem một khách hàng.

## Kiểm tra giao diện và tài nguyên

Cocoa dùng dữ liệu tổng hợp 20 khách hàng, hai ngành, tháng 02–03/2024; cố ý bỏ
một chu kỳ nguồn để đối chiếu VEE. Khoảng 29/02–02/03 có 144 dòng ở 48 chu kỳ,
72 dòng ở 24 chu kỳ; xuất rộng khách hàng có 6 dòng = 3 ngày × 2 đường.
[Số đo giao diện](results-range-runtime.json), [ảnh khoảng ngày](results-range-range-variation-48.png),
[khách hàng](results-range-customer-range.png), [bảng mở rộng](results-range-customer-table.png).
Ảnh không chứa dữ liệu khách hàng thật. Trên cửa sổ nhỏ, nút **Bảng** mở rộng
vùng số liệu để xem các dòng và cuộn ngang các cột.

Đọc lại biểu đồ đã tổng hợp từ nghiên cứu synthetic 7.000 khách hàng × một tháng:
31 ngày, 1.488 điểm/đường, 5 đường; phương pháp đại diện 0,146 giây, giữ biến
thiên 0,127 giây; RSS đỉnh tiến trình 112.197.632 byte. Sai lệch cân bằng tháng
bằng 0. [Báo cáo số đo](results-range-benchmark.json). Đây chỉ là đọc/tính view
từ dữ liệu đã lưu, không phải benchmark nhập/VEE hoặc đủ 12 tháng.

Chưa có build native hoặc lượt CI Windows mới cho thay đổi này. E01 (dữ liệu
thực), E02 (UAT bộ cài trên máy sạch hai OS), E03 (7.000 khách hàng × 12 tháng)
vẫn mở; kiểm thử source Cocoa không thay các nghiệm thu đó.

## Chạy và kiểm tra lại

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check src tests packaging
.venv/bin/ruff format --check src tests packaging
.venv/bin/mypy src
.venv/bin/python -m build --wheel --no-isolation
PYTHONPATH=src .venv/bin/python -m load_research
```

Mở lần nghiên cứu → **3 · Kết quả**. **Danh mục thành phần…** cho nhập/xem trước
hoặc lấy mẫu. Chọn **Từ ngày đến ngày**, đặt hai ngày và phương pháp, bấm **Nạp
khoảng ngày**. Chọn **Khách hàng mẫu**, tìm mã và bấm **Nạp khách hàng** để đối
chiếu trước/sau VEE. Dùng **Đường dữ liệu…**, **Bảng**, **Xuất lựa chọn…**.
Công thức và ý nghĩa số liệu: [tài liệu tính toán](../results-calculations.md),
cũng có trong **Cách tính…** và báo cáo xuất.
