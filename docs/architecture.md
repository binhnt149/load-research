# Kiến trúc triển khai v0.1

## Ranh giới

`domain` giữ kiểm tra đơn vị/cấu hình; lịch, VEE, profiles, clustering và scaling không gọi UI. `application` điều phối một pipeline chung cho CLI/Qt, worker spawn và kiểm tra một ngày. Adapter đọc CSV/XLSX/Parquet; SQLite giữ metadata và ledger checksum; exports/charts chỉ dùng kết quả đã tính.

UI không đưa toàn bảng đo vào model. Import theo Arrow batch 20.000, DuckDB giới hạn query memory/threads; dựng từng customer-month rồi giữ các vector đại diện. Silhouette giới hạn mẫu và BLAS được giới hạn luồng; DBSCAN có giới hạn vector. Xuất long tạo hàng tuần tự, Excel constant-memory. Các thao tác nghiên cứu, xuất, xác minh nguồn, sao lưu và truy vết chạy trong worker; IPC gồm cấu hình, tiến độ và tối đa một ngày khi kiểm tra.

## ADR-001 — Cache canonical dùng DuckDB

Đặc tả gợi ý Parquet chuẩn phân vùng. Bản triển khai chọn **một DuckDB bất biến chia sẻ**, chứa chu kỳ gốc chuẩn hoá và view khử trùng, thay vì ghi thêm một bản Parquet đầy đủ. Quyết định giữ một bản dữ liệu cột, một query engine và truy vết trùng/provenance; tránh tăng dung lượng trong lúc nhập. Parquet vẫn là định dạng nhập và Arrow là giao diện batch. Thư mục `canonical/` được dành cho khả năng xuất/trao đổi Parquet sau này, không khai là đã có bản Parquet chuẩn ở đó.

Cache key bao gồm canonicalizer/schema, scope, khoảng thời gian, manifest nguồn và ngữ nghĩa/ánh xạ. Cache được kiểm tra hash database và issue journal trước dùng lại. Lịch/VEE không làm mất cache số đo; mỗi run tính lại các bước phụ thuộc cấu hình này và giữ kết quả riêng.

Đây là lựa chọn triển khai lưu trữ trong kiến trúc đã chọn, không thay công thức. Chưa có benchmark AC-24 để kết luận tối ưu ở quy mô đủ. Chi phí checksum và validation toàn cache có thể cần tối ưu sau đo thực; không bỏ kiểm tra để tăng số đẹp.

## Run và tính bất biến

Snapshot chứa request đầy đủ, phiên bản app/phương pháp/thư viện, nguồn/checksum, lịch hiệu lực và catalog. Ghi JSON qua file tạm/fsync/link; artifact đã đăng ký có checksum và không ghi đè. Run terminal không nhận artifact mới. Nhãn cụm là annotation append-only, không sửa centroid/contribution. Lỗi method ở một ngành-tháng thành ô needs_review và bộ partial; lỗi nguồn mơ hồ chặn run. Huỷ giữ nguyên run hoàn tất trước đó.

Writer lock thuộc project/PID/UUID. Cơ chế tự thu hồi chỉ giới hạn worker do app sở hữu đã kết thúc; khoá từ tiến trình/phiên khác cần xác minh trước khi xoá. Dự án không có đồng bộ hoặc writer cộng tác.

## Di chuyển và sao lưu

Snapshot đường dẫn cũ được giữ làm bằng chứng nguồn. Sao lưu có nguồn thêm `source-locations.json` ánh xạ SHA-256 sang đường dẫn tương đối và manifest kiểm tra các file. Không sửa payload đã chốt để chuyển máy. `request_for_run` phân giải nguồn từ bảng này khi dùng lại cấu hình. Bản không kèm nguồn vẫn xem được kết quả; thiếu nguồn được báo khi xác minh. Không mở database từ vị trí tuỳ ý ngoài workspace qua symlink/path traversal.

## Môi trường Qt

Workspace quản lý hiện tại tự gắn cờ Finder hidden cho file trong `.venv`. Qt loại các plugin này khi quét, làm qapp abort. Bootstrap macOS dùng bản sao **platform plugins từ package PySide6 đang cài** trong TemporaryDirectory do tiến trình sở hữu, không sửa thư viện vendor. Trong cài đặt/bundle bình thường giữ cách tìm plugin mặc định. Qt tests chạy offscreen; runtime smoke dùng Qt Cocoa thật và chụp widget thực.

Python cũng bỏ qua tệp `.pth` bị hidden trong môi trường này. Bản wheel thông thường đã được cài vào `.venv`; chạy source trực tiếp với `PYTHONPATH=src` khi phát triển. Cache Matplotlib mặc định dùng thư mục tạm riêng của ứng dụng và được các worker kế thừa, tránh ghi vào home bị chặn.
