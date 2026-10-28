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

## Đợt 26/10/2026 — Kết quả tổng hợp, dữ liệu ngày và Việt hóa

Yêu cầu đã chốt trực tiếp: có cả một đường tổng hợp và nhiều đường so sánh; xem dữ liệu mẫu trước/sau xử lý cùng hai mô hình suy rộng ngày (theo loại ngày và giữ biến thiên từng ngày). Tiếp tục trên kế hoạch hiện hữu; `tasks.md` vẫn là danh sách trạng thái duy nhất. Giữ nguyên các điều kiện E01/E02/E03 và chỉnh sửa README cục bộ của người dùng.

| Khả năng | Trách nhiệm | Phụ thuộc |
|---|---|---|
| desktop-launch | Windows mở GUI không tạo cửa sổ dòng lệnh; giữ chạy CLI/worker | đóng gói hiện hữu |
| vi-presentation | Thuật ngữ, thông báo lỗi có vị trí/hướng xử lý, bảng và báo cáo tiếng Việt | hợp đồng dữ liệu hiện hữu |
| result-aggregation | Cộng nhiều mã ngành, thành phần phụ tải, toàn đơn vị; gộp loại ngày có trọng số | industry-scaling, calendar |
| daily-profiles | Mẫu trước/sau VEE và hai mô hình suy rộng theo ngày | result-aggregation, canonical cache, cohort |
| result-charts | Chọn nhiều phạm vi, so sánh, click số liệu, resize và xuất đúng lựa chọn | result-aggregation, daily-profiles, vi-presentation |
| result-methodology | Công thức, điều kiện, ví dụ tính tay và giới hạn diễn giải | các khả năng trên |

Thứ tự: sửa resize → console Windows → từ vựng/lỗi → phép tổng hợp → lưu/đọc dữ liệu ngày → tích hợp giao diện/xuất → tài liệu và kiểm chứng toàn bộ. Các task cụ thể T35–T48 nằm trong `tasks.md`; checkpoint sau T38, T43 và T48.

Quy tắc tính: cộng điện năng theo cùng chu kỳ trước khi đổi kW/chuẩn hóa; không cộng các đường chuẩn hóa độc lập. Các ngành được suy rộng riêng bằng A ngành rồi cộng, không nhân lại một hệ số chung. Gộp loại ngày bằng số ngày lịch thực tế. Không tạo tổng đầy đủ khi một ngành được chọn còn thiếu đường cong; hiển thị ngành thiếu và trạng thái rõ. Toàn đơn vị giới hạn đúng phạm vi nghiên cứu/độ phủ ngành có thể xác minh.

Ngày lịch dùng đúng đường đại diện E của loại ngày. Phương pháp biến thiên ngày dùng tập khách hàng chung đã lưu: D = tổng điện năng mẫu sau xử lý của toàn bộ ngày, beta = A/D; chỉ có đường suy rộng khi mọi ngày của cohort đều đủ điều kiện. Thiếu cả ngày không được tự bù bằng ngày đại diện. Ngày nguồn trước VEE có thể chứa ước lượng từ hệ thống; giữ chỉ báo chất lượng. A=0/D=0/thiếu A xử lý riêng, bảo toàn tháng trong cùng dung sai hiện hữu.

Dữ liệu ngày được xử lý trong worker, theo ngành-tháng, không nạp 12 tháng dữ liệu khách hàng thô vào Qt. Ưu tiên tái sử dụng quá trình VEE để lưu aggregate ngày có checksum; kết quả cũ có thể dựng lại từ catalog/cache đã xác minh, không sửa snapshot cũ. Cache phụ trợ phải gắn config/cohort/import/method và kiểm tra toàn vẹn trước khi dùng.

Giao diện giữ theme hiện có, chia bộ lọc thành các hàng gọn; luôn phân biệt ngành nghề, thành phần phụ tải theo mã ngành và nhóm hành vi. Đổi bộ lọc không thay kích thước Figure độc lập với canvas. Click chọn điểm hiển thị chu kỳ/khoảng giờ/tên đường/giá trị/đơn vị; bảng chu kỳ là cách truy cập tương đương bằng bàn phím. Báo cáo GUI dùng tiêu đề/giá trị tiếng Việt, giữ schema nội bộ và tùy chọn xuất kỹ thuật để tái lập.

Rủi ro: thiếu A/ngành/lịch, trộn cơ sở kỳ, nhóm hành vi trùng tên, ngày không đủ cohort, kết quả cũ thiếu artifact ngày, checksum cache, DPI/legend dài, console/CLI trên Windows. Verify bằng fixture tính tay, integration tệp thật, Qt hình học/sự kiện click, bộ xuất CSV/XLSX/PNG/SVG, smoke đóng gói phù hợp và full suite không skip.

## Đợt 27/10/2026 — Khoảng ngày và danh mục thành phần

T49 → T53 → T54 → T55; T50 → T51 → T52; T53 → T56 → T57; tất cả → T58.
Danh sách trạng thái duy nhất là T49–T58 trong `tasks.md`; bổ sung vào kế hoạch cũ.
Khoảng ngày hiển thị chuỗi thời gian liên tục từ 00:00 ngày đầu đến hết ngày cuối,
bao gồm hai đầu, cho phép xuyên tháng trong các tháng nghiên cứu đã lưu. Hệ số
suy rộng vẫn riêng ngành-tháng, không tính lại A theo khoảng đã chọn. Chuẩn hóa
sau tổng/chuyển chu kỳ trên toàn khoảng; đường còn thiếu không có hình dạng chuẩn hóa.
Danh mục là ánh xạ ngành→thành phần, mỗi ngành thuộc một thành phần để tránh đếm đôi.
Nhập danh mục độc lập trong dự án; mỗi lần nhập lưu phiên bản bất biến và checksum,
báo cáo đóng băng đúng phiên bản dùng; không buộc tính lại VEE cho dữ liệu đã xử lý.
Tra cứu khách hàng đọc canonical cache và cấu hình đã chốt theo từng tháng trong
worker, không lấy tổng ngành hoặc nhân trọng số làm dữ liệu đo của khách hàng.
Tách các điều khiển biểu đồ/khoảng ngày/danh mục sang module nhỏ để tránh dồn tất
cả vào ResultsView. Giữ nguyên chỉnh sửa README cục bộ của người dùng.

# Kế hoạch bổ sung: hiệu chỉnh MDMS và VEE — 28/10/2026

- Bảo toàn hồ sơ cũ: cấu hình đã lưu, cache đã kiểm chứng, kết quả và truy vết trước/sau không bị diễn giải lại theo phương pháp mới.
- Thời điểm được đưa về đầu khoảng trước đó theo chu kỳ nguồn, trước khi kiểm tra trùng, ghép công tơ và gom chu kỳ; ghi nhận mốc nguồn, mốc hiệu chỉnh và mức lệch. Với nguồn đóng dấu cuối chu kỳ, hiệu chỉnh dấu trước khi quy đổi về đầu chu kỳ.
- Cần phân biệt **đủ 100% chu kỳ có giá trị** với **100% giá trị đo gốc**. Giá trị bù phải gắn cờ, có phương pháp/nguồn và không vượt qua khoảng được đánh dấu cấm bù. Bù dựa trên dữ liệu có căn cứ; loại khách hàng-tháng không thể hoàn chỉnh khỏi tập mẫu và ghi rõ lý do.
- Thực hiện theo T61–T66 trong `tasks.md`: kiểm thử Red/Green từng lớp, kiểm tra snapshot cũ, pipeline, export, UI và kiểm chứng cuối; không thay đổi các hạng mục E01/E02/E03 đang mở.
