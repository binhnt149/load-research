# Tệp mẫu dữ liệu đầu vào

Trong ứng dụng, mở tab **Dữ liệu** → **Tệp mẫu…** ở đúng nhóm nguồn. Có thể xem dữ liệu minh hoạ, hướng dẫn từng cột và lưu **XLSX** hoặc **CSV UTF-8**. XLSX có sheet `Dữ liệu` đầu tiên để nhập trực tiếp và sheet `Hướng dẫn` phía sau; mã khách hàng/ngành được lưu dạng chuỗi.

Các CSV trong thư mục này dùng cùng nội dung với mẫu tích hợp trong ứng dụng:

| Tệp | Dùng cho |
|---|---|
| [cmis.csv](cmis.csv) | Tập khách hàng mẫu đã chốt, quan hệ khách hàng–công tơ và ngành |
| [mdms_long.csv](mdms_long.csv) | Một hàng công tơ/chu kỳ; ví dụ kWh, 30 phút, dấu đầu chu kỳ |
| [mdms_wide_24.csv](mdms_wide_24.csv) | Một hàng công tơ/ngày, 24 cột slot, nguồn 60 phút |
| [mdms_wide_48.csv](mdms_wide_48.csv) | Một hàng công tơ/ngày, 48 cột slot, nguồn 30 phút |
| [mdms_wide_96.csv](mdms_wide_96.csv) | Một hàng công tơ/ngày, 96 cột slot, nguồn 15 phút |
| [billing.csv](billing.csv) | Tổng điện năng thương phẩm toàn bộ ngành theo tháng |
| [calendar.csv](calendar.csv) | Ngày đặc biệt/ghi đè đã chốt; không phải lịch lễ chính thức |

**Thay toàn bộ dòng minh hoạ bằng dữ liệu thực trước khi nghiên cứu.** Ví dụ dùng tháng `2026-01`, phạm vi `NPC`, mã ngành `01`, khách hàng `000001/000002`; không phải tập mẫu đại diện và chưa đủ dữ liệu một tháng. Đổi tháng/phạm vi/mã và các thiết lập tương ứng theo đợt nghiên cứu.

MDMS dài/rộng là những lựa chọn thay thế cho cùng dữ liệu, không nạp lại một số đo từ nhiều mẫu. Chọn đúng dạng, chu kỳ, đơn vị, hệ số và dấu thời gian trong **Ngữ nghĩa / ánh xạ MDMS**. Các ví dụ đều là điện năng kWh đã áp hệ số, chiều nhận. Nguồn 60 phút chỉ tạo được biểu đồ 24 chu kỳ/ngày; nguồn 15/30 phút có thể tổng hợp theo độ phân giải phân tích phù hợp. Thiếu để trống; `0` là số đo thật, không dùng để thay dữ liệu thiếu.

Ưu tiên XLSX nếu sửa bằng Excel để giữ mã có số 0 đầu. Khi mở CSV trong Excel, nhập các cột mã dưới dạng **Text** trước khi lưu; định dạng hiển thị số không khôi phục được số 0 đã bị mất. CSV dùng dấu phẩy và UTF-8/BOM. Không thêm dòng tiêu đề trang trí phía trên hàng tên cột. Không dùng công thức chưa có giá trị được tính sẵn.

Mẫu không ghi đè tệp sẵn có: chọn tên mới khi lưu. Bộ mẫu được tích hợp bằng mã ứng dụng nên cũng dùng được trong bản native, không cần thư mục mã nguồn bên cạnh.

Hợp đồng đầy đủ và các trường CMIS tuỳ chọn: [định dạng đầu vào](../docs/input-formats.md).
