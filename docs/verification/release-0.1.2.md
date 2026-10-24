# Kiểm chứng phát hành 0.1.2

Ngày kiểm chứng: 25/10/2026 (giờ Việt Nam). Trạng thái: [prerelease v0.1.2](https://github.com/binhnt149/load-research/releases/tag/v0.1.2) đã công bố lúc 00:51:17; tải lại và kiểm tra asset đạt. T34 hoàn tất.

- Phạm vi: giao diện, bộ mẫu CSV/XLSX, xem trước tệp và metadata phiên bản; giữ nguyên phương pháp, schema, dependency lock và quality gates.
- Red: assertion phiên bản `0.1.2` thất bại đúng chênh lệch `0.1.1`/`0.1.2` trước khi cập nhật hai metadata.
- Green local: **188/188 pytest pass** trong 20,76 giây, không fail/error/skip. Ruff lint/format (80 file), mypy (40 module), kiểm tra metadata/tag `v0.1.2` đều đạt.
- Wheel `load_research-0.1.2-py3-none-any.whl` build thành công; CRC, metadata/init `0.1.2` và các module giao diện/template mới có đủ. Audit 72 dependency trong lock: 0 lỗ hổng đã biết.
- Review diff phát hành chỉ đổi metadata/assertion và tài liệu; không hạ quality gate, không sửa lock hoặc phương pháp tính.
- Bằng chứng UI và regression trước phát hành: [ui-inputs.md](ui-inputs.md).
- Commit phát hành: `3f976534b94d1e6b78c96509ac58cceaa294d574`. [CI main 40113846581](https://github.com/binhnt149/load-research/actions/runs/40113846581) **success**; JUnit tải lại xác nhận macOS **188/188** trong 49,485 giây, Windows **188/188** trong 47,283 giây, không fail/error/skip. Audit 72 dependency trên mỗi OS: 0 lỗ hổng đã biết.
- Tag annotated `v0.1.2` trỏ đúng commit trên. [Lượt release 40114142117](https://github.com/binhnt149/load-research/actions/runs/40114142117) đã đạt cả hai quality gate. JUnit tải lại: macOS **188/188** trong 47,666 giây, Windows **188/188** trong 53,753 giây, không fail/error/skip. Audit 72 dependency trên mỗi OS: 0 lỗ hổng đã biết. Toàn lượt tag **success**, gồm quality hai OS, native hai OS và publish.
- [Native macOS 120932484974](https://github.com/binhnt149/load-research/actions/runs/40114142117/job/120932484974) **success** trong 9 phút 45 giây; compile, native smoke và tạo/upload DMG đều đạt.
- [Native Windows 120932484953](https://github.com/binhnt149/load-research/actions/runs/40114142117/job/120932484953) **success** trong 47 phút 28 giây; audit công cụ build, compile, native smoke và tạo/upload ZIP đều đạt.
- [Publish 120943180904](https://github.com/binhnt149/load-research/actions/runs/40114142117/job/120943180904) **success**. Release `v0.1.2` không phải draft, có cờ prerelease và đủ 8 asset từ chính lượt tag này; không dùng lại asset của bản cũ.

- Đã tải đủ 8 asset từ GitHub Release. SHA-256 **7/7 khớp manifest**; digest API của cả 8 tệp đều khớp, gồm chính `SHA256SUMS` (`76c9a7bc42453d3e039291e66df03872ccade2550ff64da9d219a5e2ce3fd58a`). [Bản sao manifest đã phát hành](../releases/v0.1.2-SHA256SUMS) giữ nguyên byte để đối chiếu.
- DMG có 185.166.025 byte; `hdiutil verify` xác nhận checksum **VALID**. ZIP Windows có 174.975.332 byte, 1.374 entry, đúng `LoadResearch.dist/launcher.exe`, không có đường dẫn tuyệt đối/traversal; CRC toàn bộ đạt. Wheel có 94.578 byte, metadata/init `0.1.2`, CRC đạt và đủ module theme/preview/template.
- Hai báo cáo native đều có `status=passed`, `pipeline_status=completed`, XLSX/PNG/SVG `true`. Hai lock tải về khớp byte với commit phát hành. Không hạ gate, bỏ test, đổi tag hoặc thay asset để phát hành.

E01/E02/E03 giữ nguyên trong [tasks.md](../../tasks.md).
