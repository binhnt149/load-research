# Kiểm chứng GitHub Actions

Ngày: 24/10/2026. Workflow: [CI and desktop release](../../.github/workflows/release.yml).

## Kiểm tra tại máy phát triển

- **152/152 pytest pass**, không fail/error/skip; lượt cuối 23,25 giây sau khi bổ sung backend SVG trong cấu hình build.
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
- [CI của cấu hình mới](https://github.com/binhnt149/load-research/actions/runs/40066230879): **success** trên cả hai OS. [Lượt build native xác nhận](https://github.com/binhnt149/load-research/actions/runs/40066254619) cũng đã qua quality gates: macOS 152/152 trong 26,385 giây, Windows 152/152 trong 46,841 giây; không fail/error/skip, audit 72 dependency mỗi OS không có lỗ hổng đã biết. Số liệu được đọc lại từ JUnit và báo cáo audit tải từ artifact của lượt chạy.
- Lượt 40066254619 trên macOS đã chạy xong pipeline (`status=completed`) nhưng xuất hình thất bại vì thiếu `matplotlib.backends.backend_svg`. Đã đối chiếu `get_registered_canvas_class` của Matplotlib: backend này được nhập động khi xuất SVG. Bổ sung đúng module bằng `--include-module=matplotlib.backends.backend_svg`; giữ smoke XLSX/PNG/SVG làm gate và dùng lại compiler cache đã lưu thành công.
- Bản sửa SVG `7468340` qua [CI trên hai OS](https://github.com/binhnt149/load-research/actions/runs/40069339165). Dừng lượt native cũ đã lỗi; xác nhận bước `Save compiler cache` của Windows vẫn đạt sau khi huỷ, cache 43.729.142 byte đã được lưu. [Lượt build xác nhận tiếp theo](https://github.com/binhnt149/load-research/actions/runs/40069789873) đang chạy.
- Lượt 40069789873: Windows dừng ở compiler MSVC với C1002 trên `scipy.interpolate._cubic` và `scipy.integrate._lebedev`; chưa chạy native smoke. Cache vẫn lưu thành công. Chuyển cấu hình compiler sang `--clang` (Clang-cl của Visual Studio trên Windows, Clang trên macOS), giữ hai job compiler và bỏ `--quiet` để log có thông tin build. Runner Windows có thành phần Visual Studio Clang theo [danh mục chính thức](https://github.com/actions/runner-images/blob/main/images/windows/Windows2022-Readme.md); phương án compiler được đối chiếu với [Nuitka](https://nuitka.net/user-documentation/common-issue-solutions.html#memory-issues-and-compiler-bugs). Thêm lựa chọn nền tảng cho lượt thủ công để kiểm chứng riêng Windows; tag luôn build cả hai OS.

## Native macOS đã xác nhận

[Job macOS 120801141496](https://github.com/binhnt149/load-research/actions/runs/40069789873/job/120801141496): **success**. Compile từ 06:23:41 đến 07:05:27 UTC; smoke 15 giây đạt, tạo DMG và upload artifact đều đạt. Artifact `release-macos-arm64` có 185.072.902 byte (ZIP vận chuyển của Actions), chứa DMG và báo cáo smoke. Lượt này dùng cấu hình có backend SVG; Clang là compiler mặc định của macOS. Toàn lượt mang trạng thái failure do job MSVC Windows trước khi sửa, không phải job macOS.

[Lượt Windows dùng Clang-cl](https://github.com/binhnt149/load-research/actions/runs/40071949110) tại commit `3a08e4b`, chọn `platform=windows-x64`: quality trên cả hai OS đã đạt; chỉ tạo job native Windows, không huỷ lượt macOS đang chạy. Kết quả native Windows sẽ được ghi khi hoàn tất.

Đã tải artifact macOS: báo cáo smoke ghi `status=passed`, `pipeline_status=completed`, cả XLSX/PNG/SVG đều `true`. DMG có 185.072.390 byte, SHA-256 `02b5d2cb68eb378a9f8cab516dca55d4c232438601efff8ac7ca11f24c2178eb`; `hdiutil verify` trả checksum **VALID**.

Quality của cấu hình `3a08e4b`: macOS 152/152 trong 31,612 giây, Windows 152/152 trong 51,625 giây; không fail/error/skip, audit 72 dependency mỗi OS không có lỗ hổng đã biết. JUnit/audit đã được tải và đọc lại. [CI push main](https://github.com/binhnt149/load-research/actions/runs/40071928270) cũng **success**.

Lượt Windows dùng Clang-cl mất hơn một giờ ở bước build. Tăng timeout native cho các lượt sau từ 90 lên 120 phút để dành thời gian cho compile, smoke, nén ZIP và upload; timeout quality vẫn 25 phút và mọi gate giữ nguyên. Timeout mới không thay đổi lượt 40071949110 đã bắt đầu với cấu hình 90 phút.

Lượt thủ công không công bố Release. Tag/release `v0.1.0` được giữ nguyên; chưa tạo tag phiên bản mới. Các test native CLI không thay UAT giao diện trên máy sạch hoặc nghiệm thu dữ liệu thực/quy mô đủ năm (E01/E02/E03).
