# Kiểm chứng nâng cấp Kết quả — 26/10/2026

Nhánh triển khai: `feature/results-and-localization`. Đây là thay đổi sau v0.1.2,
chưa tạo tag hoặc phát hành phiên bản mới. Bản sửa README đang có của người dùng
được giữ nguyên và không đưa vào các commit của thay đổi này.

## Phạm vi đã kiểm tra

- Tổng hợp điện năng nhiều ngành trước khi đổi kW hoặc chuẩn hóa; gộp loại ngày
  theo số ngày của lịch nghiên cứu; các ngành/nhóm trùng mã không bị cộng hai lần.
- Thành phần phụ tải có tên, toàn đơn vị kiểm tra danh mục ngành, thiếu phạm vi
  không biến thành đường 0 hoặc tổng đầy đủ. Kết quả cũ chưa biết phạm vi không
  được xác nhận toàn đơn vị.
- Tập mẫu chung có trọng số, tổng nguồn/sau VEE từng ngày; phương pháp đại diện
  theo loại ngày và phương pháp giữ biến thiên với hệ số tháng riêng. Trường hợp
  thiếu A, mẫu 0, thiếu ngày, ngày không đủ điều kiện và khoảng thiếu được kiểm tra.
- Artifact ngày được đăng ký checksum; dựng lại snapshot cũ từ catalog/cache đã
  xác minh khi tệp nguồn offline, không sửa snapshot cũ; có hủy tác vụ.
- CSV/XLSX dài/rộng, 24/48 chu kỳ, PNG/SVG dùng cùng view tính toán với bảng và
  biểu đồ; ghi ngày/tháng, phạm vi, chuẩn hóa, phương pháp và hệ số. Bộ lọc ngành,
  loại ngày và nhóm được áp dụng cả đường và thành viên. Ô thiếu để trống.
- Công thức/URL từ chuỗi nhập không được thực thi trong Excel, CSV được chặn
  tiền tố công thức; xuất qua staging, không ghi đè báo cáo cũ, hủy không công bố
  thư mục dở dang. Manifest có checksum và cấu hình nhập được rút gọn đường dẫn.
- Lỗi nhập có tiếng Việt và tọa độ nguồn khi biết; bảng lỗi MDMS tối đa 1.000
  dòng hiển thị, nhật ký đầy đủ vẫn trên đĩa. Giữ thông điệp kỹ thuật gốc để truy vết.
- Giao diện chọn nhiều ngành/ngày, xem hệ số và trạng thái thiếu, bấm đọc chu kỳ,
  đổi đơn vị/chu kỳ/chuẩn hóa, xem bảng mở rộng và resize; thử thêm lựa chọn 50 ngành.

## Bằng chứng cục bộ

| Kiểm tra | Kết quả |
|---|---|
| Pytest toàn bộ sau refactor | 272 pass, 0 fail/error/skip/xfail |
| Ruff lint và định dạng | Pass |
| mypy | Pass, 50 module source |
| Wheel | Build pass, 50/50 module khớp source; SHA-256 `1eced196fbd9d3dd975dd17edf459a9969f510f40eb72d76a62045ebe124e7f7` |
| Audit lock runtime/dev và build | 72 gói runtime/dev và 3 gói build, không có lỗ hổng đã biết tại thời điểm kiểm tra |
| Mutation tổng hợp | Đảo điều kiện đủ phạm vi làm test thất bại; khôi phục source |
| Mutation resize | Thay Figure mới thay vì dùng canvas hiện hữu làm test thất bại; khôi phục source |
| So sánh trước/sau refactor báo cáo | Giá trị và thứ tự cột dài/rộng giữ nguyên |
| Qt Cocoa thực tế | Demo 20 khách hàng, 2 ngành; 5 trạng thái tại 1024×768 pass |

Ảnh Cocoa đã kiểm tra gồm thành phần 48/24 chu kỳ, chuẩn hóa 24 chu kỳ và hai
phương pháp theo ngày. Canvas 958×180 logical pixel; bảng tương ứng 48/24 dòng.
Regression bổ sung tái hiện trường hợp thông tin tổng hợp và điểm bấm cùng chiếm
hai dòng: cửa sổ vượt 768 px hoặc thanh chia lấn canvas. Bỏ khoảng đệm dọc lồng
nhau ở vùng Kết quả; kiểm tra lại kích thước cửa sổ và hình học thanh chia đều pass.
Ảnh [tổng hợp](results-cocoa-aggregate.png) và [theo ngày](results-cocoa-daily.png)
dùng dữ liệu tổng hợp, không chứa thông tin khách hàng thực. Log/JUnit/ảnh thô
trong `ci-results/` được ignore vì có đường dẫn máy cá nhân.
[Bản tổng hợp kiểm tra](results-checks.json) và [số đo runtime](results-runtime.json)
đã bỏ hostname và đường dẫn cá nhân.

## Rà soát độc lập

