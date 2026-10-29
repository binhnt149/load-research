# Kiểm chứng xử lý xung đột MDMS và phân tầng sản lượng

Ngày 29/10/2026. Kiểm chứng trên macOS trong workspace phát triển; chưa phát hành
bản cài mới hoặc kiểm thử native Windows cho thay đổi này.

- Với bộ dữ liệu thực do người dùng cung cấp, phiên bản 0.1.4rc1 dừng sau nhập
  do 529 nhóm bản ghi cùng công tơ–chu kỳ có giá trị/chất lượng mâu thuẫn sau
  làm tròn xuống. Trong đó 513 nhóm có mốc đúng và 16 nhóm chỉ có mốc lệch.
- Sau sửa và với chính bộ tệp, lần chạy cục bộ hoàn tất có cảnh báo: 7.246.489
  bản ghi chu kỳ, 2.380 bản ghi hiệu chỉnh thời điểm và 529 nhóm xung đột. Có
  1.482 dòng không ghép được công tơ và 9 dòng có số âm/không hữu hạn/không hợp
  lệ; các dòng này được ghi vào nhật ký nhập, không tự coi là số liệu hợp lệ.
  Dự án thử và dữ liệu khách hàng chỉ nằm trong `ci-results/` đã được Git bỏ qua.
- Test hồi quy kiểm tra ưu tiên gần mốc, ưu tiên đúng mốc, đồng hạng mâu thuẫn
  phải dừng, chính sách cũ, kiểm tra nhật ký/xuất và workbook có nhiều sheet trùng
  số dòng. Mỗi nguồn MDMS có định danh riêng để không ghép nhầm giữa các sheet.
- Bảng cấu hình người dùng có 88 tầng thuộc 18 ngành. Bộ đọc đã kiểm tra cấu
  trúc thực và test mẫu CSV/XLSX. Thử nghiệm phân tầng, phân bổ 25%/75%, bảo toàn
  điện năng, thiếu mẫu/cấu hình, nhóm ngoài phạm vi, tổng toàn đơn vị và khoảng
  xuyên tháng bằng dữ liệu giả lập, không dùng thông tin khách hàng thực trong test.
- Suy rộng giữ biến thiên ngày được kiểm tra độc lập bằng hai tầng có hình dạng
  ngày khác nhau; mỗi tầng dùng hệ số riêng và tổng tháng đúng thương phẩm. Tỷ
  trọng tham chiếu là giả định ước tính theo tháng, không phải số đo từng tầng.
- Các tình huống thực tế đã được rà soát độc lập: định danh nhiều sheet, hệ số
  tầng xuyên tháng và ngành chỉ có trong cấu hình. Đều có test hồi quy sau sửa.
- Toàn bộ **423/423** bài kiểm thử đạt, không lỗi hoặc bỏ qua; Ruff lint/format,
  mypy 62 module và build wheel đạt. Nội dung 62 module Python trong wheel khớp
  mã nguồn. Kiểm tra mở lại dự án mẫu phiên bản phương pháp v1 và truy vết một
  ngày đủ 48 chu kỳ đạt; kết quả lưu trước không bị sửa.

Điều kiện kiểm thử Windows/macOS trên máy sạch và quy mô 7.000 khách hàng × 12
tháng vẫn chưa được xác nhận; không suy rộng kết quả 1 tháng của bộ dữ liệu này
thành bằng chứng cho toàn bộ quy mô hoặc cho dữ liệu đầu vào khác.
