# Rà soát chất lượng và bảo mật

Ngày: 24/10/2026. Phạm vi: source, tests, pipeline khoa học, desktop, nhập/xuất, workspace/backup và dependencies của v0.1. Có review độc lập chỉ đọc bằng model khác theo skill code-review-and-quality; các finding được tái hiện bằng test trước khi sửa.

## Finding đã xử lý

| Finding Required | Hành vi sau sửa | Bằng chứng |
|---|---|---|
| MDMS bỏ qua unit/direction/khoảng start–end mâu thuẫn | Kiểm tra ngữ nghĩa từng dòng với khai báo nguồn; cách ly có nguyên nhân | `test_metering.py`, T23-review-red/green |
| Nguồn đổi sau snapshot vẫn được tính với hash cũ | Xác minh trước nhập, trước công bố cache và trước kết quả | `test_pipeline.py`, thử đổi tại started/import |
| Lỗi clustering một ô làm mất toàn lô | Ô needs_review kèm error/action; tiếp tục các ô khác, run partial | test hai ngành trong `test_pipeline.py` |
| Chọn K theo tie tuần tự lệch maximum | So toàn bộ điểm hợp lệ trước khi chọn K nhỏ trong dung sai | `test_clustering.py`, chuỗi 0.260/0.275/0.285 |
| Hàng wide lỗi giữ tiền tố rồi bỏ phần sau | Commit nguyên hàng tối đa 96 chu kỳ; lỗi loại cả hàng, ghi source_slot | `test_metering.py` |
| Xuất Quality mất cột chỉ có ở tháng sau | Hợp đầy đủ tên cột, không lấy schema từ hàng đầu | `test_export.py` |
| Xuất thành viên không áp bộ lọc ngày/nhóm | Áp cùng selection vào members; chất lượng tháng có metadata phạm vi riêng | `test_export.py` |
| Backup Windows không tái chạy trên host macOS | Tra cứu chuỗi đường dẫn nguyên gốc trước khi diễn giải theo host; nguồn nhúng theo SHA | `test_review_regressions.py` |
| Worker crash trước close để khoá/running vĩnh viễn | Thu hồi đúng khoá thuộc worker đã chết, trạng thái failed/cancelled; close idempotent | child `os._exit(7)` trong `test_review_regressions.py` |

Review độc lập không phát hiện Critical. Các Required trên đã sửa và có regression. Những sửa bổ sung từ kiểm tra nội bộ: đếm hình dạng tương đương ở 12 chữ số để không phân nhóm sai số máy; giữ vector đầy đủ khi fit/tổng hợp; ngăn artifact mới vào run terminal; bổ sung tham số donor/MAD; đối soát CMIS có cơ sở kỳ; giữ lịch/ngữ nghĩa nguồn trong báo cáo; chặn bù qua gián đoạn đã biết; xử lý so sánh khi thiếu curve và khác lịch; ghi actor/thời điểm/config hash vào nhật ký bù.

## Đơn giản hoá và hiệu năng

- Dùng chung hàm chuyển kWh/độ phân giải cho UI và bảng/hình; không duy trì một công thức riêng trong UI.
- Annotation tên nhóm được áp qua một helper; không sửa lại artifact số để đặt nhãn.
- Xuất long bằng iterator, Excel constant-memory; bộ xem nguồn giữ tối đa 50 dòng, bảng UI dùng model thay vì widget từng ô.
- Một registry điều khiển tham số số trong form, một pipeline cho CLI/desktop, một cơ chế worker/cancel cho các tác vụ.
- Canonical trên đĩa/batch, dựng customer-month lần lượt; seed, thread cap và silhouette sample được chốt theo run. Chi phí checksum/validate cache toàn phần vẫn cần đo đủ năm trước khi tối ưu tiếp.

## Kiểm tra bảo mật

| Ranh giới | Biện pháp/kiểm chứng |
|---|---|
| Input không tin cậy | Định dạng/ánh xạ/kiểu số/đơn vị/kỳ/phạm vi/hiệu lực có validation; không eval/pickle/macro; XLSX thiếu cached formula và ZIP expansion bất thường bị từ chối |
| SQL/filesystem | SQL tham số hoá; không nhận SQL từ cấu hình; DuckDB tắt external access/extension tự tải; đường artifact/cache nằm trong workspace; kiểm thử traversal/symlink |
| Bất biến/độ toàn vẹn | Hash nguồn/cache/journal/artifact; writer owner; ghi tạm rồi đăng ký; kết quả cũ giữ được sau huỷ; source thay đổi không được coi là cùng nguồn |
| Bảng/hình xuất | CSV chống formula injection; XLSX tắt auto-formula/URL; không cắt vượt row limit; filename hình dựa hash; Matplotlib không diễn giải tên nhóm như math |
| Quyền riêng tư | Xử lý tại máy, không có telemetry/upload/API mạng trong app; thành viên chỉ xuất khi chọn; request xuất rút đường dẫn nguồn về tên tệp, kể cả đường dẫn từ OS khác |
| Dependencies | Audit **72 package** trong lock bằng PyPI: **0 vulnerability đã biết** tại thời điểm kiểm tra; xem `verification/dependency-audit.json`. Native build dependencies tương lai chưa được audit/khóa theo OS |

Ứng dụng không có cơ chế đăng nhập hay mã hoá dữ liệu tại chỗ; phạm vi là một người dùng trên máy cá nhân với quyền thư mục của OS. Audit dependency là kiểm tra lỗ hổng đã biết, không phải chứng nhận không có lỗi. Lock hiện khóa phiên bản, chưa có hash cho toàn bộ wheel theo từng OS; việc xác nhận chuỗi build native còn thuộc E02.

## Mutation và giới hạn bằng chứng

Đã cố ý đổi `alpha=A/S` thành `alpha=1`: test bảo toàn năng lượng thất bại, sau đó khôi phục đúng source hash và chạy lại toàn suite. Bằng chứng: `verification/mutation.json` và XML. Không bỏ test, skip/xfail hoặc giảm ngưỡng để đạt Green.

Qt offscreen và Qt Cocoa thực đã chạy với kết quả demo. Python wheel build/install smoke là kiểm tra gói Python, không thay AC-23 bộ cài máy sạch. Tệp CMIS/MDMS thực, Windows/máy sạch và UAT chưa có; benchmark đủ năm chưa chạy qua preflight dung lượng. Những việc đó giữ mở trong `tasks.md`; không dùng tỷ lệ test pass để tuyên bố tất cả AC đã nghiệm thu.
