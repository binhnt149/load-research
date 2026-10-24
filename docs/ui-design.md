# Giao diện Desktop: dữ liệu đầu vào

Mục tiêu: chuyên viên nhìn rõ nguồn đã chọn, xem nhanh dữ liệu, lấy đúng mẫu và chạy lại nghiên cứu theo phương pháp đã lưu. Không có bộ nhận diện hoặc ảnh tham chiếu riêng; thiết kế tiếp nối các tab và nút Qt hiện có, kiểm chứng bằng ảnh runtime trên cửa sổ 1.240×860 và 1.024×768.

- Nền sáng xám xanh, vùng nhập/bảng trắng, chữ xanh đậm; một màu nhấn xanh lam cho thao tác chính. Không dùng gradient hoặc bóng đổ trang trí.
- Font hệ thống Windows/macOS, thân chữ 14 px, tiêu đề chính 28 px và tiêu đề vùng 17 px; khoảng cách theo nhịp 4/8/12/16/24 px.
- Bốn nhóm nguồn bố trí hai cột ở cửa sổ desktop; có cuộn nếu chiều cao hạn chế. Tên tệp dễ quét, đường dẫn đầy đủ nằm ở tooltip và hộp xem trước. Chọn tệp không dựa riêng vào màu: có trạng thái số tệp và nút xem trước bật/tắt.
- Hành động chính là “Chạy nghiên cứu”; “Tệp mẫu…” và “Xem trước…” đặt cùng nguồn. Focus bàn phím, selection, disabled và lỗi có trạng thái riêng với tương phản rõ.
- Cửa sổ xem trước có tên tệp, sheet/dấu phân cách, thông báo số dòng/giới hạn hoặc lỗi và bảng read-only. Template có ví dụ và hướng dẫn cột riêng; không biến dữ liệu minh hoạ thành nguồn nghiên cứu tự động.
- Trạng thái cần kiểm tra: chưa có tệp, đã chọn, nhiều tệp, lỗi đọc, chỉ tiêu đề, xem trước có giới hạn, kết quả thực và hộp mẫu. Kiểm tra các hộp thoại kế thừa theme, focus theo Tab và các điều khiển không chồng/cắt.
