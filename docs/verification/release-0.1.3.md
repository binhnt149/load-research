# Kiểm chứng phát hành 0.1.3

Ngày kiểm chứng: 27/10/2026. Trạng thái: [prerelease v0.1.3](https://github.com/binhnt149/load-research/releases/tag/v0.1.3) đã công bố lúc 22:52:36 giờ Việt Nam; tải lại và xác minh asset đạt. T59/T60 hoàn tất.

- Phạm vi: phát hành cả các nâng cấp Kết quả sau v0.1.2, gồm khoảng ngày,
  danh mục thành phần và khách hàng trước/sau VEE.
- Giữ nguyên phương pháp, dependency lock và quality gates. Chỉnh sửa README
  có sẵn của người dùng được giữ riêng, không đưa vào commit phát hành.
- Bằng chứng tính năng trước phát hành: [Kết quả](results-upgrade.md),
  [khoảng ngày/khách hàng](results-range.md).
- E01/E02/E03 giữ điều kiện nghiệm thu riêng; native smoke không thay UAT.

- Red: assertion `0.1.3` thất bại đúng chênh lệch `0.1.2`/`0.1.3` trước khi đổi metadata.
- Green local: **331/331 pass**, 39,06 giây, không fail/error/skip; Ruff lint/format và mypy 59 module đạt.
- Wheel 0.1.3 build đạt, CRC/metadata/init đúng phiên bản, 59/59 module khớp source.
- `release_tools.py version --tag v0.1.3` đạt. Rà soát diff chuẩn bị chỉ đổi phiên bản/assertion, ghi chú và tài liệu; không hạ gate hoặc sửa lock/phương pháp.

- Commit phát hành `8180a73c783944faa60d06c1b58d035e54e1c4e4`.
  [CI main 40524442150](https://github.com/binhnt149/load-research/actions/runs/40524442150)
  success: macOS **331/331**, 81,867 giây; Windows **331/331**, 67,651 giây;
  không fail/error/skip, audit mỗi OS 0 lỗ hổng đã biết. JUnit/audit đã tải lại.
- Tag annotated `v0.1.3` trỏ đúng commit trên.
  [Lượt tag 40525028257](https://github.com/binhnt149/load-research/actions/runs/40525028257)
  có cả hai quality job success: macOS **331/331**, 90,850 giây; Windows
  **331/331**, 105,860 giây; không fail/error/skip. Audit 72 dependency mỗi OS:
  0 lỗ hổng đã biết. JUnit/audit đã tải lại, Ruff/mypy/wheel/tag gates đều đạt.

- [Native macOS 122264359205](https://github.com/binhnt149/load-research/actions/runs/40525028257/job/122264359205)
  success, 12 phút 10 giây: audit build tools, compile, native demo/XLSX/PNG/SVG,
  tạo DMG và upload artifact đều đạt.

- [Native Windows 122264357094](https://github.com/binhnt149/load-research/actions/runs/40525028257/job/122264357094)
  success, 57 phút 48 giây: audit build tools, compile, native demo/XLSX/PNG/SVG,
  kiểm tra không tạo console, tạo ZIP và upload đều đạt. Báo cáo console tải lại
  xác nhận đối chứng dương đạt, tiến trình còn chạy và không có console đính kèm.
- [Publish 122298595854](https://github.com/binhnt149/load-research/actions/runs/40525028257/job/122298595854)
  success, 29 giây. Release không phải draft, có cờ prerelease và đủ 8 asset từ
  chính lượt tag này; không dùng lại bộ cài của phiên bản trước. Toàn lượt tag success.

- Đã tải đủ 8 asset từ GitHub Release. SHA-256 **7/7 khớp manifest**, digest API
  **8/8 khớp**, bao gồm chính `SHA256SUMS`. [Manifest đã phát hành](../releases/v0.1.3-SHA256SUMS)
  giữ nguyên byte; [báo cáo kiểm tra](release-0.1.3-checks.json) không chứa đường dẫn máy cá nhân.
- DMG có **185.579.989 byte**, `hdiutil verify` đạt. Windows ZIP có **175.328.762
  byte**, 1.374 entry, CRC toàn bộ đạt; có đúng `LoadResearch.dist/launcher.exe`,
  không có đường dẫn tuyệt đối hoặc traversal.
- Wheel có **146.762 byte**, CRC/metadata `0.1.3` đạt; **59/59 module khớp byte với
  tag**. Metadata không chứa phần README chưa commit của người dùng. Hai lock
  tải về khớp byte với commit phát hành.
- Hai báo cáo native tải lại đều có `status=passed`, `pipeline_status=completed`
  và XLSX/PNG/SVG `true`. Không hạ gate, bỏ test, đổi tag hoặc thay asset để phát hành.

E01/E02/E03 tiếp tục mở trong [tasks.md](../../tasks.md). Source và bộ cài thuộc
tag `v0.1.3` bất biến; cập nhật báo cáo sau phát hành chỉ thay tài liệu trên main.
