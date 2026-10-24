# Kế hoạch triển khai Load Research

Nguồn chuẩn: `load-research.md`. Danh sách task và trạng thái duy nhất: `tasks.md` ở thư mục gốc, theo yêu cầu người dùng. Người dùng đã yêu cầu thực hiện liên tục lập kế hoạch → TDD → đơn giản hoá → review/bảo mật; không cần một vòng xin phép riêng giữa các giai đoạn đã được giao.

## Quyết định triển khai

- Python 3.12, PySide6, DuckDB/Parquet, NumPy/scikit-learn, SQLite metadata. Dùng môi trường ảo riêng và dependency lock; không sửa Python hệ thống.
- Lõi nghiệp vụ không phụ thuộc Qt; pipeline dùng cùng hợp đồng cho CLI và desktop.
- File thực tế chưa được cung cấp: triển khai bộ nhập có ánh xạ và mẫu dữ liệu chuẩn; các ngữ nghĩa không rõ phải được khai báo hoặc từ chối. Không giả định adapter đã được xác nhận với CMIS/MDMS sản xuất.
- Công thức và ngưỡng giữ theo spec. Chọn mẫu mới, mạng và thông tin đại diện thống kê ngoài phạm vi.
- Ban đầu không có Git repository. Theo yêu cầu xuất bản tiếp theo, mã nguồn được đưa lên `https://github.com/binhnt149/load-research`; dữ liệu nghiên cứu và cache được giữ cục bộ. Bằng chứng TDD thô lưu cục bộ tại `docs/verification/`; repository chứa báo cáo tổng hợp và JUnit cuối đã bỏ hostname.

## Đồ thị phụ thuộc

T01 → T02/T03/T04 → T05/T06 → T07 → T08 → T09/T10 → T11 → T12/T13 → T14 → T15 → T16 → T17 → T18/T19 → T20 → T21 → T22 → T23 → T24.

Thực hiện tuần tự, checkpoint sau các nhóm tính toán, pipeline và UI. Mỗi task có tests Red trước phần mã hành vi, Green sau đó; refactor không thay đổi test để che thay đổi hành vi. Task tài liệu/cấu hình thuần không cần test Red nhân tạo.

## Kiểm chứng

- Unit theo chức năng và trường hợp biên; integration dùng tệp thật CSV/XLSX/Parquet tổng hợp, có kết quả tính độc lập.
- UI chạy Qt offscreen và kiểm tra app thực khi môi trường hỗ trợ.
- Kiểm tra mutation có chủ đích sau review; chạy toàn bộ suite không skip/xfail trước khi bàn giao.
- Benchmark nhỏ nằm trong suite; benchmark quy mô 7.000 × 365 × 48 chạy riêng và ghi thông số thật nếu đủ tài nguyên. Không suy diễn benchmark nhỏ thành AC-24.
- Windows và máy sạch không có tại máy macOS hiện tại: chuẩn bị hướng dẫn/cấu hình đóng gói nhưng giữ task xác nhận ngoài môi trường ở trạng thái chưa hoàn thành.

## Rủi ro

| Rủi ro | Xử lý |
|---|---|
| Chỉ Python 3.15 trên PATH | Dùng Python 3.12 có sẵn trong runtime, tạo `.venv` tại dự án |
| Tệp thực/ngữ nghĩa chưa được xác nhận | Mẫu nhập, mapping và validation bắt buộc, báo rõ giới hạn |
| Dữ liệu 122 triệu giá trị | Batch import, DuckDB, phân vùng tháng, worker process, không đưa dữ liệu thô vào UI |
| Gói Qt/khoa học cần tải | Chỉ wheel, lock phiên bản, audit; báo chính xác nếu mạng/cài đặt bị chặn |
| Không có máy Windows | Không đánh dấu AC-23 đạt; bàn giao kiểm thử riêng |

## Điều kiện kết thúc

Toàn bộ tests đã triển khai phải pass, không bỏ/skips tests thất bại. Task chỉ `[x]` khi tiêu chí được kiểm chứng. Các mục phụ thuộc dữ liệu thực/máy khác giữ `[ ]`, ghi lý do và hướng dẫn tiếp tục thay vì khai hoàn thành giả.
