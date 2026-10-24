# Build và kiểm thử Desktop

Gói Python wheel được build/kiểm chứng riêng với bản native không cần Python. Hiện chưa có bộ cài đã xác nhận trên máy sạch Windows/macOS; E02 còn mở. Ma trận OS/CPU tối thiểu và ký bộ cài chưa được đơn vị chốt. Môi trường đã thực chạy là macOS 26.4.1/arm64, Python 3.12; không suy ra hỗ trợ Intel hoặc Windows từ kết quả đó.

## Wheel

Từ root dự án, trong venv có dependencies đã khóa:

```bash
python -m build --wheel --no-isolation
```

Wheel không kèm Python/Qt. Muốn cài ngoại tuyến cần chuẩn bị wheelhouse chứa các dependency đúng OS/CPU trước đó.

## Native trên chính hệ điều hành đích

`pysidedeploy.spec` dựa trên template của PySide6 6.12.0 đang cài. Phiên bản Nuitka đề xuất từ template là 4.1.1, chưa cài/chạy compiler trong phiên này; cần khóa cả phụ thuộc build theo từng OS trước phát hành.

```bash
python -m pip install Nuitka==4.1.1
pyside6-deploy -c packaging/pysidedeploy.spec --mode standalone --dry-run --no-install --extra-ignore-dirs=.venv,tests,docs,research-projects,benchmark-data,build,dist
pyside6-deploy -c packaging/pysidedeploy.spec --mode standalone --no-install --extra-ignore-dirs=.venv,tests,docs,research-projects,benchmark-data,build,dist
```

Kiểm tra lệnh dry-run trước; không dùng `--force` để bỏ qua cảnh báo không hiểu. macOS cần toolchain Xcode; Windows cần compiler tương thích Nuitka. Đầu ra dự kiến dưới `dist/native`; đây là cấu hình chuẩn bị, **chưa phải build native đã pass**. Xác nhận đường plugin, gói dữ liệu Matplotlib/scikit-learn, multiprocessing spawn và metadata phiên bản bằng smoke test trên artifact thực.

Tài liệu gốc: [Qt pyside6-deploy](https://doc.qt.io/qtforpython-6/deployment/deployment-pyside6-deploy.html), [Nuitka user manual](https://nuitka.net/user-documentation/user-manual.html). Lệnh `pyside6-deploy --help` đã được đối chiếu với bản cài trong workspace.

## Smoke trên bản source và máy sạch

```bash
python packaging/smoke_desktop.py --project research-projects/demo-project --screenshot docs/verification/desktop.png
```

Script mở Qt desktop thực, nạp run thật và chụp widget; `qt_platform=cocoa` xác nhận không dùng offscreen trên macOS. Suite pytest-qt riêng dùng offscreen để lặp lại ổn định.

Trên **từng artifact native và từng máy sạch**: mở không có Python, tạo dự án ở đường dẫn tiếng Việt, nạp demo, chạy/huỷ/chạy lại, xem 24/48 kW/kWh/chuẩn hoá và thành phần, truy vết ngày, đặt nhãn, so run, xuất CSV/XLSX/PNG/SVG, sao lưu, chuyển bản sao lưu sang máy còn lại và xác minh checksum. So fixture trong dung sai của spec. Ghi OS/CPU/build hash/ảnh/log/kết quả; chỉ lúc đó mới đóng E02/AC-23. Việc ký/notarize/installer cần quyết định phân phối riêng, không có credential hay quy trình phát hành tự động trong repo.
