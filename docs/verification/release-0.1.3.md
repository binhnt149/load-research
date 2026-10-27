# Kiểm chứng phát hành 0.1.3

Ngày chuẩn bị: 27/10/2026. Trạng thái: kiểm tra cục bộ đã đạt, đang chờ CI/build và công bố bộ cài.

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

Kết quả local/CI, commit/tag, build hai nền tảng và kiểm tra asset tải lại sẽ
được ghi sau khi thực sự hoàn tất.
