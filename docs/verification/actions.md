# Kiểm chứng GitHub Actions

Ngày: 24/10/2026. Workflow: [CI and desktop release](../../.github/workflows/release.yml).

**Cập nhật phát hành:** [lượt tag v0.1.1 40082527303](https://github.com/binhnt149/load-research/actions/runs/40082527303) đã **success**, gồm quality, hai native job và publish. [Prerelease v0.1.1](https://github.com/binhnt149/load-research/releases/tag/v0.1.1) đã có DMG/ZIP/wheel cùng báo cáo smoke, lock và SHA256SUMS. Xem [kiểm chứng 0.1.1](release-0.1.1.md) cho bằng chứng của cùng lượt tag; phần dưới giữ lịch sử giai đoạn thiết lập workflow.

## Kết quả xác nhận trước đợt phát hành 0.1.1

| Nền tảng | Full suite | Native CLI, xuất báo cáo và đóng gói |
|---|---|---|
| macOS 15 arm64 | 152/152 pass, không skip | [Job thành công](https://github.com/binhnt149/load-research/actions/runs/40069789873/job/120801141496): demo, XLSX/PNG/SVG, DMG và upload |
| Windows Server 2022 x64 | 152/152 pass, không skip | [Lượt thành công](https://github.com/binhnt149/load-research/actions/runs/40071949110): Clang-cl, demo, XLSX/PNG/SVG, ZIP và upload |

Lượt Windows chọn riêng `windows-x64` vẫn chạy quality trên cả hai OS. Job publish được **skipped** đúng thiết kế cho workflow_dispatch; các lượt thủ công không tạo Release.

### Hạn chế tài khoản Actions sau kiểm chứng native (đã khôi phục)

[Lượt push 40076810720](https://github.com/binhnt149/load-research/actions/runs/40076810720) của commit `0d43dda` (timeout/tài liệu) bị GitHub chặn **trước khi khởi động cả hai quality job**, với thông báo tài khoản có payment thất bại hoặc cần tăng spending limit. Không có step hay test nào được thực thi trong lượt đó. E04 được mở khi ấy để theo dõi khả năng chạy job mới. Các kết quả 152/152 test và native smoke ở bảng trên đã hoàn tất trước tình trạng này; mã ứng dụng không đổi trong commit timeout/tài liệu.

**Cập nhật khi tiếp tục release:** chạy lại [40077587587, attempt 2](https://github.com/binhnt149/load-research/actions/runs/40077587587/attempts/2) đã **success** trên cả Windows/macOS với đủ quality gates. E04 đã hoàn tất; không có thay đổi Billing trong repository hoặc qua công cụ. Quá trình chuẩn bị/phát hành `0.1.1` được ghi tiếp tại [báo cáo phiên bản](release-0.1.1.md).

## Kiểm tra tại máy phát triển

- **152/152 pytest pass**, không fail/error/skip; lượt cuối 24,69 giây sau khi GitHub chặn khởi động job mới do Billing. Ruff/mypy/actionlint cũng chạy lại và đạt; không sửa hoặc bỏ test.
- Ruff lint/format: pass, 71 file; mypy: pass, 36 module.
- actionlint 1.7.12: pass. Action checkout/setup-python/upload/download/cache được ghim SHA theo release chính thức.
- 17 test mới cho metadata/tag, định vị executable, smoke thật, bộ asset và checksum; 2 regression cho vòng đời SQLite backup.
- Mutation bỏ guard tag: 4 trường hợp tag sai thất bại; khôi phục source hash và xác nhận lại các test này đạt.
- Audit 3 công cụ build đã khóa: không có lỗ hổng đã biết tại thời điểm kiểm tra. Lock runtime/dev tiếp tục được audit trên CI.
- Review độc lập không còn Required/Critical sau sửa cài Nuitka sdist riêng và ràng buộc publish chỉ cho sự kiện push tag.

## Lượt chạy trên GitHub

- [Lượt đầu](https://github.com/binhnt149/load-research/actions/runs/40062536508): macOS đạt; Windows 147 pass, 3 fail cùng nguyên nhân backup giữ connection SQLite đích. Không bỏ test hoặc hạ gate.
- Bản sửa `90edf3b`: đóng connection bằng `contextlib.closing`, giữ transaction context; hai regression thật tái hiện Red trước sửa và Green sau sửa, cả khi công bố backup thất bại.
- [CI xác nhận bản sửa](https://github.com/binhnt149/load-research/actions/runs/40062843834): **success**. JUnit tải lại xác nhận macOS 152/152 pass trong 32,361 giây; Windows 152/152 pass trong 43,869 giây. Cả hai không fail/error/skip; audit 72 dependency mỗi OS không có lỗ hổng đã biết.
- [Lượt native đầu](https://github.com/binhnt149/load-research/actions/runs/40062858984): quality gates cả hai OS đạt; macOS compile xong nhưng smoke phát hiện thiếu `scipy._external.array_api_compat.numpy.fft`. Đã xác minh import động trong NumPy compatibility của SciPy/scikit-learn, bổ sung `--include-package` cho hai package tương ứng và bật `dill-compat` cho cloudpickle. Dừng phần Windows còn đang biên dịch của cấu hình cũ; không công bố artifact chưa đạt.
- Lệnh `pyside6-deploy --dry-run --no-install` với cấu hình sửa và actionlint đạt. Thêm cache compiler theo OS/CPU/dependency lock, lưu trước smoke; khả năng tái sử dụng còn phụ thuộc compiler và graph import của từng build.
- [CI của cấu hình mới](https://github.com/binhnt149/load-research/actions/runs/40066230879): **success** trên cả hai OS. [Lượt build native xác nhận](https://github.com/binhnt149/load-research/actions/runs/40066254619) cũng đã qua quality gates: macOS 152/152 trong 26,385 giây, Windows 152/152 trong 46,841 giây; không fail/error/skip, audit 72 dependency mỗi OS không có lỗ hổng đã biết. Số liệu được đọc lại từ JUnit và báo cáo audit tải từ artifact của lượt chạy.
- Lượt 40066254619 trên macOS đã chạy xong pipeline (`status=completed`) nhưng xuất hình thất bại vì thiếu `matplotlib.backends.backend_svg`. Đã đối chiếu `get_registered_canvas_class` của Matplotlib: backend này được nhập động khi xuất SVG. Bổ sung đúng module bằng `--include-module=matplotlib.backends.backend_svg`; giữ smoke XLSX/PNG/SVG làm gate và dùng lại compiler cache đã lưu thành công.
- Bản sửa SVG `7468340` qua [CI trên hai OS](https://github.com/binhnt149/load-research/actions/runs/40069339165). Dừng lượt native cũ đã lỗi; xác nhận bước `Save compiler cache` của Windows vẫn đạt sau khi huỷ, cache 43.729.142 byte đã được lưu. [Lượt build xác nhận tiếp theo](https://github.com/binhnt149/load-research/actions/runs/40069789873) đạt trên macOS; Windows lộ lỗi compiler nêu dưới đây.
- Lượt 40069789873: Windows dừng ở compiler MSVC với C1002 trên `scipy.interpolate._cubic` và `scipy.integrate._lebedev`; chưa chạy native smoke. Cache vẫn lưu thành công. Chuyển cấu hình compiler sang `--clang` (Clang-cl của Visual Studio trên Windows, Clang trên macOS), giữ hai job compiler và bỏ `--quiet` để log có thông tin build. Runner Windows có thành phần Visual Studio Clang theo [danh mục chính thức](https://github.com/actions/runner-images/blob/main/images/windows/Windows2022-Readme.md); phương án compiler được đối chiếu với [Nuitka](https://nuitka.net/user-documentation/common-issue-solutions.html#memory-issues-and-compiler-bugs). Thêm lựa chọn nền tảng cho lượt thủ công để kiểm chứng riêng Windows; tag luôn build cả hai OS.

## Native và artifact đã xác nhận

[Job macOS 120801141496](https://github.com/binhnt149/load-research/actions/runs/40069789873/job/120801141496): **success**. Compile từ 06:23:41 đến 07:05:27 UTC; smoke 15 giây đạt, tạo DMG và upload artifact đều đạt. Artifact `release-macos-arm64` có 185.072.902 byte (ZIP vận chuyển của Actions), chứa DMG và báo cáo smoke. Lượt này dùng cấu hình có backend SVG; Clang là compiler mặc định của macOS. Toàn lượt mang trạng thái failure do job MSVC Windows trước khi sửa, không phải job macOS.

[Lượt Windows dùng Clang-cl](https://github.com/binhnt149/load-research/actions/runs/40071949110) tại commit `3a08e4b`, chọn `platform=windows-x64`: **success**; quality trên cả hai OS đạt, chỉ tạo job native Windows, không huỷ lượt macOS đang chạy. Compile từ 06:57:46 đến 08:09:55 UTC; smoke 10 giây, ZIP và upload đều đạt. Log xác nhận compiler `clang-cl`, 2.005 tệp C được biên dịch (0 cache hit trong lượt đổi compiler); cache mới được lưu thành công. Artifact `release-windows-x64` có 174.906.339 byte, digest ZIP vận chuyển `sha256:8025ad8de8bb470b50d7c5ba2e510b9d4d4eabbf326706fb4ef80c4b05923ddb`.

Đã tải artifact macOS: báo cáo smoke ghi `status=passed`, `pipeline_status=completed`, cả XLSX/PNG/SVG đều `true`. DMG có 185.072.390 byte, SHA-256 `02b5d2cb68eb378a9f8cab516dca55d4c232438601efff8ac7ca11f24c2178eb`; `hdiutil verify` trả checksum **VALID**.

Quality của cấu hình `3a08e4b`: macOS 152/152 trong 31,612 giây, Windows 152/152 trong 51,625 giây; không fail/error/skip, audit 72 dependency mỗi OS không có lỗ hổng đã biết. JUnit/audit đã được tải và đọc lại. [CI push main](https://github.com/binhnt149/load-research/actions/runs/40071928270) cũng **success**.

Lượt Windows dùng Clang-cl mất hơn một giờ ở bước build. Tăng timeout native cho các lượt sau từ 90 lên 120 phút để dành thời gian cho compile, smoke, nén ZIP và upload; timeout quality vẫn 25 phút và mọi gate giữ nguyên. Timeout mới không thay đổi lượt 40071949110 đã bắt đầu với cấu hình 90 phút.

macOS được kiểm chứng ở `7468340`, Windows ở `3a08e4b`; khác biệt giữa hai revision nằm ở cấu hình compiler/CI và tài liệu, mã ứng dụng không đổi. Lượt macOS dùng Clang mặc định; cấu hình hiện tại chọn Clang tường minh. Khi push tag, cả hai native job lấy cùng commit và publisher chỉ tải artifact trong chính lượt chạy đó.

Đã tải ZIP Windows: báo cáo smoke ghi `status=passed`, `pipeline_status=completed`, XLSX/PNG/SVG đều `true`. ZIP có 174.905.819 byte, 1.374 entry, chứa `LoadResearch.dist/launcher.exe`; kiểm tra CRC toàn bộ bằng `zipfile.testzip()` đạt. SHA-256: `e30b02583810aa532f49c98fc5fbb5a7e6e3a6beae85f18920081c8a307e90e6`.

Đã thử `release_tools.py assets` với đủ 7 tệp thực: DMG/báo cáo macOS từ lượt 40069789873, ZIP/báo cáo Windows và wheel/lock từ lượt 40071949110. Helper kiểm tra đủ tên tệp, trạng thái smoke và tạo SHA256SUMS; `shasum -a 256 -c` xác nhận **7/7 OK**. [Checksum của bộ asset thử](native-ci-SHA256SUMS) chỉ phục vụ kiểm chứng này, không phải manifest của release `v0.1.0` đã công bố; không tải bộ kết hợp này lên Release.

Review độc lập cuối không có Required/Critical. T27 hoàn tất bằng kiểm tra cục bộ, các lượt hosted đã đạt, kiểm tra artifact và tài liệu; khả năng chạy thêm job của tài khoản được theo dõi riêng ở E04.

Lượt thủ công không công bố Release. Tag/release `v0.1.0` được giữ nguyên; bản tiếp theo `v0.1.1` được phát hành bằng lượt push tag riêng nêu ở đầu báo cáo. Các test native CLI không thay UAT giao diện trên máy sạch hoặc nghiệm thu dữ liệu thực/quy mô đủ năm (E01/E02/E03).
