# Truy vết đặc tả → kiểm thử

| Yêu cầu | Kiểm chứng chính |
|---|---|
| FR-01 dự án/run | unit/workspace, annotations; integration/backup, review_regressions; UI/workflow |
| FR-02 nhập dữ liệu | unit/tables, catalog, metering; integration/store, pipeline, CLI |
| FR-03 ghép/chuẩn hoá | catalog + metering + store: ID chuỗi, hiệu lực, cộng công tơ, duplicate/overlap |
| FR-04 lịch | calendar + UI/calendar editor; năm nhuận, ưu tiên override, snapshot/hash |
| FR-05 VEE/chất lượng | quality + like_days + integration/inspection; flags, ngân sách bù, dữ liệu gốc, gián đoạn |
| FR-06 điều kiện mẫu | profiles; tập chung, số ngày tối thiểu và độ phủ gốc |
| FR-07 biểu đồ/chuẩn hoá | energy, profiles, clustering, scaling; Q/U/V và inactive |
| FR-08 phân cụm | clustering: K/seed/tie/fallback, DBSCAN noise/limit, roundoff; thống kê nhóm |
| FR-09 suy rộng | scaling + pipeline: A/S/alpha, trọng số, loại ngày, zero/missing/partial |
| FR-10 xem/so sánh | UI/results: 24/48, đơn vị, thiếu curve, config/calendar/cohort, worker thực |
| FR-11 xuất | integration/export, charts, jobs: CSV/XLSX, row limit, bộ lọc, manifest, PNG/SVG |
| FR-12 tái lập | workspace + pipeline + backup: snapshot, hash, run mới, cache, ngữ nghĩa nguồn |
| FR-13 tài nguyên/tác vụ | jobs + performance/benchmark: process, cancel/crash, batch, disk preflight/RSS |
| FR-14 desktop hai OS | pytest-qt + Cocoa runtime trên macOS hiện tại; cấu hình native sẵn, **AC-23 còn E02** |

Đối chiếu mã FR theo bảng gốc ở mục 15 của spec; test module được liệt kê theo chức năng. Bằng chứng máy sạch/đầy đủ năm/UAT là điều kiện bên ngoài, không được thay bằng fixture.

| AC | Test/bằng chứng |
|---|---|
| 01–06 | catalog, tables, metering, energy, store |
| 07–08 | quality, like_days, inspection |
| 09–12 | calendar, profiles, energy, clustering |
| 13–17 | scaling, clustering, export; bảng tính tay và bảo toàn năng lượng |
| 18–22 | workspace, annotations, backup, pipeline, jobs, export, review_regressions |
| 23 | **Chưa nghiệm thu**; packaging/README, Cocoa smoke hiện tại chỉ là một phần |
| 24 | **Chưa nghiệm thu đủ năm**; benchmark nhỏ và kiểm tra preflight có số đo riêng |

JUnit Red được giữ cục bộ làm bằng chứng trạng thái trước triển khai/sửa. `final-tests.xml` là lượt cuối triển khai, `release-tests.xml` là lượt kiểm tra trước phát hành; cả hai được bỏ hostname trước khi đưa lên Git. Không cộng các lần chạy để báo tăng số test.
