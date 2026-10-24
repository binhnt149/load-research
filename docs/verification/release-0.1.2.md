# Kiểm chứng phát hành 0.1.2

Ngày: 24/10/2026. Trạng thái: đang chuẩn bị, chưa công bố. T34 chỉ hoàn tất sau khi kiểm tra asset tải lại từ GitHub.

- Phạm vi: giao diện, bộ mẫu CSV/XLSX, xem trước tệp và metadata phiên bản; giữ nguyên phương pháp, schema, dependency lock và quality gates.
- Red: assertion phiên bản `0.1.2` thất bại đúng chênh lệch `0.1.1`/`0.1.2` trước khi cập nhật hai metadata.
- Green local: **188/188 pytest pass** trong 20,76 giây, không fail/error/skip. Ruff lint/format (80 file), mypy (40 module), kiểm tra metadata/tag `v0.1.2` đều đạt.
- Wheel `load_research-0.1.2-py3-none-any.whl` build thành công; CRC, metadata/init `0.1.2` và các module giao diện/template mới có đủ. Audit 72 dependency trong lock: 0 lỗ hổng đã biết.
- Review diff phát hành chỉ đổi metadata/assertion và tài liệu; không hạ quality gate, không sửa lock hoặc phương pháp tính.
- Bằng chứng UI và regression trước phát hành: [ui-inputs.md](ui-inputs.md).

Kết quả local, CI hai OS, native và kiểm tra tải lại sẽ được bổ sung sau từng gate thực tế. E01/E02/E03 giữ nguyên trong [tasks.md](../../tasks.md).
