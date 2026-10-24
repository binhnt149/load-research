# Build và kiểm thử Desktop

Gói Python wheel được build/kiểm chứng riêng với bản native không cần Python. Hiện chưa có bộ cài đã xác nhận trên máy người dùng không cài Python; E02 còn mở. Ma trận OS/CPU tối thiểu và ký bộ cài chưa được đơn vị chốt. Đã chạy Cocoa desktop trên macOS 26.4.1/arm64 và source test suite trên CI macOS 15/arm64, Windows Server 2022/x64; chưa xác nhận Mac Intel hoặc Windows desktop sạch.

## Wheel

Từ root dự án, trong venv có dependencies đã khóa:

```bash
python -m build --wheel --no-isolation
```

Wheel không kèm Python/Qt. Muốn cài ngoại tuyến cần chuẩn bị wheelhouse chứa các dependency đúng OS/CPU trước đó.

## Native trên chính hệ điều hành đích

`pysidedeploy.spec` dựa trên template PySide6 6.12.0; công cụ build được khóa trong `requirements-build.txt`. Chạy deploy từ thư mục `packaging` để đường dẫn tương đối trong spec được giải quyết đúng. Build giới hạn 2 compiler job và cho phép Nuitka tải công cụ phụ trợ mà nó yêu cầu; không bỏ qua lỗi/cảnh báo kiểm chứng.

```bash
python -m pip install -r packaging/requirements-build.txt
python -m pip install --no-deps --no-build-isolation .
cd packaging
pyside6-deploy -c pysidedeploy.spec --mode standalone --dry-run --no-install --extra-ignore-dirs=.git,.venv,tests,docs,research-projects,benchmark-data,build,dist
pyside6-deploy -c pysidedeploy.spec --mode standalone --no-install --extra-ignore-dirs=.git,.venv,tests,docs,research-projects,benchmark-data,build,dist
cd ..
```

Kiểm tra lệnh dry-run trước; không dùng `--force` để bỏ qua cảnh báo không hiểu. macOS cần toolchain Xcode; Windows cần Visual Studio với thành phần Clang-cl. Spec dùng `--clang` vì compiler MSVC đã báo C1002 khi tối ưu module SciPy trên runner Windows; macOS vốn sử dụng Clang. Đầu ra dự kiến dưới `dist/native`; kết quả CI được ghi trong [báo cáo Actions](../docs/verification/actions.md). Kiểm tra native CLI trong CI không thay việc xác nhận GUI, plugin, worker multiprocessing và cài/chạy trên máy sạch.

Kiểm tra diff của spec sau dry-run: công cụ có thể tự ghi đường dẫn icon theo máy. Giữ `icon =` trong cấu hình chung để mỗi runner chọn icon phù hợp.

