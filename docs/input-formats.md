# Định dạng đầu vào v1

Tên cột dưới đây là tên chuẩn, có thể ánh xạ từ tên hệ thống. CSV UTF-8/BOM, dấu phân cách khai báo; MDMS có lựa chọn dấu thập phân và định dạng thời gian. ID là chuỗi; không ghép bằng tên. XLSX công thức phải có cached value, nếu không phải xuất lại thành giá trị. Parquet nên lưu ID kiểu string.

## Danh mục CMIS mẫu

```csv
customer_id,industry_code,industry_name,meter_id,sampling_weight,year_month,sample_billing_kwh,sample_billing_basis
000001,01,Cơ khí,M000001,1,2024-02,2400,calendar_month
```

`organization_code` nếu có phải khớp scope. `valid_from`, `valid_to` là thời gian địa phương ISO, khoảng `[from,to)`; trống là không giới hạn. Nhiều công tơ chồng thời gian của một khách hàng phải khai báo `meter_role=additive` cho tất cả; công tơ thay thế dùng khoảng hiệu lực không chồng. Ngành/trọng số phải ổn định trọn tháng để vào cohort chung. `sampling_weight` mặc định 1, chỉ dùng trọng số dương do đơn vị cung cấp. `industry_name` tuỳ chọn và phải nhất quán theo mã ngành.

Sản lượng mẫu tuỳ chọn, cần `year_month`. `sample_billing_basis` trống/chưa xác nhận hoặc `billing_label_month` trả đối soát N/A; `calendar_month` chỉ so khi MDMS gốc đủ cả tháng. Không dùng số mẫu này làm tổng toàn ngành A.

## MDMS

```csv
meter_id,timestamp,value,source_quality_flag,unit,direction,interval_minutes
M000001,2024-02-01T00:00:00,2,actual,kWh,import,30
```

Khai báo cho từng nguồn: `values_already_scaled` bắt buộc true/false, `multiplier`, native `interval_minutes=15/30/60`, `measurement_kind=interval_energy` hoặc `interval_average_power`, đơn vị Wh/kWh/MWh hoặc W/kW/MW tương ứng, `timestamp_convention=start/end`, múi giờ, dạng dài/rộng, sheet/ánh xạ và format.

Chỉ nhận điện năng tác dụng chiều nhận. Không hỗ trợ trực tiếp chỉ số luỹ kế hoặc công suất tức thời; phải có quy trình chuyển đổi được xác nhận trước. Trường `channel`, `direction`, `unit`, `measurement_kind`, `interval_minutes`, `interval_start/end` có mặt phải khớp khai báo, không bỏ qua mâu thuẫn.

`source_quality_flag`: actual/measured/valid/a là biết đo gốc; estimated/substituted/e/s tính vào ngân sách ước lượng; invalid/missing là thiếu; không có hoặc mã khác báo chất lượng nguồn chưa biết. Ánh xạ mã riêng của đơn vị trước khi dùng. `outage/shutdown/do_not_estimate` hoặc cột `repair_blocked=true` chặn bù; giá trị 0 có đo vẫn được giữ, thiếu phải để trống. Cờ này lan từ 15→30/60 phút và giữa công tơ cộng gộp.

Giá trị thiếu để trống. Giá trị âm/không hữu hạn/cột mâu thuẫn bị cách ly, có source row và lý do. Hàng wide có lỗi bị loại **cả hàng**, không giữ một phần tiền tố; ghi slot lỗi nếu đã xác định. Dòng trùng giống nhau khử trùng có nguồn; trùng khác giá trị/chất lượng hoặc chu kỳ chồng bị chặn để rà soát.

Wide dùng `date=YYYY-MM-DD` và đủ cột `slot_01`… theo native resolution. Thứ tự slot theo giờ địa phương; dấu cuối chu kỳ 00:00 được quy về ngày trước theo khai báo. Ngày DST chưa có chính sách riêng bị từ chối.

## Thương phẩm toàn ngành và lịch

```csv
industry_code,year_month,billing_energy,unit,billing_basis,organization_scope,source_description
01,2024-02,100000,kWh,calendar_month,NPC,Bảng thương phẩm đã xác nhận
```

Mỗi ngành-tháng có đúng một A; không âm, hữu hạn, đơn vị năng lượng và cơ sở kỳ bắt buộc. `billing_label_month` được giữ nguyên nhãn cơ sở kỳ; khớp số học không chứng minh tương đương tháng lịch. Chưa có A vẫn xử lý mẫu, ô suy rộng là missing_billing.

```csv
date,day_type
2024-02-10,holiday
2024-02-17,weekday
```

Ưu tiên: override tệp (theo thứ tự tệp), override cấu hình/UI, holiday, cuối tuần, weekday. Calendar thực dùng được snapshot/hash; không tự lấy lịch lễ trên Internet. Các mã ngày là weekday/saturday/sunday/holiday.

## Xử lý lỗi nguồn

Mở nhật ký tác vụ để xem giai đoạn/lý do; `import-issues.jsonl` và `quality-events.jsonl` nằm trong artifacts của run (hoặc được tham chiếu cache). Sửa tệp xuất hoặc ngữ nghĩa/mapping rồi tạo run mới. Giữ nguyên bản nguồn cũ để còn tái lập run cũ; sử dụng chức năng sao lưu trước khi thay nguồn thực tế.
