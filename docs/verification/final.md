# Kiểm chứng cuối — Load Research v0.1.0

Hoàn tất các task triển khai/kiểm chứng khả dụng trong môi trường hiện tại; **E01/E02/E03 vẫn mở**, chưa tuyên bố nghiệm thu toàn bộ AC-01…AC-24.

## Kết quả kiểm tra

| Kiểm tra | Kết quả | Bằng chứng |
|---|---|---|
| Toàn bộ pytest, gồm unit/integration/UI/performance giới hạn | **133/133 pass**, 0 fail/error/skip/xfail; lượt triển khai 15.76 giây, trước phát hành 17.16 giây | [JUnit triển khai](final-tests.xml), [JUnit phát hành](release-tests.xml) |
| Ruff lint + format | Pass; 69 file được kiểm tra định dạng | [static-checks.json](static-checks.json) |
| mypy | Pass, 36 module source | [static-checks.json](static-checks.json) |
| Mutation | Alpha sai bị test bắt; source được khôi phục trước suite cuối | [mutation.json](mutation.json) |
| Dependency audit | 72 package trong lock, 0 vulnerability đã biết | [dependency-audit.json](dependency-audit.json) |
| Wheel phát hành | Build thành công; cài/import ở thư mục tạm và `.venv`; 36 file source khớp wheel; chạy CLI demo/xuất XLSX/PNG/SVG | [integrity](release-package.json), [smoke](release-smoke.json) |
| Qt desktop thật | Cocoa, mở run demo thật, bảng 48 chu kỳ; 3/3 nguồn xác minh | Ảnh và log gốc được giữ cục bộ vì có đường dẫn máy cá nhân |
| Timezone trên môi trường không có IANA database của OS | Pass qua tzdata trong dependencies; cấu hình native giữ package/data này | `test_timezone_data_is_available_without_an_os_timezone_database` |
| Đường dẫn Windows chuyển host | Pass cả dấu `\` và `/`/khác chữ hoa; đây là fixture trên macOS, không thay máy Windows | `test_review_regressions.py` |

Wheel phát hành: `load_research-0.1.0-py3-none-any.whl`. SHA-256: `449fe27d90598243f202b23e12c6b8e06d870a21ae96cd1441e42e554cf4559c`. Gói này bổ sung README và URL repository vào metadata; mã của 36 module khớp source đã kiểm chứng.

Các XML Red/Green trước đó là lịch sử TDD; một số chứa failure có chủ đích trước triển khai hoặc lỗi đã sửa. Lịch sử thô và log được giữ cục bộ. Hai JUnit cuối được bỏ hostname trước khi đưa lên Git; không thay đổi kết quả kiểm thử và không cộng dồn các lần chạy để tăng số test.

## Benchmark 7.000 khách hàng × 1 tháng

[Báo cáo JSON gốc](benchmark-7000x1.json). Máy: macOS 26.4.1, arm64, 10 logical CPU, 16 GiB RAM; Python 3.12.14. Cấu hình synthetic có hai ngành, native 30 phút, nguồn Parquet wide; pipeline/query memory 512 MB, 2 luồng. Đo CLI trên cùng pipeline dùng cho Desktop; không có worker con chứa dữ liệu trong lượt này. RSS/disk peak lấy mẫu mỗi 100 ms.

| Chỉ số đo thật | Giá trị |
|---|---|
| Khách hàng/tháng/giá trị chuẩn | 7.000 / tháng 01-2025 / 10.416.000 |
| Sinh nguồn synthetic | 3.190 giây |
| Xử lý và xuất bảng | **565.675 giây** |
| Tổng thời gian | 568.865 giây |
| RSS đỉnh | **0.960 GiB** (1,031,176,192 bytes) |
| Disk đỉnh lấy mẫu | 2.300 GiB |
| Disk giữ lại sau hoàn tất | 110.690 MiB |
| Sai lệch cân bằng lớn nhất | 1.19209289551e-07 kWh, trong dung sai spec |
| Kết quả | completed; 2 ô ngành-tháng valid; raw canonical count = 10.416.000 |

Lượt này chứng minh xử lý tập 7.000 khách hàng của **một tháng**; không suy ra thời gian/RAM/disk đủ năm từ nó. [Lượt 100 khách hàng](benchmark-100x1.json) là số đo checkpoint nhỏ trước đó, không phải nghiệm thu AC-24.

## Điều chưa nghiệm thu

- **E01:** chưa nhận tệp CMIS/MDMS thực và hồ sơ ngữ nghĩa/chọn mẫu của đơn vị; cần xác nhận adapter, scope/kỳ/hệ số và UAT.
- **E02 / AC-23:** chưa build/chạy bộ cài không cần Python trên máy sạch Windows và macOS/CPU đã chốt. Wheel và Cocoa source runtime không thay điều kiện này; [hướng dẫn native](../../packaging/README.md) ghi rõ phần chuẩn bị chưa chạy.
- **E03 / AC-24:** lượt đủ 7.000 × 365 × 48 bị chặn ở preflight trước sinh dữ liệu. Ước tính cần 29.70 GB trống, tại thời điểm kiểm tra có 26.85 GB. Đây là dự toán dung lượng bảo vệ máy, không phải số đo full-size. [Báo cáo preflight](benchmark-7000x12-preflight.json). Mốc 120 phút/10 GiB RSS và UAT chưa được nghiệm thu.

## Chạy và kiểm tra lại

Theo hướng dẫn [README](../../README.md) hoặc cài wheel từ [release v0.1.0](https://github.com/binhnt149/load-research/releases/tag/v0.1.0). Trong workspace triển khai, `.venv` đã cài wheel vì cơ chế hidden của môi trường làm Python bỏ qua `.pth` editable; muốn chạy source đang sửa dùng `PYTHONPATH=src .venv/bin/python -m load_research`.

Demo có thể sinh theo README. Trong workspace triển khai đã có `research-projects/demo-input`, `research-projects/demo-project`, `research-projects/demo-report`; các thư mục này được ignore. Repository và gói phát hành không kèm dữ liệu nghiên cứu, database hay cache.

Chi tiết [review](../review.md), [truy vết spec](../traceability.md), [kiến trúc](../architecture.md), [task checklist](../../tasks.md). Repository phát hành: [binhnt149/load-research](https://github.com/binhnt149/load-research). Tag `v0.1.0` dành cho bản thử nghiệm; E01/E02/E03 vẫn mở.