Tài liệu gốc: [Qt pyside6-deploy](https://doc.qt.io/qtforpython-6/deployment/deployment-pyside6-deploy.html), [Nuitka user manual](https://nuitka.net/user-documentation/user-manual.html). Lệnh `pyside6-deploy --help` đã được đối chiếu với bản cài trong workspace.

## Smoke trên bản source và máy sạch

```bash
python packaging/smoke_desktop.py --project research-projects/demo-project --screenshot docs/verification/desktop.png
```

Script mở Qt desktop thực, nạp run thật và chụp widget; `qt_platform=cocoa` xác nhận không dùng offscreen trên macOS. Suite pytest-qt riêng dùng offscreen để lặp lại ổn định.

Trên **từng artifact native và từng máy sạch**: mở không có Python, tạo dự án ở đường dẫn tiếng Việt, nạp demo, chạy/huỷ/chạy lại, xem 24/48 kW/kWh/chuẩn hoá và thành phần, truy vết ngày, đặt nhãn, so run, xuất CSV/XLSX/PNG/SVG, sao lưu, chuyển bản sao lưu sang máy còn lại và xác minh checksum. So fixture trong dung sai của spec. Ghi OS/CPU/build hash/ảnh/log/kết quả; chỉ lúc đó mới đóng E02/AC-23. Việc ký/notarize/installer cần quyết định phân phối riêng; workflow hiện đóng gói chưa ký số và không chứa credential ký.

## GitHub Actions

[Workflow](../.github/workflows/release.yml) dùng Python 3.12, runner `macos-15` (Apple Silicon arm64) và `windows-2022` (x64). Các action được ghim commit SHA. Job kiểm tra/build chỉ có quyền đọc repository; duy nhất job publish có `contents: write`. Không dùng `pull_request_target`, PAT hay secret ký số.

| Sự kiện | Kết quả |
|---|---|
| Push `main` / PR vào `main` | Ruff, mypy, toàn bộ pytest, audit lock và build wheel trên hai OS |
| Actions → Run workflow | Các gate trên cả hai OS; build native theo lựa chọn all/macOS/Windows, smoke demo/xuất, DMG/ZIP; chỉ lưu artifact, không tạo Release |
| Push tag `vX.Y.Z` | Toàn bộ gate/build; kiểm tra đủ asset và báo cáo smoke; SHA256SUMS; tạo GitHub pre-release |

Thứ tự: quality cả hai OS → native cả hai OS → publish. Một gate lỗi sẽ chặn publish. Không bỏ/skip test để phát hành. Lượt full-year benchmark không nằm trong CI; E01/E02/E03 vẫn có điều kiện nghiệm thu riêng.

Compiler cache được tách theo OS/CPU và dependency lock, ghim action cache bằng SHA; lưu sau compile, kể cả khi smoke sau đó lỗi. Cache không thay thế các quality/smoke gate. Spec khai báo rõ NumPy compatibility vendored của SciPy/scikit-learn vì chúng nhập FFT/linalg bằng tên động, backend SVG được Matplotlib nhập khi xuất hình, đồng thời bật `dill-compat` cho cloudpickle.

Để build thử, mở [Actions](https://github.com/binhnt149/load-research/actions/workflows/release.yml), chọn **Run workflow**, nhánh `main`, rồi chọn `platform`: `all`, `macos-arm64` hoặc `windows-x64`. Hai OS vẫn chạy đủ quality gates khi chỉ build một nền tảng. Các lượt thủ công khác lựa chọn nền tảng không huỷ lẫn nhau. Sau khi hoàn tất, tải artifact `release-*` tương ứng trong mục **Artifacts** của lượt chạy; artifact giữ 3 ngày, báo cáo quality giữ 7 ngày. Runner native có timeout 120 phút để có thời gian dự phòng cho compile Windows và đóng gói; thời gian build không phải chỉ tiêu hiệu năng nghiên cứu phụ tải.

Để phát hành phiên bản tiếp theo, ví dụ `0.1.2`:

1. Sửa version đồng nhất trong `pyproject.toml` và `src/load_research/__init__.py`; cập nhật assertion version trong `tests/unit/test_package.py` cùng changelog/ghi chú liên quan.
2. Commit và push `main`, kiểm tra CI đạt.
3. Tạo tag mới trỏ commit đó:

```bash
git tag -a v0.1.2 -m "Release 0.1.2"
git push origin v0.1.2
```

Chỉ đẩy tag khi metadata đã trùng phiên bản đó; nếu khác, workflow sẽ từ chối. Không di chuyển tag đã phát hành. Workflow tạo release mới và không dùng `--clobber`; nếu release cùng tag đã tồn tại, dừng để kiểm tra thay vì thay asset. Lượt thủ công không phát hành lại tag cũ.

Tệp phát hành:

- `LoadResearch-X.Y.Z-macos-arm64.dmg`: chứa `LoadResearch.app` và liên kết Applications; chưa có bản Intel/universal.
- `LoadResearch-X.Y.Z-windows-x64.zip`: giải nén, chạy `LoadResearch.dist/launcher.exe`, giữ nguyên toàn thư mục; đây là bản portable, không phải MSI.
- Python wheel, `requirements.lock`, `requirements-build.txt`, hai `native-smoke-*.json` và `SHA256SUMS`.

Smoke test gọi đúng executable trong bundle từ thư mục tạm ngoài checkout, bỏ `PYTHONPATH/PYTHONHOME/VIRTUAL_ENV`, chạy demo và xuất XLSX/PNG/SVG. Đây là kiểm tra native CLI; chưa thay thế UAT giao diện, kiểm thử worker hoặc chạy trên máy sạch không cài Python. DMG chưa ký Developer ID/notarize, Windows chưa Authenticode. Bản phát hành luôn đánh dấu thử nghiệm cho đến khi có quyết định nghiệm thu/phân phối.

Nếu build/test lỗi, xem log và artifact `checks-*` trong Actions rồi sửa bằng commit mới; không hạ gate. Nếu phát hiện lỗi ở bản đã phát hành, giữ tag/asset để truy vết, sử dụng bản sao lưu dự án và phát hành bản sửa với version mới; không có cập nhật tự động dữ liệu người dùng.

Nguồn: [runner của GitHub](https://docs.github.com/en/actions/reference/runners/github-hosted-runners), [quyền GITHUB_TOKEN](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token), [artifact](https://github.com/actions/upload-artifact).