Các lỗi được phát hiện và có regression: coverage toàn đơn vị cũ chưa biết;
đơn vị chuẩn hóa; scope mẫu của view ngày; ngày lịch không theo bộ lọc; nhóm
hành vi và thành viên xuất sai lựa chọn. Tất cả đã sửa. Lượt rà soát lại xác nhận
không còn Critical/Required trong các phần này và helper kiểm tra console. Rà soát
cuối kiểm tra thêm nhãn nhóm trùng tên, ngữ cảnh hình báo cáo, việc xóa kết quả cũ
khi lần nghiên cứu mới không có ô phù hợp và bản sửa khoảng đệm cửa sổ nhỏ.

Phân tích bảo mật tập trung vào tệp nhập không tin cậy, dữ liệu khách hàng lưu
cục bộ, tính toàn vẹn artifact/cache và xuất bảng tính. Không thêm dịch vụ bên
ngoài hoặc dependency; khóa nguồn dữ liệu và đường dẫn an toàn dùng cơ chế hiện có.
Tổng ngày được tích lũy theo ngành-tháng, không tạo khối khách hàng × năm trong RAM.

## Kiểm chứng Windows

Các lượt CI đầu giữ nguyên regression và phát hiện chênh lệch font của môi trường
Windows/offscreen. Số đo tiêu đề cho thấy ký tự có cùng độ rộng; đối chiếu Qt 6.12
cho thấy offscreen dùng FreeType và đọc `QT_QPA_FONTDIR`. Test bootstrap nay trỏ
đến thư mục Fonts của Windows, kèm guard không được dùng font hộp dự phòng.
Nguồn chính thức: [offscreen integration](https://github.com/qt/qtbase/blob/v6.12.0/src/plugins/platforms/offscreen/qoffscreenintegration.cpp),
[font directory](https://github.com/qt/qtbase/blob/v6.12.0/src/gui/text/qplatformfontdatabase.cpp).
[Lượt CI cuối 40339613158](https://github.com/binhnt149/load-research/actions/runs/40339613158)
kiểm tra source `2edb09c`: **272/272 mỗi OS**, 0 fail/error/skip; lint, định dạng,
mypy, dependency audit và wheel build đều pass. Full suite cục bộ cùng source:
272 pass trong 36,73 giây.

[Native Windows đã kiểm chứng](https://github.com/binhnt149/load-research/actions/runs/40327062787)
ở source `2dbb1dd`: CLI demo/xuất XLSX/PNG/SVG, tạo ZIP và smoke console đều pass.
Smoke có đối chứng dương `python.exe`, khởi chạy desktop từ `pythonw.exe` không có
console cha, xác nhận tiến trình còn chạy và không tạo console mới. Cấu hình
`--windows-console-mode=attach` giữ nguyên sau lượt này.

Build native Windows tại source cuối `2edb09c` đang chạy khi chốt báo cáo; chưa
xác nhận smoke của bundle này. Lượt thủ công chỉ tạo artifact, không publish.
Các bổ sung sau native đã kiểm chứng gồm nhãn/chú thích báo cáo, xóa kết quả cũ
và bố cục cửa sổ nhỏ; có regression, review và quality gates hai OS như trên.

E01 (dữ liệu thực), E02 (UAT bộ cài trên máy sạch hai OS), E03 (7.000 khách hàng
đủ 12 tháng và UAT) vẫn mở. Smoke trên runner và Cocoa source không thay nghiệm
thu trên máy sạch hoặc xác nhận tính đại diện thống kê của mẫu đã chốt.

## Đo 7.000 khách hàng × một tháng

Lượt synthetic 01/2025, 10.416.000 giá trị, bộ nhớ DuckDB 512 MB, 2 luồng:
865,108 giây phân tích/xuất, tổng 868,824 giây, RSS đỉnh 1,075 GiB, disk đỉnh
2,382 GiB và 110,561 MiB giữ lại. Sai lệch cân bằng tối đa 1,1921×10⁻⁷ kWh,
2 artifact ngày đã lưu; trạng thái `completed`. [Báo cáo số đo](results-benchmark-7000x1.json).

Số đo cũ cùng quy mô là 565,675 giây. Lượt hiện tại không cô lập khỏi các tác vụ
kiểm thử/GUI đang chạy; không kết luận tăng tốc hoặc quy chênh lệch cho riêng phần
lưu ngày. Cần đo lặp có kiểm soát khi nghiệm thu E03; không nội suy đủ 12 tháng.

## Chạy lại

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check src tests packaging
.venv/bin/ruff format --check src tests packaging
.venv/bin/mypy src/load_research
.venv/bin/python -m build --wheel --no-isolation
PYTHONPATH=src .venv/bin/python -m load_research
```

Trong ứng dụng, mở lần nghiên cứu → **3 · Kết quả**; dùng các bộ chọn Ngành/Loại
ngày để chọn nhiều mục, chọn cấp tổng hợp. Chuyển **Theo từng ngày**, chọn **Nạp
dữ liệu ngày**, rồi chọn phương pháp. Bấm biểu đồ để đọc số liệu; nút **Bảng**
mở rộng bảng trên cửa sổ nhỏ. Nút **Cách tính…** và mỗi báo cáo có đầy đủ công thức.
Xem [tài liệu tính toán](../results-calculations.md).
