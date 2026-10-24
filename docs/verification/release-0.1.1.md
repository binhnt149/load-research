# Kiểm chứng phát hành 0.1.1

Ngày: 24/10/2026. Trạng thái: đang chuẩn bị bản thử nghiệm, chưa tạo tag.

- Chạy lại quality của commit `8237c93`: [lượt 40077587587, attempt 2](https://github.com/binhnt149/load-research/actions/runs/40077587587/attempts/2) **success**. macOS đạt trong 1 phút 29 giây, Windows trong 3 phút 46 giây; test/lint/type/audit/build đều đạt. E04 được đóng bằng bằng chứng này, không thay đổi thiết lập Billing.
- Baseline tại máy phát triển: 152/152 pytest pass, không skip, trong 20,93 giây.
- Red: đổi assertion phiên bản thành `0.1.1` trước khi sửa metadata; test thất bại đúng chênh lệch `0.1.0`/`0.1.1`. Sau đó cập nhật đồng nhất `pyproject.toml` và package init; giữ nguyên `METHOD_VERSION`.
- Green: toàn bộ **152/152 pytest pass** trong 20,77 giây; JUnit không fail/error/skip. Ruff lint/format (71 file), mypy (36 module), kiểm tra metadata/tag `v0.1.1` đều đạt. Wheel `load_research-0.1.1-py3-none-any.whl` build thành công; metadata/init cùng ghi `0.1.1`, CRC archive đạt.
- Review diff chỉ đổi metadata/assertion phiên bản và tài liệu; không sửa phương pháp, schema, dependency lock hoặc hạ gate. Không có Required/Critical.
- Chờ CI trên main, sau đó mới đẩy tag và xác nhận native/publish/checksum của cùng lượt tag. Không sử dụng lại asset của bản `0.1.0`.

E01/E02/E03 giữ nguyên điều kiện nghiệm thu trong [tasks.md](../../tasks.md). Xem [ghi chú phát hành](../releases/v0.1.1.md) để biết cách chạy thử và khôi phục từ bản sao lưu.
