# Kiểm chứng GitHub Actions

Ngày: 24/10/2026. Workflow: [CI and desktop release](../../.github/workflows/release.yml).

## Kiểm tra tại máy phát triển

- **152/152 pytest pass**, không fail/error/skip; 20,82 giây sau bản sửa backup Windows.
- Ruff lint/format: pass, 71 file; mypy: pass, 36 module.
- actionlint 1.7.12: pass. Action checkout/setup-python/upload/download được ghim SHA theo release chính thức.
- 17 test mới cho metadata/tag, định vị executable, smoke thật, bộ asset và checksum; 2 regression cho vòng đời SQLite backup.
- Mutation bỏ guard tag: 4 trường hợp tag sai thất bại; khôi phục source hash và xác nhận lại các test này đạt.
- Audit 3 công cụ build đã khóa: không có lỗ hổng đã biết tại thời điểm kiểm tra. Lock runtime/dev tiếp tục được audit trên CI.
- Review độc lập không còn Required/Critical sau sửa cài Nuitka sdist riêng và ràng buộc publish chỉ cho sự kiện push tag.

## Lượt chạy trên GitHub

- [Lượt đầu](https://github.com/binhnt149/load-research/actions/runs/40062536508): macOS đạt; Windows 147 pass, 3 fail cùng nguyên nhân backup giữ connection SQLite đích. Không bỏ test hoặc hạ gate.
- Bản sửa `90edf3b`: đóng connection bằng `contextlib.closing`, giữ transaction context; hai regression thật tái hiện Red trước sửa và Green sau sửa, cả khi công bố backup thất bại.
- [CI xác nhận bản sửa](https://github.com/binhnt149/load-research/actions/runs/40062843834): **success**. JUnit tải lại xác nhận macOS 152/152 pass trong 32,361 giây; Windows 152/152 pass trong 43,869 giây. Cả hai không fail/error/skip; audit 72 dependency mỗi OS không có lỗ hổng đã biết.
- [Lượt native đầu](https://github.com/binhnt149/load-research/actions/runs/40062858984): quality gates cả hai OS đạt; macOS compile xong nhưng smoke phát hiện thiếu `scipy._external.array_api_compat.numpy.fft`. Đã xác minh import động trong NumPy compatibility của SciPy/scikit-learn, bổ sung `--include-package` cho hai package tương ứng và bật `dill-compat` cho cloudpickle. Dừng phần Windows còn đang biên dịch của cấu hình cũ; không công bố artifact chưa đạt.
- Lệnh `pyside6-deploy --dry-run --no-install` với cấu hình sửa và actionlint đạt. Thêm cache compiler theo OS/CPU/dependency lock, lưu trước smoke để không phải biên dịch lại từ đầu sau lỗi đóng gói. Lượt native xác nhận bản sửa sẽ được ghi khi có kết quả.

Lượt thủ công không công bố Release. Tag/release `v0.1.0` được giữ nguyên; chưa tạo tag phiên bản mới. Các test native CLI không thay UAT giao diện trên máy sạch hoặc nghiệm thu dữ liệu thực/quy mô đủ năm (E01/E02/E03).
