# Load Research Desktop

Ứng dụng nghiên cứu phụ tải cục bộ theo **ngành × năm-tháng × loại ngày**, từ tập mẫu đã chốt. Có biểu đồ chung, thành phần hành vi, chuẩn hoá Q/U/V, suy rộng theo thương phẩm và xuất 24/48 chu kỳ bằng kW/kWh. Ứng dụng không gửi dữ liệu lên mạng.

Đặc tả: [load-research.md](load-research.md). Tiến độ và nghiệm thu: [tasks.md](tasks.md). Kết quả kiểm chứng bản hiện tại: [release 0.1.1](docs/verification/release-0.1.1.md).

## Bản phát hành 0.1.1

[GitHub Release v0.1.1](https://github.com/binhnt149/load-research/releases/tag/v0.1.1) đã cung cấp DMG macOS Apple Silicon, ZIP portable Windows x64 và Python wheel. Workflow tag đạt mọi quality/native/publish gate. Xem [ghi chú và cách cài đặt](docs/releases/v0.1.1.md), [changelog](CHANGELOG.md). Đây là bản **thử nghiệm**, các gói native chưa ký số; UAT trên máy sạch vẫn thuộc E02.

## Giao diện và tệp mẫu trong mã nguồn hiện tại

Tab **Dữ liệu** có bốn nhóm nguồn trong hai cột, font hệ thống lớn hơn và màu nhấn xanh. Tên tệp hiển thị ngắn gọn; di chuột để xem đường dẫn đầy đủ. Phần sheet/dấu phân cách/ánh xạ CMIS, thương phẩm và lịch nằm trong **Thiết lập cột & định dạng…**.

Mỗi nhóm có **Tệp mẫu…** để xem ví dụ, hướng dẫn từng cột và lưu CSV/XLSX. Có mẫu CMIS, MDMS dài/rộng 24/48/96, thương phẩm và lịch; xem [bộ mẫu và lưu ý](templates/README.md). Thay toàn bộ dữ liệu minh hoạ bằng dữ liệu thực trước khi nghiên cứu.

Sau **Thêm tệp…**, tệp mới được chọn sẵn. Bấm **Xem trước…** hoặc double-click để xem tối đa 50 dòng đầu; có chọn sheet Excel, đổi dấu phân cách CSV và **Đọc lại**. Các thiết lập tại đây chỉ dùng để xem, cần khai báo tương ứng cho nguồn trước khi chạy. Hộp xem trước báo lỗi rõ, hỗ trợ tệp chỉ có tiêu đề và giữ nguyên mã có số 0 đầu.

Ảnh và kết quả kiểm chứng: [giao diện/đầu vào](docs/verification/ui-inputs.md).

## Chạy từ mã nguồn

Dùng Python **3.12** và thư mục dự án có quyền ghi. Các phiên bản trong `requirements.lock` đã qua CI trên Windows x64 và macOS Apple Silicon. Việc cài/chạy bản native trên máy người dùng không có Python vẫn cần xác nhận E02; xem [bằng chứng CI](docs/verification/actions.md).

macOS:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install --no-deps --no-build-isolation -e .
python -m load_research
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.lock
.venv\Scripts\python -m pip install --no-deps --no-build-isolation -e .
.venv\Scripts\python -m load_research
```

Nếu môi trường quản lý máy không nạp được editable install qua `.pth`, có thể cài wheel hoặc chạy trực tiếp source bằng `PYTHONPATH=src .venv/bin/python -m load_research` trên macOS. Pytest đã cấu hình `pythonpath=src`.

## Demo có thể kiểm tra lại

```bash
python -m load_research demo --output research-projects/demo-input
python -m load_research run --request research-projects/demo-input/request.json --project research-projects/demo-project --export research-projects/demo-report --charts png svg
```

Demo gồm 60 khách hàng tổng hợp, hai ngành và hai hình dạng vận hành trong tháng 02/2024; không chứa khách hàng thật. Thư mục đích phải chưa tồn tại. Lệnh trả JSON kết quả trên stdout, tiến độ trên stderr. Chạy lại cùng request/project tạo run mới và dùng lại cache hợp lệ; chọn tên thư mục xuất mới để giữ báo cáo cũ.

Trong GUI: mở `demo-project` để xem lịch sử, hoặc tạo thư mục dự án trống rồi nạp `demo-input/request.json`. Các đường dẫn tương đối trong request được tính từ thư mục chứa request. Cấu hình ghi từ GUI lưu đủ ngữ nghĩa nguồn đã khai báo.

## Quy trình sử dụng

1. Tạo/mở dự án, chọn CMIS mẫu, MDMS và tổng thương phẩm toàn ngành. Xem trước nguồn, ánh xạ cột và khai báo ngữ nghĩa **từng tệp MDMS**.
2. Nhập/chỉnh lịch; không tích hợp sẵn lịch lễ hằng năm chưa xác nhận. Tệp lịch áp sau các override trên giao diện.
3. Chọn tháng, phạm vi, độ phân giải và tham số VEE/phân cụm. Có công thức và khôi phục mặc định đề xuất.
4. Chạy nghiên cứu trong worker process; có tiến độ và huỷ. Xem trạng thái từng ô, độ phủ, phần ước lượng/không biết chất lượng, khách hàng bị loại và nhóm hành vi.
5. Lọc ngành/tháng/loại ngày/nhóm; xem chung/thành phần, kW/kWh, Q/U/V, 24/48 chu kỳ. Đặt tên nhóm kèm lý do; nhãn được ghi riêng theo lịch sử, giữ nguyên kết quả số.
6. Chọn “Xem dữ liệu ngày / bù…” để xem trước/sau xử lý, phương pháp và ngày nguồn. “Lịch sử” hỗ trợ so hai run cùng phạm vi, thay đổi cấu hình và thành phần mẫu.
7. Xuất lựa chọn/toàn run: CSV luôn có; XLSX, PNG/SVG, bảng thành viên tuỳ chọn. Chất lượng được ghi rõ là toàn tháng; manifest phân biệt ô thiếu/xem thử và phạm vi bộ lọc.
8. Sao lưu từ nút “Sao lưu…”. Có thể lưu kèm nguồn ngoài dự án; mở thư mục sao lưu như dự án thông thường. Không sửa snapshot run để di chuyển nguồn: bảng vị trí theo checksum giữ liên kết tương đối.

## Hợp đồng đầu vào

Chi tiết và ví dụ: [docs/input-formats.md](docs/input-formats.md). Hỗ trợ CSV UTF-8, XLSX có giá trị đã tính, Parquet. Không thực thi công thức Excel/macro hoặc cấu hình như mã.

| Nguồn | Cột tối thiểu theo tên chuẩn |
|---|---|
| CMIS mẫu | `customer_id,industry_code,meter_id` hoặc `measurement_point_id` |
| MDMS dài | `meter_id,timestamp,value` |
| MDMS rộng | `meter_id,date,slot_01,…,slot_48` (15 phút: 96; 60 phút: 24) |
| Tổng thương phẩm | `industry_code,year_month,billing_energy,unit,billing_basis` |
| Lịch tuỳ chọn | `date,day_type` |

Giữ mã có số 0 đầu bằng kiểu chuỗi ngay từ nguồn; không khôi phục được số 0 đã mất trong Excel số. Chưa có tệp thực để xác nhận adapter CMIS/MDMS của đơn vị (E01).

## Phương pháp và giới hạn diễn giải

Trung bình **từng khách hàng** trước khi tổng hợp, dùng tập chung giữa các loại ngày. Giữ ngày 0 và đỉnh hợp lệ; nội suy ngắn/ngày tương đồng có giới hạn, nguồn bù là quan sát gốc. MAD chỉ cảnh báo. K-Means dùng hình dạng Q, DBSCAN giữ noise trong đóng góp. Nhãn nhóm ban đầu trung tính; tên ca cần cơ sở nghiệp vụ.

`F = Σ(w×M)`, `S = Σ(N×ΣF)`, `α = A/S`, `E = αF`, `P = E/Δt`. Cùng α cho toàn tháng và mọi thành phần. Đổi 48→24 bằng cộng kWh; kW là công suất trung bình. Nguồn 60 phút không thể tạo số đo 30 phút. Thiếu A vẫn xem mẫu/chuẩn hoá; không tạo đường suy rộng giả.

Đối soát CMIS chỉ so tháng lịch có đủ MDMS gốc và `sample_billing_basis=calendar_month`; các kỳ khác là N/A. Không ép từng khách hàng khớp CMIS. Không tuyên bố độ tin cậy/sai số toàn tổng thể khi thiếu hồ sơ thiết kế mẫu.

Kết quả nằm trong `runs/<run_id>/artifacts/result.json`; cấu hình, manifest/checksum, danh mục và nhật ký bù được giữ trong dự án. Chu kỳ chuẩn nằm trong cache DuckDB bất biến dùng chung giữa các run; quyết định kỹ thuật được giải thích trong [docs/architecture.md](docs/architecture.md). Khi nguồn bị mất/thay đổi, vẫn xem được kết quả cũ; không tái chạy như thể nguồn chưa đổi. `run-config.json` trong bộ xuất giữ ngữ nghĩa nhập và lịch hiệu lực, rút đường dẫn về tên tệp để không đưa tên thư mục cá nhân vào báo cáo; cần đặt lại vị trí nguồn khi tái chạy.

## Kiểm thử và build

```bash
python -m pytest -q
python -m ruff check src tests
python -m ruff format --check src tests
python -m mypy src/load_research
python -m build --wheel --no-isolation
```

Suite bao gồm benchmark nhỏ có giới hạn, không tự chạy quy mô 122 triệu giá trị. Không skip/xfail để đạt tỷ lệ pass. Tài liệu build native và kiểm thử máy sạch: [packaging/README.md](packaging/README.md).

## GitHub Actions và phát hành

Workflow [CI and desktop release](.github/workflows/release.yml) kiểm tra Windows x64 và macOS arm64 khi push `main` hoặc mở PR. Push tag `vX.Y.Z` sẽ build DMG macOS, ZIP portable Windows và wheel, chạy smoke test chương trình đóng gói, tạo checksum rồi công bố GitHub **pre-release**. Tag phải trùng version trong `pyproject.toml` và `src/load_research/__init__.py`; workflow không thay release đã có.

Để build thử: mở [Actions](https://github.com/binhnt149/load-research/actions/workflows/release.yml) → **Run workflow** → chọn `main` và `platform`: `all`, `macos-arm64` hoặc `windows-x64`. Lượt thủ công tạo artifact để tải. Job publish dùng `GITHUB_TOKEN` có sẵn với `contents: write` khi push tag hợp lệ.

Quy trình tag mới, tệp đầu ra và giới hạn ký số được ghi trong [hướng dẫn phát hành](packaging/README.md#github-actions). Kết quả test, native smoke và trạng thái tài khoản Actions được ghi trong [báo cáo kiểm chứng](docs/verification/actions.md).

```bash
python -m load_research benchmark --output benchmark-data/small --customers 100 --months 1 --year 2025
python -m load_research benchmark --output benchmark-data/full --customers 7000 --months 12 --year 2025 --full-size
```

Benchmark ghi OS/CPU/RAM, số giá trị, thời gian, RSS và disk lấy mẫu. Kiểm tra dung lượng trước khi sinh dữ liệu lớn. Mốc 120 phút/10 GB RSS là mục tiêu đề xuất; chưa xác nhận AC-24. Hiện còn E01 (tệp thực/UAT), E02 (bộ cài trên hai OS/máy sạch), E03 (benchmark đầy đủ/UAT); xem trạng thái chính xác trong `tasks.md`.
