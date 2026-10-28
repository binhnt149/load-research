# Đặc tả ứng dụng Desktop Load Research

- Phiên bản tài liệu: 0.1.
- Ngày lập: 23/10/2026, múi giờ Asia/Ho_Chi_Minh.
- Trạng thái: mục tiêu đã được người dùng xác nhận; đặc tả nghiệp vụ, phương pháp và kỹ thuật dưới đây là bản đề xuất để duyệt trước khi lập kế hoạch triển khai.
- Phạm vi lưu trữ: mục tiêu và đặc tả cùng nằm trong `load-research.md` theo yêu cầu người dùng.
- Hiện trạng dự án: thư mục chưa có mã nguồn, cấu hình build hoặc bộ kiểm thử; các cấu trúc và lệnh trong tài liệu là hợp đồng cho bước triển khai, chưa phải chức năng đang chạy.

## 1. Mục tiêu đã được xác nhận

Xây dựng ứng dụng desktop chạy trên **Windows và macOS**, phục vụ chuyên viên nghiên cứu phụ tải làm việc trên máy tính cá nhân. Ứng dụng giảm thao tác thủ công khi ghép dữ liệu, làm sạch và tổng hợp, đồng thời bảo đảm phương pháp nhất quán và có thể kiểm tra lại giữa các đợt nghiên cứu.

Mỗi đợt dự kiến xử lý **khoảng 7.000 khách hàng với 12 tháng dữ liệu**. Đầu vào là tệp xuất từ CMIS và MDMS của **tập mẫu đã được chốt**, cùng bảng **tổng điện năng thương phẩm từng tháng của toàn bộ khách hàng theo nhóm ngành nghề**.

Đầu ra là bộ biểu đồ phụ tải theo **ngành nghề × tháng × loại ngày**, gồm một biểu đồ chung để báo cáo và các biểu đồ thành phần theo nhóm hành vi. Người dùng xem, so sánh và xuất dữ liệu dưới dạng **công suất kW** hoặc **điện năng kWh**, lựa chọn **48 chu kỳ/ngày hoặc 24 chu kỳ/ngày**. Có đường cong chuẩn hoá để so sánh hình dạng phụ tải và đường cong suy rộng theo điện năng thương phẩm.

Ứng dụng cần bộ phương pháp có giải thích rõ, cho phép người dùng điều chỉnh tham số, lưu cấu hình và truy lại từng lần nghiên cứu. Thiết kế/chọn mẫu mới, bao gồm phân bổ Neyman, thuộc giai đoạn sau. Giai đoạn đầu nhập tệp và xử lý tại máy cá nhân; chưa kết nối trực tiếp CMIS/MDMS.

### 1.1. Tiêu chí thành công ở cấp sản phẩm

1. Hoàn thành quy trình từ nhập tệp đến xuất bộ kết quả phục vụ báo cáo trên cả hai hệ điều hành.
2. Có thể giải thích một đường cong được tạo từ những khách hàng, ngày, quy tắc và tham số nào.
3. Chạy lại được một nghiên cứu bằng dữ liệu và cấu hình đã lưu, với sai khác số học trong dung sai quy định.
4. Điện năng suy rộng cân bằng với bảng thương phẩm; các đường cong đóng góp của nhóm hành vi cộng lại thành đường cong chung.
5. Giảm thao tác thủ công thông qua ánh xạ cột dùng lại được, xử lý theo lô và mẫu cấu hình. Mức giảm thời gian thực tế được đo khi UAT; chưa có số liệu nền để cam kết tỷ lệ giảm.

## 2. Giả định và quyết định được đề xuất

Những điểm sau **chưa phải yêu cầu đã được người dùng xác nhận riêng**. Chúng là mặc định đề xuất để đặc tả có thể triển khai và kiểm thử; thay đổi phải được cập nhật vào tài liệu trước khi viết phần mã liên quan.

| ID | Giả định/đề xuất | Cách xử lý nếu không đúng |
|---|---|---|
| A-01 | Một người dùng thao tác một dự án tại một thời điểm; xử lý nghiệp vụ không cần Internet | Tách yêu cầu cộng tác hoặc tích hợp mạng thành phạm vi bổ sung |
| A-02 | Giao diện tiếng Việt, giữ thuật ngữ và đơn vị kỹ thuật chuẩn | Bổ sung bản địa hoá khi có yêu cầu |
| A-03 | MDMS chủ yếu có điện năng chu kỳ hoặc công suất trung bình chu kỳ, độ phân giải 15/30/60 phút | Xác nhận bằng tệp mẫu; không suy đoán đơn vị hay ý nghĩa cột |
| A-04 | Chu kỳ phân tích ưu tiên 30 phút để đáp ứng đầu ra 48/24 chu kỳ | Dữ liệu chỉ có 60 phút chỉ đủ cho đầu ra 24 chu kỳ; xử lý theo mục 7 |
| A-05 | Tháng nghiên cứu là năm-tháng cụ thể theo lịch địa phương | Cần khai báo riêng nếu điện năng thương phẩm là tháng ghi sổ hoặc kỳ chốt chỉ số |
| A-06 | Phân nhóm ngày gồm ngày thường, thứ Bảy, Chủ nhật, lễ | Cho phép hiệu chỉnh từng ngày bằng lịch của đơn vị |
| A-07 | Phân cụm mặc định trên đường cong đại diện của khách hàng theo tháng và loại ngày | Nếu cần phân cụm từng khách hàng-ngày, phải bổ sung phương án và benchmark riêng |
| A-08 | Xuất XLSX, CSV và hình PNG/SVG là đủ cho bản đầu | Báo cáo PDF/DOCX theo mẫu hành chính là phần mở rộng sau khi có mẫu |
| A-09 | Python + Qt/PySide6 và công cụ phân tích dữ liệu cục bộ là phương án kỹ thuật ưu tiên | Có thể thay stack nếu vẫn đáp ứng toàn bộ hợp đồng nghiệp vụ và hiệu năng |

Tệp mẫu thực tế, phiên bản hệ điều hành và cấu hình máy chưa được cung cấp. Các ngưỡng chất lượng, cấu hình thuật toán và mục tiêu hiệu năng trong tài liệu là **đề xuất ban đầu**, không được trình bày như tiêu chuẩn bắt buộc của EVN/NPC hoặc kết quả benchmark đã đạt.

## 3. Phạm vi phiên bản đầu

### 3.1. Bắt buộc

- Quản lý dự án, bộ dữ liệu và nhiều lần chạy nghiên cứu.
- Nhập nhiều tệp CMIS/MDMS, bảng thương phẩm theo ngành, danh mục ngành nghề và lịch ngày đặc biệt.
- Ánh xạ trường, kiểm tra định dạng, đơn vị, chu kỳ, hệ số đo và quan hệ khách hàng-công tơ.
- Ghép dữ liệu; kiểm tra chất lượng; bù dữ liệu có giới hạn; lưu dấu vết xử lý.
- Đánh giá mức đáp ứng của tập mẫu hiện hữu theo ngành, tháng và loại ngày.
- Tạo đường cong đại diện, chuẩn hoá, phân cụm K-Means hoặc DBSCAN và tổng hợp biểu đồ.
- Suy rộng theo điện năng thương phẩm tháng, có kiểm tra bảo toàn điện năng.
- Xem biểu đồ chung, đường cong chuẩn hoá, biểu đồ nhóm hành vi và bảng dữ liệu.
- Xuất theo lô 24/48 chu kỳ, kW/kWh, kèm thông tin phương pháp và chất lượng.
- Lưu cấu hình, lịch sử, nguồn dữ liệu, thao tác điều chỉnh và phiên bản phương pháp.
- Chạy tác vụ nền, hiển thị tiến độ, huỷ tác vụ và chạy lại từ kết quả trung gian hợp lệ.
- Đóng gói và kiểm thử ứng dụng trên Windows và macOS.

### 3.2. Ngoài phạm vi phiên bản đầu

- Thiết kế/chọn mẫu mới, tính phân bổ Neyman và tự bổ sung khách hàng ngoài tập mẫu.
- Khẳng định độ chính xác đại diện toàn bộ tổng thể khi chưa có hồ sơ thiết kế mẫu.
- Kết nối trực tiếp cơ sở dữ liệu/API CMIS, MDMS hoặc đồng bộ thời gian thực.
- Nền tảng web, máy chủ trung tâm, tài khoản dùng chung và chỉnh sửa đồng thời.
- Dự báo phụ tải tương lai, tối ưu vận hành hoặc đánh giá hiệu quả điều chỉnh phụ tải.
- Phân tích điện phản kháng, công suất biểu kiến và điện phát ngược trong cùng đường cong điện tiêu thụ.
- Tự chuyển chỉ số công tơ tích luỹ hoặc công suất tức thời thành điện năng khi thiếu thông tin cần thiết.
- Tự xác nhận một cụm tương ứng với ca sản xuất thực tế khi chưa có thông tin nghiệp vụ.
- Báo cáo PDF/DOCX theo mẫu chưa được cung cấp; bootstrap hoặc khoảng tin cậy suy luận theo thiết kế mẫu.

## 4. Bản đồ năng lực và ranh giới module

Các ID dưới đây được giữ ổn định để truy vết yêu cầu, hợp đồng dữ liệu và kiểm thử. Bản đồ là đề xuất trong cùng file đặc tả; chưa phải kế hoạch công việc hoặc thứ tự giao task đã được duyệt.

| Module ID | Trách nhiệm | Phụ thuộc |
|---|---|---|
| `research-workspace` | Dự án, phiên bản cấu hình, manifest đầu vào, nhật ký lần chạy và lưu trữ dùng chung | — |
| `data-import` | Đọc tệp, ánh xạ, chuẩn hoá kiểu/đơn vị/thời gian, ghép khách hàng-công tơ | `research-workspace` |
| `calendar` | Tạo lịch ngày nghiên cứu, loại ngày và số ngày theo tháng | `research-workspace` |
| `data-quality` | VEE phục vụ nghiên cứu, bù có kiểm soát, danh sách đủ điều kiện, thống kê chất lượng | `data-import`, `calendar` |
| `class-profiles` | Tạo đường cong đại diện trên cùng tập khách hàng và chuẩn hoá | `data-quality`, `calendar` |
| `behavior-clustering` | Phân cụm hình dạng, gán nhãn, lưu kết quả và chỉ số đánh giá | `class-profiles` |
| `industry-scaling` | Tổng hợp đường cong, đóng góp cụm và suy rộng theo điện năng thương phẩm | `class-profiles`, `behavior-clustering`, `data-import`, `calendar` |
| `report-export` | Kết xuất bảng, hình, phương pháp, chỉ số chất lượng và manifest | `industry-scaling` |
| `desktop-shell` | Điều hướng, cấu hình, xem dữ liệu/biểu đồ, điều khiển tác vụ nền | Các hợp đồng công khai của các module trên |

Thứ tự phụ thuộc: `research-workspace` → `data-import` và `calendar` → `data-quality` → `class-profiles` → `behavior-clustering` → `industry-scaling` → `report-export`. `desktop-shell` là lớp trình bày; các module phân tích không import UI.

### 4.1. Hợp đồng giữa các module

| Bên cung cấp | Đầu ra công khai tối thiểu | Bất biến |
|---|---|---|
| `research-workspace` | `ProjectRef`, `RunConfig`, `InputManifest`, `ArtifactRef` | Cấu hình và nguồn của run đã bắt đầu không bị sửa tại chỗ |
| `data-import` | `CanonicalDatasetRef`, `ImportSummary`, danh sách lỗi theo nguồn | Mỗi giá trị có đơn vị, thời gian, nguồn và khoá xác định |
| `calendar` | Bảng ngày và `N[year_month, day_type]` | Mỗi ngày thuộc đúng một loại; tổng N bằng số ngày trong tháng |
| `data-quality` | `QualityDatasetRef`, `EligibilityTable`, `AdjustmentLog` | Không thay đổi bản gốc; phân biệt thiếu dữ liệu với giá trị 0 |
| `class-profiles` | `CustomerProfileSet`, tập khách hàng chung theo ngành-tháng | Một vector đầy đủ K chu kỳ cho mỗi khách hàng-tháng-loại ngày đủ điều kiện |
| `behavior-clustering` | `ClusterAssignmentSet`, `ClusterDiagnostics` | Mỗi vector được gán một nhãn, kể cả chưa phân loại/không hoạt động |
| `industry-scaling` | `ProfileResultSet`, `BalanceChecks`, trạng thái từng ngành-tháng | Thành phần cộng được; suy rộng cân bằng A tháng |
| `report-export` | `ExportManifest`, đường dẫn và checksum các tệp | Chỉ công bố bộ xuất hoàn chỉnh sau khi ghi thành công |

`ArtifactRef` chứa ít nhất `artifact_id`, `schema_version`, `content_hash`, đường dẫn tương đối và ID nguồn tạo ra nó. Tiến độ, cảnh báo và lỗi là sự kiện có cấu trúc, không phải chuỗi log để UI tự phân tích.

## 5. Quy trình người dùng

1. Tạo dự án, khai báo kỳ nghiên cứu, múi giờ, phạm vi ngành nghề và thư mục lưu.
2. Chọn tệp nguồn, cấu hình ánh xạ hoặc dùng lại mẫu ánh xạ đã lưu.
3. Xem kết quả kiểm tra sơ bộ: khách hàng ghép được, đơn vị/chu kỳ, độ bao phủ, dữ liệu trùng, lỗi và ngành chưa ánh xạ.
4. Nhập hoặc hiệu chỉnh lịch lễ/ngày làm việc đặc biệt, kiểm tra số ngày từng loại.
5. Chọn bộ tham số VEE, điều kiện mẫu, chuẩn hoá, thuật toán phân cụm và suy rộng.
6. Chạy kiểm tra/bù dữ liệu; xem thống kê và các trường hợp cần rà soát. Các sửa đổi nghiệp vụ cần lý do.
7. Chạy phân tích; xem trạng thái từng ngành-tháng, đường cong chung và thành phần.
8. Chọn loại ngày, nhóm hành vi, đơn vị và 24/48 chu kỳ; so sánh kết quả hoặc lần chạy khác.
9. Xuất bộ kết quả cùng cấu hình, phương pháp, chất lượng và đối soát năng lượng.
10. Mở lại dự án để xem kết quả cũ, sao chép cấu hình thành lần chạy mới hoặc chạy lại.

Có chế độ chạy liên tục theo cấu hình và chế độ chạy từng bước. Chạy liên tục dừng tại lỗi chặn hoặc trường hợp cần xác nhận ý nghĩa dữ liệu; cảnh báo thông thường được tổng hợp trong kết quả. Không yêu cầu thao tác tay cho từng khách hàng đã đáp ứng quy tắc.

## 6. Dữ liệu đầu vào và mô hình chuẩn

### 6.1. Định dạng tệp

- Bắt buộc hỗ trợ CSV UTF-8/UTF-8 BOM và XLSX; hỗ trợ Parquet để nhập lại dữ liệu chuẩn đã lưu.
- MDMS hỗ trợ dạng dài: một bản ghi/điểm đo/chu kỳ; và dạng rộng: một bản ghi/điểm đo/ngày với các cột chu kỳ.
- Cho phép chọn nhiều tệp, sheet, hàng tiêu đề, định dạng ngày, dấu phân cách và dấu thập phân. Các lựa chọn phải được lưu.
- Mã khách hàng, công tơ, đơn vị và ngành nghề là chuỗi; giữ số 0 đầu. Không ghép theo tên khách hàng.
- Tệp có cột cần thiết chứa công thức Excel phải có giá trị lưu sẵn hợp lệ; ứng dụng không thực thi macro hoặc tự tính công thức của workbook nguồn.
- Định dạng XLS cũ, tệp mã hoá, tệp hỏng hoặc cấu trúc không hỗ trợ được báo rõ; không tự bỏ qua.

### 6.2. CMIS của tập mẫu

| Trường chuẩn | Bắt buộc | Ý nghĩa/quy tắc |
|---|---|---|
| `customer_id` | Có | Khoá khách hàng trong phạm vi `organization_code` nếu mã không duy nhất toàn hệ thống |
| `industry_code` | Có | Mã ngành theo danh mục đã được phiên bản hoá |
| `organization_code` | Khi cần phân biệt khoá/phạm vi | Phải tương thích với phạm vi bảng thương phẩm |
| `meter_id`, `measurement_point_id` | Trực tiếp hoặc qua bảng liên kết | Liên kết có thời gian hiệu lực; không giả định một khách hàng chỉ có một công tơ |
| `valid_from`, `valid_to` | Khi quan hệ/ngành thay đổi | Khoảng hiệu lực không chồng lấn mâu thuẫn |
| `year_month`, `sample_billing_kwh` | Nếu có trong tệp CMIS | Sản lượng mẫu dùng đối soát; cần khai báo cơ sở kỳ tính |
| `sampling_weight` | Không | Chỉ dùng nếu được đơn vị cung cấp kèm nguồn, ý nghĩa và phạm vi hiệu lực |
| Tên, địa chỉ, cấp điện áp, công suất hợp đồng | Không | Hiển thị/đối soát khi có; không phải khoá ghép |

Nếu CMIS không có sản lượng tháng của từng khách hàng, ứng dụng vẫn tạo biểu đồ và suy rộng bằng MDMS cùng tổng ngành; chỉ số đối soát CMIS ở cấp khách hàng sẽ là `N/A`.

### 6.3. MDMS

| Trường chuẩn | Bắt buộc | Ý nghĩa/quy tắc |
|---|---|---|
| `measurement_point_id`, `meter_id` | Có khoá đủ để ghép | Kèm mã đơn vị nếu cần |
| `interval_start`, `interval_end` | Có hoặc suy ra từ quy ước đã khai báo | Lưu khoảng nửa mở `[start, end)` |
| `value`, `unit` | Có | Điện năng chu kỳ Wh/kWh/MWh hoặc công suất trung bình W/kW/MW |
| `measurement_kind` | Có trong cấu hình nguồn | `interval_energy` hoặc `interval_average_power`; không tự nhận công suất tức thời là trung bình |
| `channel`, `direction` | Có trong cấu hình nguồn | Bản đầu phân tích điện năng tác dụng nhận từ lưới; tránh cộng kênh tổng với kênh thành phần |
| `interval_minutes` | Có | 15, 30 hoặc 60; kiểm tra thực tế từng bản ghi |
| `values_already_scaled`, `multiplier` | Có trong cấu hình nguồn | Xác định có áp CT/PT/hệ số nhân hay không; chỉ áp một lần |
| `source_quality_flag` | Không | Giữ nguyên cờ VEE nguồn; nếu không có ghi `unknown`, không tự gọi là số đo đã xác minh |
| `source_file_id`, `sheet`, `source_row`, `source_slot` | Do ứng dụng sinh | Truy vết về dữ liệu gốc |

Khóa chống trùng bao gồm phạm vi đơn vị, điểm đo/công tơ, kênh, chiều, bắt đầu và kết thúc chu kỳ. Sau khi giải quyết quan hệ công tơ, dữ liệu phân tích được tổng hợp về **khách hàng × ngày × chu kỳ**, tránh đếm đôi khi thay công tơ hoặc có điểm đo tổng/phụ.

### 6.4. Bảng tổng điện năng thương phẩm toàn ngành

| Trường | Bắt buộc | Quy tắc |
|---|---|---|
| `organization_scope` | Có | Phạm vi tổng thể; phải khớp phạm vi dự án |
| `industry_code` | Có | Cùng danh mục ngành với tập mẫu hoặc có bảng chuyển đổi rõ ràng |
| `year_month` | Có | Năm-tháng, không chỉ số tháng |
| `billing_energy`, `unit` | Có | Quy đổi về `industry_billing_kwh = A[g,m]`, hữu hạn và không âm |
| `billing_basis` | Có | `calendar_month` hoặc `billing_label_month` |
| `source_description` | Có | Báo cáo/kỳ trích xuất/phạm vi điện thương phẩm |

Một giá trị duy nhất cho mỗi phạm vi-ngành-tháng sau hợp nhất. Nếu nhập nhiều đơn vị con, phải khai báo chúng không chồng lấn trước khi cộng. Không cộng đồng thời dòng tổng và các dòng cấu thành tổng.

Nếu A là số tháng ghi sổ, kết quả phải mang nhãn **suy rộng theo điện năng thương phẩm tháng ghi sổ**, cùng giả định phân bố theo lịch tháng nghiên cứu. Không mô tả nó là số đo thực tế của tháng dương lịch. Chưa khai báo cơ sở kỳ tính thì chưa được xuất kết quả suy rộng chính thức.

### 6.5. Danh mục và lịch

- Danh mục ngành: mã, tên, phiên bản, hiệu lực và ánh xạ từ mã nguồn. Ngành chưa ánh xạ được cách ly với thống kê năng lượng liên quan.
- Lịch: ngày, loại ngày, nhãn ngày đặc biệt, nguồn, ghi chú và phiên bản. Cho nhập CSV/XLSX hoặc chỉnh trong UI.
- Ngày lễ/nghỉ và ngày làm bù do đơn vị cung cấp hoặc xác nhận; không đóng cứng lịch của một năm vào ứng dụng.
- Nếu ngành của khách hàng đổi giữa tháng, chỉ tự xử lý khi có hiệu lực và quy tắc quy thuộc rõ ràng. Nếu thiếu quy tắc, đưa khách hàng-tháng vào diện cần xử lý, không tự gán theo bản ghi cuối.

## 7. Thời gian, đơn vị và 24/48 chu kỳ

### 7.1. Quy ước thời gian

- Múi giờ mặc định đề xuất: `Asia/Ho_Chi_Minh`; lưu trong cấu hình và kết quả.
- Phải khai báo dấu thời gian nguồn là đầu hay cuối chu kỳ. Bản ghi kết thúc lúc 00:00 phải được quy về khoảng bắt đầu thuộc ngày trước nếu đúng quy ước nguồn.
- Chỉ số chu kỳ xuất bắt đầu từ 1: 48 chu kỳ là `[00:00,00:30)` … `[23:30,24:00)`; 24 chu kỳ là `[00:00,01:00)` … `[23:00,24:00)`.
- Ngày là ngày của `interval_start` sau khi chuẩn hoá. `24:00` chỉ là nhãn kết thúc, không phải thời điểm bắt đầu của cùng ngày.
- Kiểm tra tháng thiếu ngày, năm nhuận, tháng 28/29/30/31 ngày và kỳ nghiên cứu qua nhiều năm.
- Nếu dùng múi giờ có chuyển giờ mùa hè, phải bổ sung quy tắc ngày 23/25 giờ trước khi xử lý; bản đầu không ép các ngày đó thành 24/48 chu kỳ âm thầm.

### 7.2. Đại lượng vật lý

Điện năng và công suất có ý nghĩa khác nhau; tham khảo định nghĩa của [EIA về đo lường điện](https://www.eia.gov/energyexplained/electricity/measuring-electricity.php). Với công suất **trung bình trong chu kỳ**:

```text
e[k] (kWh) = p[k] (kW) × Δt (giờ)
p[k] (kW)  = e[k] (kWh) / Δt (giờ)
```

- 48 chu kỳ: `Δt = 0,5 giờ`; 24 chu kỳ: `Δt = 1 giờ`.
- Biểu đồ kWh biểu diễn điện năng **trong từng chu kỳ**, không phải điện năng tích luỹ trong ngày.
- Đường cong chuẩn hoá là đại lượng không thứ nguyên; không gắn trục kW/kWh cho đường cong này.
- Giữ số thực 64 bit cho tổng hợp/suy rộng; chỉ làm tròn khi hiển thị hoặc xuất theo tuỳ chọn.

### 7.3. Quy đổi độ phân giải

```text
e_60[h] = e_30[2h - 1] + e_30[2h]
p_60[h] = (p_30[2h - 1] + p_30[2h]) / 2
```

- Dữ liệu 15 phút được cộng điện năng về 30 hoặc 60 phút, với đủ các chu kỳ con hợp lệ.
- Chu kỳ con thiếu không được coi là 0 hoặc coi tổng một phần là chu kỳ đủ. Chu kỳ đích được gắn cờ để VEE xử lý.
- Khi đổi cách xem/xuất 48 → 24, dùng kết quả cùng run và cộng điện năng; không phân cụm lại chỉ vì đổi cách hiển thị.
- Dữ liệu chỉ có 60 phút không xác định được biến động trong hai nửa giờ. Bản đầu không xuất 48 điểm như dữ liệu có độ phân giải thực 30 phút.
- Dữ liệu trộn 30/60 phút: người dùng chọn phân tích 60 phút cho tập chung, hoặc chọn 30 phút và loại rõ phần không đáp ứng. Danh sách bị loại được ghi vào báo cáo.
- Điều kiện để đáp ứng đầy đủ đầu ra 48 chu kỳ: có đủ MDMS 30 phút hoặc mịn hơn cho tập được phân tích. Đây là điểm phải kiểm tra bằng tệp mẫu.

## 8. Kiểm tra chất lượng và bù dữ liệu

VEE trong ứng dụng là quy trình phục vụ nghiên cứu và truy vết. Việc tách kiểm tra, thay thế/ước lượng và cờ chất lượng tham khảo [AEMO Metrology Procedures, Part B](https://www.aemo.com.au/energy-systems/electricity/national-electricity-market-nem/market-operations/retail-and-metering/metrology-procedures-and-unmetered-loads). Các ngưỡng cụ thể dưới đây do đặc tả đề xuất; không tuyên bố tuân thủ quy trình thị trường điện của AEMO hoặc thay thế VEE của MDMS.

### 8.1. Kiểm tra trước khi bù

| Nhóm | Kiểm tra | Hành động mặc định |
|---|---|---|
| Cấu trúc | Thiếu cột, mã rỗng, ngày không đọc được, số không hữu hạn | Cách ly dòng, báo vị trí nguồn; lỗi có tính hệ thống chặn tệp |
| Ngữ nghĩa | Chưa rõ đơn vị, hệ số, kênh, ý nghĩa công suất hoặc dấu thời gian | Chặn nguồn đến khi khai báo rõ |
| Trùng | Cùng khoá, cùng giá trị và cùng thông tin chất lượng | Giữ một giá trị, lưu các tham chiếu nguồn trùng |
| Mâu thuẫn | Cùng khoá nhưng khác giá trị/cờ ảnh hưởng xử lý | Không tự chọn dòng cuối; yêu cầu quy tắc ưu tiên nguồn hoặc xử lý có lý do |
| Thời gian | Sai bước, chồng lấn, lệch biên, thiếu chu kỳ, thiếu cả ngày | Gắn cờ; đưa vào quy trình bù/loại có kiểm soát |
| Ghép mẫu | Không ghép được, nhiều quan hệ cùng hiệu lực, điểm đo bị đếm đôi | Cách ly phần ảnh hưởng; hiển thị số khách hàng và năng lượng liên quan |
| Giá trị | Điện nhận âm, ngoài miền vật lý đã cấu hình | Gắn cờ; xác định lỗi kênh/hệ số trước khi thay bằng ước lượng |
| Hành vi | Đỉnh bất thường, đường bằng kéo dài, ngày toàn 0 | Cảnh báo; không tự xoá vì có thể là hành vi vận hành thật |
| Đối soát | CMIS và MDMS có kỳ tính/phạm vi so sánh được | Báo sai lệch trước suy rộng; không tự ép từng khách hàng khớp CMIS |

Phát hiện ngoại lai thống kê có thể dùng median/MAD trên cùng khách hàng, tháng, loại ngày và vị trí chu kỳ. Mặc định chỉ tạo cảnh báo với hệ số đề xuất 6; nếu MAD bằng 0 hoặc dữ liệu quá ít thì không chia cho 0 và trả trạng thái không đủ cơ sở. Không tự cắt đỉnh hoặc làm phẳng phụ tải.

### 8.2. Thứ tự bù đề xuất

1. Ưu tiên dữ liệu thay thế đã được đơn vị xác minh, có nguồn và lý do; giữ cờ VEE gốc.
2. Với khoảng trống nội ngày không quá **60 phút**, nội suy tuyến tính khi có hai đầu hợp lệ, cùng khách hàng và cùng chế độ dữ liệu. Không nội suy qua ranh giới ngày hoặc qua sự kiện ngừng điện/ngừng sản xuất đã biết.
3. Với khoảng trống còn lại không quá **120 phút**, dùng trung vị chu kỳ tương ứng từ ít nhất **3 ngày nguồn** của cùng khách hàng, cùng tháng và cùng loại ngày. Ngày nguồn phải có số liệu gốc hợp lệ ở vị trí được dùng, không lấy giá trị vừa bù làm nguồn bù tiếp.
4. Có thể hiệu chỉnh mức của đường cong ngày tương đồng bằng tỷ số tổng điện năng trên các chu kỳ quan sát chung. Chỉ áp dụng nếu mẫu số dương, có ít nhất 50% số chu kỳ trong ngày để so mức và hệ số trong khoảng đề xuất `[0,5; 2,0]`.
5. Nếu không đạt điều kiện, giữ thiếu và loại ngày khỏi tập đủ điều kiện; không lấy trung bình toàn ngành để che lấp thiếu hụt.

Không tự bù cả ngày mất dữ liệu, sao chép ngày thường thành ngày lễ, hoặc dùng tháng khác mà không có phương pháp bổ sung được ghi nhận. Ngày toàn 0 hợp lệ được giữ là ngày không hoạt động; chỉ chuyển thành thiếu khi có bằng chứng lỗi dữ liệu.

### 8.3. Điều kiện ngày/khách hàng đủ dùng

- Ngày dùng cho đường cong phải đủ K chu kỳ sau xử lý; tỷ lệ giá trị ước lượng đã biết không vượt ngưỡng đề xuất **10% số chu kỳ**.
- Tỷ lệ trên gồm giá trị ứng dụng bù và giá trị MDMS đã đánh dấu ước lượng, nếu nguồn có thông tin. Phần không biết chất lượng nguồn phải báo riêng.
- Khách hàng-tháng phải có tối thiểu **80% chu kỳ gốc hợp lệ**, tính trên thời gian dự kiến có hiệu lực, trước bù của ứng dụng. Giá trị thiếu không được loại khỏi mẫu số.
- Mặc định bộ đường cong suy rộng chỉ dùng khách hàng có hiệu lực trọn tháng và đáp ứng yêu cầu các loại ngày hiện diện trong tháng; khách hàng gia nhập/rời giữa tháng được báo riêng.
- Sau loại mẫu, thống kê số khách hàng còn lại, số ngày, tỷ lệ bù và mức thay đổi thành phần mẫu theo ngành-tháng. Không đổi tên tập còn lại thành mẫu Neyman mới.

Mỗi chỉnh sửa lưu: định danh bản ghi, giá trị/cờ trước và sau, phương pháp, tham số, nguồn ngày dùng bù nếu có, thời điểm, người thao tác cục bộ và lý do khi sửa tay. Dữ liệu gốc bất biến.

## 9. Lịch và tập khách hàng chung

### 9.1. Phân loại ngày

Thứ tự ưu tiên: điều chỉnh theo ngày đã được xác nhận → lịch lễ/ngày đặc biệt → thứ Bảy → Chủ nhật → ngày thường. Mỗi ngày chỉ thuộc một loại, có ghi nguồn quy tắc.

`N[m,t]` là số ngày lịch của loại ngày t trong năm-tháng m. Nếu `N[m,t] = 0`, loại ngày đó là **không áp dụng**, không phải thiếu dữ liệu và không tạo đường cong 0 giả.

### 9.2. Cùng thành phần mẫu giữa các loại ngày

Đề xuất dùng **tập khách hàng chung I[g,m]** cho tất cả loại ngày có mặt trong cùng ngành-tháng. Cách này giúp tránh việc biểu đồ ngày thường chủ yếu đến từ một tập khách hàng còn biểu đồ Chủ nhật đến từ một tập khác.

Số ngày đủ điều kiện tối thiểu cho mỗi khách hàng-tháng-loại ngày, đề xuất:

| Loại ngày | Số ngày tối thiểu |
|---|---|
| Ngày thường | `min(5, N[m,t])` |
| Thứ Bảy | `min(2, N[m,t])` |
| Chủ nhật | `min(2, N[m,t])` |
| Lễ | `min(1, N[m,t])` |

Khách hàng thiếu một loại ngày có hiện diện sẽ không vào tập chung của ngành-tháng. Hiển thị số lượng và nguyên nhân bị loại; nếu tập chung quá nhỏ, cần điều chỉnh dữ liệu hoặc tạo run mới với tham số khác. Bản đầu không tự mượn loại ngày/tháng khác để tạo kết quả chính thức.

Ngưỡng đề xuất: tập chung có từ 30 khách hàng với vector năng lượng dương trở lên có thể thử phân cụm. Tập chung từ 10 đến 29 khách hàng vẫn có thể tổng hợp nhưng cảnh báo ít mẫu; dưới 10 chỉ tạo bản xem thử, chưa đủ điều kiện xuất suy rộng chính thức theo cấu hình mặc định. Nếu tập chung lớn nhưng còn dưới 30 vector năng lượng dương thì không phân cụm, vẫn tổng hợp đường cong vật lý. Đây là ngưỡng vận hành có thể chỉnh, không phải chứng minh sai số thống kê.

## 10. Tạo đường cong đại diện và chuẩn hoá

Ký hiệu:

- `i`: khách hàng; `d`: ngày; `g`: ngành; `m`: năm-tháng; `t`: loại ngày; `c`: cụm; `k`: chu kỳ.
- `e[i,d,k]`: điện năng kWh trong chu kỳ sau chuẩn hoá dữ liệu và VEE.
- `D[i,m,t]`: tập ngày đủ điều kiện của khách hàng i, tháng m, loại ngày t.
- `K`: 48 hoặc 24 theo độ phân giải phân tích; `Δt = 24/K` giờ.

Đường cong điện năng ngày đại diện của khách hàng:

```text
M[i,m,t,k] = Σ(d thuộc D[i,m,t]) e[i,d,k] / |D[i,m,t]|
E_day[i,m,t] = Σ(k=1..K) M[i,m,t,k]
```

Lấy trung bình trong từng khách hàng trước khi tổng hợp để số ngày quan sát nhiều hơn không tự làm khách hàng đó có trọng số cao hơn. Ngày toàn 0 hợp lệ vẫn tham gia phép tính trung bình này.

Các dạng chuẩn hoá được hỗ trợ:

```text
q[i,m,t,k] = M[i,m,t,k] / E_day[i,m,t]       # tỷ phần điện năng, tổng bằng 1
u[i,m,t,k] = K × q[i,m,t,k]                  # p.u. theo trung bình ngày, trung bình bằng 1
v[i,m,t,k] = M[i,m,t,k] / max_k M[i,m,t,k]    # theo đỉnh, đỉnh bằng 1; dùng để xem
```

Chuẩn hoá tách hình dạng khỏi mức tiêu thụ; ví dụ nghiên cứu [EPRI về phân cụm phụ tải](https://restservice.epri.com/publicdownload/000000003002018090/0/Product) sử dụng chuẩn hoá theo trung bình ngày. Đặc tả này đề xuất dùng **q** làm đặc trưng phân cụm và **u** làm cách xem chuẩn hoá mặc định; đây là lựa chọn của ứng dụng, không phải toàn bộ quy trình EPRI.

Nếu `E_day = 0`, giữ đường cong vật lý toàn 0 và nhãn `inactive`; q/u/v là `N/A`, không chia cho 0 và không đưa vector 0 vào phân cụm hình dạng.

## 11. Phân cụm hành vi

### 11.1. Đơn vị phân cụm

- Phân cụm riêng trong mỗi **ngành × năm-tháng × loại ngày** trên các vector q của khách hàng thuộc tập chung.
- Mỗi khách hàng có một vector cho một ô phân tích; có thể thuộc các nhóm khác nhau giữa các tháng hoặc loại ngày.
- Bản đầu mô tả hành vi trung bình theo ô phân tích, chưa mô hình hoá chuyển ca của từng ngày trong cùng tháng.
- Không thêm sản lượng tuyệt đối vào đặc trưng mặc định. Mức năng lượng được dùng ở bước tổng hợp, không để khách hàng lớn lấn át hình dạng khi học cụm.

Trong các quy tắc chọn số cụm, `n` là số vector năng lượng dương đủ điều kiện trong ô phân tích, sau khi tách `inactive`; không phải số ngày hoặc số dòng MDMS. Điều kiện tối thiểu 30 vector áp dụng cho cả K-Means tự động và DBSCAN trong cấu hình mặc định.

### 11.2. K-Means mặc định

- Khoảng số cụm đề xuất: 2–6, đồng thời có phương án một nhóm khi chưa có cơ sở tách cụm.
- Đặt rõ `random_state = 42`, `n_init = 10`, `max_iter = 300`; sắp xếp đầu vào theo khoá ổn định và lưu phiên bản thư viện.
- Đánh giá trên cùng tập con cố định tối đa 2.000 vector, bảo đảm có đại diện từng cụm và số nhãn hợp lệ. Không tính ma trận khoảng cách cho toàn bộ dữ liệu chu kỳ.
- Loại phương án có cụm dưới `max(10, ceil(2% × n))` khách hàng; chọn silhouette cao nhất trong các phương án còn lại. Nếu chênh không quá 0,02, ưu tiên ít cụm hơn.
- Nếu không có phương án hợp lệ hoặc silhouette tốt nhất dưới ngưỡng đề xuất 0,25, trả một nhóm `not_segmented` và lý do; không loại dữ liệu ra khỏi đường cong chung.
- Người dùng được đặt số cụm thủ công; vẫn hiển thị chỉ số, cảnh báo cụm nhỏ và ghi cấu hình.

Silhouette chỉ được định nghĩa khi có từ 2 đến n−1 nhãn; một cụm hoặc tập con không đủ nhãn phải trả `N/A`. Cơ sở thuật toán và chỉ số: [scikit-learn Clustering](https://scikit-learn.org/stable/modules/clustering.html), [silhouette_score](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.silhouette_score.html). Các ngưỡng 0,25/0,02 và kích thước cụm là đề xuất của đặc tả.

### 11.3. DBSCAN tùy chọn trong bản đầu

- Dùng cùng vector q và khoảng cách Euclidean; lưu `eps`, `min_samples`, độ phân giải và cách chuẩn hoá.
- `min_samples` đề xuất ban đầu là 10. `eps` được người dùng chọn sau khi xem phân bố khoảng cách lân cận; không dùng một eps cố định cho mọi ngành/độ phân giải.
- Nhãn noise được giữ trong nhóm đóng góp `unclassified`, không mặc nhiên coi là dữ liệu lỗi.
- Báo tỷ lệ noise, số cụm và chỉ số trên phần phân loại được; nếu còn dưới 2 cụm, silhouette là `N/A`.
- Có giới hạn bộ nhớ và kích thước ô phân tích; không chạy DBSCAN trên hàng trăm triệu dòng chu kỳ. Tài liệu [scikit-learn](https://scikit-learn.org/stable/modules/clustering.html) lưu ý nhu cầu bộ nhớ của một số cách tính lân cận, vì vậy cần kiểm soát kích thước bài toán trước khi chạy.
- Nếu DBSCAN vượt tài nguyên, kết thúc bước với lỗi rõ ràng và cho tạo run dùng K-Means; không âm thầm đổi thuật toán.

### 11.4. Nhãn và giải thích cụm

- Nhãn mặc định: Nhóm 1, Nhóm 2…; có gợi ý mô tả như đỉnh ban ngày/ban đêm hoặc tương đối bằng.
- Chuyên viên được đặt tên ca 1/2/3 sau khi xem biểu đồ và thông tin khách hàng; lưu tên, lý do và thời điểm.
- Không suy luận chắc chắn số ca làm việc chỉ từ số cụm.
- ID cụm chỉ có ý nghĩa trong ô phân tích và run; không mặc định Nhóm 1 tháng này là cùng hành vi với Nhóm 1 tháng khác.
- Lưu centroid hình dạng, danh sách thành viên, số khách hàng, tỷ trọng năng lượng mẫu và chỉ số chất lượng. Centroid chuẩn hoá không thay thế đường cong đóng góp vật lý của cụm.

## 12. Tổng hợp và suy rộng theo thương phẩm tháng

### 12.1. Trọng số và đường cong tập mẫu

Mặc định `w[i,m] = 1`. Nếu có trọng số do đơn vị cung cấp, phải dương, hữu hạn, có ý nghĩa và phạm vi được khai báo; sử dụng cùng trọng số trong mọi loại ngày của khách hàng-tháng đó. Không tự suy ra xác suất chọn mẫu hoặc trọng số Neyman từ dữ liệu MDMS hiện có.

```text
F[g,m,t,k] = Σ(i thuộc I[g,m]) w[i,m] × M[i,m,t,k]
```

F là đường cong tổng hợp của tập mẫu/trọng số đã khai báo. Với w bằng 1, đây là tổng các đường cong khách hàng đại diện, **không phải phụ tải trung bình của một khách hàng**. Mức tiêu thụ khác nhau được giữ trong M nên khách hàng tiêu thụ lớn đóng góp năng lượng tương ứng.

Đường cong chuẩn hoá của ngành-loại ngày lấy từ F: `Q[k] = F[k]/ΣF`, `U[k] = K×Q[k]`. Không dùng trung bình không trọng số các centroid cụm làm hình dạng toàn ngành.

### 12.2. Điện năng nền tháng và hệ số suy rộng

```text
S[g,m] = Σ(t có N[m,t] > 0) N[m,t] × Σ(k=1..K) F[g,m,t,k]
α[g,m] = A[g,m] / S[g,m]
E_industry[g,m,t,k] = α[g,m] × F[g,m,t,k]      # kWh/chu kỳ của ngày đại diện
P_industry[g,m,t,k] = E_industry[g,m,t,k] / Δt # kW trung bình chu kỳ
```

Giữ chênh lệch mức tiêu thụ giữa các loại ngày khi tính S. Không chuẩn hoá mỗi loại ngày về cùng tổng điện năng rồi chia đều A theo số ngày, vì thao tác đó làm mất chênh lệch ngày làm việc/ngày nghỉ.

Bất biến bắt buộc:

```text
Σ_t N[m,t] × Σ_k E_industry[g,m,t,k] = A[g,m]
Σ_t N[m,t] × Σ_k P_industry[g,m,t,k] × Δt = A[g,m]
```

Đây là mô hình phân bố điện năng tháng theo hình dạng mẫu. Việc khớp A chứng minh cân bằng điện năng theo mô hình, **không chứng minh hình dạng mẫu đại diện đúng cho mọi khách hàng ngoài mẫu**.

### 12.3. Biểu đồ đóng góp theo nhóm hành vi

```text
F_cluster[g,m,t,c,k] = Σ(i thuộc cụm c) w[i,m] × M[i,m,t,k]
E_cluster[g,m,t,c,k] = α[g,m] × F_cluster[g,m,t,c,k]
Σ_c E_cluster[g,m,t,c,k] = E_industry[g,m,t,k]
```

Tổng theo c phải gồm `unclassified`, `not_segmented` hoặc `inactive` khi có. Mỗi khách hàng thuộc đúng một nhãn trong ô phân tích. Tỷ lệ ngành phân cho các cụm là ước lượng từ tập mẫu; chưa có A riêng từng cụm để xác nhận cơ cấu toàn tổng thể.

UI tách hai cách xem: **hình dạng chuẩn hoá của nhóm** để so hành vi và **đóng góp kW/kWh của nhóm** để cộng thành đường chung. Không cộng các đường cong đã chuẩn hoá độc lập rồi gọi là tổng phụ tải vật lý.

### 12.4. Trường hợp biên và dữ liệu không đủ

| Tình huống | Kết quả |
|---|---|
| Thiếu A | Được xem/xuất đường cong mẫu hoặc chuẩn hoá có nhãn; không có suy rộng cho ô đó |
| A âm hoặc không hữu hạn | Lỗi đầu vào, chặn suy rộng ngành-tháng |
| A > 0, S = 0 hoặc không có tập mẫu đủ điều kiện | Không thể suy rộng; không tạo đường cong 0 giả |
| A = 0, S > 0 | Đường cong suy rộng bằng 0, cảnh báo khác biệt thương phẩm và mẫu |
| A = 0, S = 0, có dữ liệu hợp lệ xác nhận toàn 0 | Đường cong vật lý bằng 0; α và chuẩn hoá là `N/A` |
| N[m,t] = 0 | Loại ngày không áp dụng, không yêu cầu mẫu cho loại đó |
| Có loại ngày hiện diện nhưng không đủ dữ liệu | Theo quy tắc tập chung; không tự tạo loại ngày từ loại khác |
| Một ngành-tháng lỗi giữa lô | Các ô khác được hoàn thành; toàn run là `partial`, có manifest ô thiếu |

## 13. Đánh giá chất lượng và giới hạn suy luận

Mỗi ngành-tháng phải có ít nhất:

- Số khách hàng nhập, ghép được, bị loại theo nguyên nhân và còn trong tập chung.
- Số ngày/chu kỳ kỳ vọng, gốc hợp lệ, thiếu, ước lượng, sửa tay và không biết chất lượng nguồn.
- Số ngày từng loại theo lịch; số ngày dùng được của từng khách hàng và toàn ô phân tích.
- Thay đổi thành phần mẫu so với tháng trước; không che việc biểu đồ thay đổi do mẫu thay đổi.
- Đối soát CMIS–MDMS khi cùng phạm vi/kỳ; phần chênh lệch không so sánh được phải là `N/A` kèm lý do.
- Số cụm, kích thước cụm, silhouette khi áp dụng, tỷ lệ noise và lý do không phân cụm.
- A, S, α, sai số cân bằng tháng và sai số tổng thành phần ở từng chu kỳ.
- Điện năng ngày đại diện, đỉnh **của đường cong đại diện**, thời điểm đỉnh và hệ số phụ tải của đường cong này; không gọi chúng là cực đại thực đo của toàn ngành trong năm.

Nếu có sản lượng CMIS tháng dương lịch cùng phạm vi, có thể báo `Σ sản lượng khách hàng mẫu / A`. Chỉ số này là tỷ lệ điện năng quan sát được của mẫu, không phải chứng nhận tính đại diện thống kê.

Hồ sơ thiết kế mẫu và xác suất chọn chưa được cung cấp. Trạng thái ban đầu là **chưa xác minh thiết kế mẫu**; không kết luận mẫu là ngẫu nhiên hay phi xác suất chỉ vì có đo xa. Không xuất tuyên bố “độ tin cậy 95%, sai số ±x% toàn tổng thể” từ số lượng 7.000 hoặc từ silhouette. Việc suy luận cần thông tin về cơ chế chọn và khả năng sai lệch, như thảo luận trong [Statistics Canada về sử dụng mẫu phi xác suất](https://www150.statcan.gc.ca/n1/pub/12-001-x/2025001/article/00008-eng.htm).

Không đặt một chỉ số “độ chính xác mô hình” khi chưa có bộ đối chứng phù hợp. Chất lượng dữ liệu, chất lượng tách cụm và mức đại diện của mẫu được báo riêng.

## 14. Bộ tham số và cấu hình từng lần nghiên cứu

Mọi giá trị hiệu lực, kể cả mặc định, phải được lưu. Không chỉ lưu những trường người dùng đã sửa.

| Nhóm | Tham số | Mặc định đề xuất |
|---|---|---|
| Phạm vi | Ngành, năm-tháng, đơn vị, múi giờ | Theo dự án; `Asia/Ho_Chi_Minh` |
| Nhập | Ánh xạ, định dạng ngày/số, dấu thời gian, kênh, hệ số | Phải khai báo theo nguồn |
| Lịch | Phiên bản lịch, điều chỉnh loại ngày | Người dùng xác nhận lịch dùng cho run |
| Độ phân giải | Chu kỳ phân tích | 30 phút nếu nguồn đáp ứng |
| VEE | Khoảng trống nội suy tối đa | 60 phút |
| VEE | Khoảng trống dùng ngày tương đồng tối đa | 120 phút |
| VEE | Số ngày nguồn tối thiểu, miền hệ số hiệu chỉnh | 3 ngày; `[0,5; 2,0]` |
| VEE | Tỷ lệ ước lượng tối đa/ngày | 10% chu kỳ |
| Điều kiện mẫu | Chu kỳ gốc hợp lệ tối thiểu/tháng | 80% |
| Điều kiện mẫu | Ngày tối thiểu theo loại | 5/2/2/1, giới hạn theo số ngày lịch |
| Điều kiện mẫu | Số khách hàng chung tối thiểu để xuất chính thức | 10 |
| Ngoại lai | Hệ số MAD | 6, chỉ cảnh báo |
| Chuẩn hoá | Đặc trưng phân cụm; cách xem | Tỷ phần điện năng q; p.u. U |
| Phân cụm | Thuật toán | K-Means; DBSCAN khi người dùng chọn |
| K-Means | Khoảng cụm, seed, n_init, max_iter | 2–6; 42; 10; 300 |
| K-Means | Số mẫu tối đa tính silhouette | 2.000 |
| K-Means | Silhouette tối thiểu; ngưỡng hoà điểm | 0,25; 0,02 |
| K-Means | Cụm nhỏ nhất | `max(10, ceil(2% × n))` |
| DBSCAN | min_samples; eps | 10; eps do người dùng chọn, lưu rõ |
| Tổng hợp | Trọng số | 1; chỉ thay nếu có trọng số được cung cấp |
| Suy rộng | Cơ sở kỳ A và bảng thương phẩm | Bắt buộc khai báo |
| Xuất | Đơn vị, 24/48, kiểu bảng, số lẻ hiển thị | kW, 48 nếu hỗ trợ, dạng rộng, 6 số lẻ |
| Tài nguyên | Bộ nhớ query, số worker, thư mục tạm | Theo máy, có giới hạn và kiểm tra trước chạy |

Kiểm tra cấu hình: tỷ lệ thuộc `[0,1]`; thời lượng phù hợp lưới chu kỳ; số cụm/số mẫu là số nguyên dương trong miền hợp lệ; `eps > 0` khi chọn DBSCAN; trọng số hữu hạn dương. Thay đổi ngưỡng không sửa kết quả cũ: tạo run mới và ghi khác biệt cấu hình.

## 15. Yêu cầu chức năng có thể truy vết

| ID | Yêu cầu | Điều kiện chấp nhận chính | Kịch bản liên quan ở mục 21 |
|---|---|---|---|
| FR-01 | Quản lý nghiên cứu | Tạo/mở lại dự án, liệt kê run và sao chép cấu hình được | AC-18, AC-22; kiểm thử UI |
| FR-02 | Nhập theo lô | Nhập nhiều tệp, lưu ánh xạ, báo tổng dòng và lỗi theo nguồn | AC-01, AC-05; kiểm thử tích hợp nhập lô |
| FR-03 | Chuẩn hoá và ghép | Giữ mã chuỗi; áp đúng đơn vị/hệ số/kỳ; không ghép nhiều nghĩa | AC-01, AC-02, AC-06 |
| FR-04 | Quản lý lịch | Một loại ngày/ngày; lịch và số ngày được phiên bản hoá | AC-09 |
| FR-05 | VEE và bù | Giữ bản gốc; bù đúng giới hạn; truy vết giá trị sau sửa | AC-07, AC-08 |
| FR-06 | Đánh giá mẫu | Có danh sách đủ điều kiện/bị loại và tập chung theo ngành-tháng | AC-10, AC-11 |
| FR-07 | Đường cong chuẩn hoá | Q tổng 1, U trung bình 1 khi năng lượng dương; xử lý 0 đúng | AC-08, AC-12; kiểm thử bất biến Q/U |
| FR-08 | Phân cụm | K-Means/DBSCAN, cấu hình lưu lại, noise được giữ, nhãn sửa có lịch sử | AC-13, AC-14, AC-21; kiểm thử UI đổi nhãn |
| FR-09 | Tổng hợp/suy rộng | Đúng công thức mục 12, bảo toàn tháng và tổng thành phần | AC-13, AC-15, AC-16, AC-17 |
| FR-10 | Xem/so sánh | Lọc ngành-tháng-loại ngày; đổi kW/kWh, 24/48; xem chung/thành phần | AC-03, AC-04, AC-17; kiểm thử UI so hai run |
| FR-11 | Xuất kết quả | Xuất lô bảng/hình kèm nguồn, phương pháp, chất lượng, ô không đủ dữ liệu | AC-20; kiểm thử schema và nội dung bộ xuất |
| FR-12 | Tái lập | Run lưu đủ cấu hình, phiên bản, seed, manifest và các chỉnh sửa | AC-18, AC-21, AC-22 |
| FR-13 | Tác vụ nền | UI phản hồi, có tiến độ/huỷ; không công bố kết quả đang ghi dở | AC-19, AC-24; kiểm thử UI khi job chạy |
| FR-14 | Hai hệ điều hành | Cùng bộ dữ liệu chuẩn tạo kết quả tương đương trên Windows/macOS | AC-21, AC-23 |

## 16. Giao diện và trải nghiệm sử dụng

Điều hướng đề xuất gồm: **Dự án → Dữ liệu → Chất lượng → Phương pháp → Kết quả → Xuất & lịch sử**.

- Dữ liệu: xem trước có phân trang, ánh xạ cột, thống kê ghép và lỗi; không tải hàng trăm triệu dòng lên bảng UI.
- Chất lượng: bảng tổng quan theo ngành-tháng, lọc khách hàng cần rà soát, biểu đồ trước/sau bù và lý do loại.
- Phương pháp: tham số có đơn vị, giải thích tác dụng, giới hạn hợp lệ và nút khôi phục bộ mặc định đề xuất. Có xem phương pháp và công thức.
- Kết quả: bộ lọc ngành, năm-tháng, loại ngày; chuyển giữa đường cong chuẩn hoá, tập mẫu và suy rộng toàn ngành. Tên trục phải thể hiện đúng phạm vi/đơn vị.
- Nhóm hành vi: xem chồng hình dạng hoặc xem đóng góp xếp chồng; có nhóm chưa phân loại và thống kê thành viên.
- Bảng kết quả: chu kỳ, bắt đầu/kết thúc, kW/kWh, tỷ phần và cờ chất lượng; xuất đúng bộ lọc hoặc toàn lô.
- So sánh: tối đa hai run cùng phạm vi; hiển thị thay đổi cấu hình và thành phần mẫu trước khi giải thích khác biệt đường cong.
- Tiến độ: giai đoạn, số tệp/ngành-tháng đã xong, cảnh báo, trạng thái huỷ; thời gian dự kiến chỉ hiển thị khi có cơ sở ước tính.
- Không đủ dữ liệu: thông báo lý do và số liệu liên quan; phân biệt rõ 0, không áp dụng, chưa tính và lỗi.
- Khả dụng: thao tác bàn phím, thứ tự focus hợp lý, nhãn rõ, không chỉ dùng màu để phân biệt trạng thái/đường cong; hỗ trợ đường dẫn và font tiếng Việt.

## 17. Mô hình lưu trữ, lần chạy và truy vết

### 17.1. Thực thể tối thiểu

`Project`, `InputFile`, `ImportMapping`, `IndustryDictionary`, `CalendarVersion`, `CustomerMeterLink`, `CanonicalInterval`, `QualityEvent`, `EligibilityDecision`, `RunConfig`, `ResearchRun`, `CustomerProfile`, `ClusterAssignment`, `ProfileResult`, `ExportManifest`.

Các bản ghi kết quả chứa `run_id`, `schema_version`, `method_version`, phạm vi đơn vị, ngành, năm-tháng, loại ngày, chu kỳ, độ phân giải và chất lượng. Khoá kết quả còn gồm cụm/phạm vi đường cong khi áp dụng.

### 17.2. Thư mục dự án dữ liệu

```text
<research-project>/
  project.json
  metadata.sqlite
  sources/                 # manifest/checksum và bản sao nguồn khi chọn lưu kèm
  canonical/               # Parquet chuẩn, phân vùng theo năm-tháng/phạm vi hợp lý
  quality/                 # cờ và phần điều chỉnh, tham chiếu dữ liệu chuẩn
  cache/                   # kết quả trung gian theo hash dữ liệu + cấu hình liên quan
  runs/<run_id>/
    config.json
    input-manifest.json
    diagnostics.json
    artifacts/             # đường cong, thành viên cụm, thống kê
    logs/
  exports/<run_id>/
  temp/
```

- Không tạo một bản sao đầy đủ dữ liệu chu kỳ cho mỗi run; dùng dữ liệu bất biến chia sẻ và phần điều chỉnh theo phiên bản.
- Nếu chỉ lưu tham chiếu tệp nguồn, mở lại phải xác minh hash. Khi tệp mất hoặc đổi, vẫn xem được kết quả đã lưu nhưng không tuyên bố tái chạy được từ nguồn cũ.
- Có chức năng tạo bản sao lưu dự án kèm dữ liệu cần thiết; manifest mô tả rõ thành phần được đóng gói và dung lượng dự kiến.
- Đường dẫn trong dự án là tương đối để chuyển máy; không phụ thuộc dấu phân cách của hệ điều hành.

### 17.3. Trạng thái và tính bất biến

Trạng thái run: `draft`, `running`, `needs_review`, `completed`, `completed_with_warnings`, `partial`, `failed`, `cancelled`.

- Run bắt đầu phải chốt snapshot cấu hình, lịch, danh mục, manifest và chỉnh sửa nghiệp vụ.
- Có lỗi mơ hồ ảnh hưởng ý nghĩa dữ liệu: `needs_review`; sau xử lý, tạo snapshot mới có lịch sử rõ ràng.
- `completed` khi toàn bộ ô yêu cầu hợp lệ; `completed_with_warnings` nếu hoàn tất nhưng có cảnh báo; `partial` nếu một phần không có kết quả.
- Cache chỉ dùng lại nếu hash dữ liệu, phương pháp và phần cấu hình phụ thuộc trùng nhau. Đổi lịch hoặc VEE làm mất hiệu lực các kết quả sau bước đó.
- Ghi tệp vào vị trí tạm, kiểm tra rồi đổi tên/đăng ký artifact hoàn chỉnh. Run hỏng/huỷ không làm thay đổi kết quả hoàn thành trước đó.
- Một tiến trình giữ quyền ghi dự án; mở lần hai phải ở chế độ chỉ đọc hoặc báo dự án đang được sử dụng.

Tái lập dùng cùng đầu vào, cấu hình, thứ tự ổn định, phiên bản thuật toán và seed. Số thực giữa hai hệ điều hành có thể sai khác nhỏ; yêu cầu tương đương trong dung sai, không buộc tệp nhị phân giống hệt. Bộ fixture phân cụm chuẩn so sánh thành viên sau chuẩn hoá nhãn; dữ liệu sát biên cụm cần ghi nhận khác biệt nếu có.

## 18. Kiến trúc và stack đề xuất

### 18.1. Lựa chọn kỹ thuật

| Thành phần | Đề xuất | Vai trò |
|---|---|---|
| Ngôn ngữ | Python 3.12.x | Nghiệp vụ, xử lý dữ liệu và kiểm thử dùng chung |
| Desktop | PySide6/Qt 6.x, Qt Widgets | UI native đa nền tảng, bảng phân trang, điều khiển tác vụ |
| Truy vấn dữ liệu lớn | DuckDB 2.x hoặc bản ổn định tương thích được khóa khi scaffold | Đọc CSV/Parquet, join, tổng hợp và xử lý theo phân vùng |
| Định dạng dữ liệu | Parquet/Arrow với PyArrow tương thích | Lưu dữ liệu cột, trao đổi batch |
| Metadata | SQLite qua thư viện chuẩn Python | Dự án, run, cấu hình và trạng thái giao dịch |
| Toán/phân cụm | NumPy 2.x; scikit-learn 1.x tương thích Python đã chọn | Tính vector, K-Means, DBSCAN, chỉ số |
| Biểu đồ | Matplotlib 3.x tích hợp Qt | Biểu đồ và xuất PNG/SVG từ cùng dữ liệu |
| Excel | openpyxl 3.1.x đọc; XlsxWriter 3.x ghi | Đọc nguồn dạng sheet và xuất workbook |
| Cấu hình | JSON, validation có kiểu | Schema có phiên bản; không thực thi cấu hình như mã |
| Kiểm thử/chất lượng | pytest, pytest-qt, Ruff, mypy | Unit, tích hợp, UI và kiểm tra tĩnh |
| Đóng gói | pyside6-deploy/Nuitka, build riêng trên từng nền tảng | Bộ chạy độc lập, không yêu cầu người dùng cài Python |

Các dải phiên bản là lựa chọn thiết kế, chưa phải lockfile. Khi scaffold phải khóa **phiên bản cụ thể** của runtime, thư viện và công cụ build sau khi kiểm tra tương thích trên hai hệ điều hành; không tự lấy bản mới nhất ở mỗi lần build.

Qt cung cấp công cụ đóng gói cho các nền tảng desktop; hình thức ứng dụng và tham số triển khai tham khảo [Qt for Python deployment](https://doc.qt.io/qtforpython-6/deployment/index.html) và [pyside6-deploy](https://doc.qt.io/qtforpython-6/deployment/deployment-pyside6-deploy.html). Mỗi kiến trúc CPU phải có artifact và kiểm thử tương ứng; việc hỗ trợ macOS không tự chứng minh đã hỗ trợ cả Intel lẫn Apple Silicon.

### 18.2. Luồng xử lý và tài nguyên

- UI gọi application service; service tạo job chạy trong worker process, trao đổi cấu hình, tham chiếu artifact và sự kiện tiến độ. Không truyền toàn bộ bảng chu kỳ qua IPC.
- Các module nghiệp vụ có thể chạy không cần UI để kiểm thử và tái lập cùng một pipeline.
- Ưu tiên một bộ máy truy vấn dữ liệu lớn; không thêm song song nhiều thư viện ETL khi chưa có nhu cầu đo được.
- Xử lý theo tháng/phạm vi, đọc theo batch, giới hạn worker và phối hợp số luồng DuckDB/BLAS để tránh nhân số luồng vượt CPU/RAM.
- Phân cụm dùng vector đại diện, tối đa khoảng 7.000 vector trong một ô nếu mọi khách hàng thuộc một ngành; không dùng trực tiếp 122 triệu giá trị làm 122 triệu đối tượng phân cụm.
- Giới hạn memory/query và thư mục spill chỉ là một phần kiểm soát; theo dõi RSS toàn cây tiến trình vì bộ nhớ ngoài buffer manager vẫn tồn tại. Tham khảo [DuckDB memory management](https://www.duckdb.org/2024/07/09/memory-management) và [Out-of-Memory Issues](https://www.duckdb.org/docs/current/guides/performance/oom).
- Thiếu RAM/dung lượng phải kết thúc an toàn và báo giai đoạn/đầu vào liên quan, không trả kết quả bị cắt.

## 19. Hiệu năng và yêu cầu phi chức năng

### 19.1. Quy mô chuẩn

- 7.000 × 365 × 48 = **122.640.000 giá trị khách hàng-chu kỳ** ở độ phân giải 30 phút; năm nhuận là **122.976.000**.
- Số bản ghi MDMS vật lý có thể lớn hơn do nhiều công tơ/kênh; benchmark phải ghi cả số trước và sau tổng hợp về khách hàng.
- Nhập 15 phút làm số giá trị nguồn tăng gấp đôi so với 30 phút; không mặc nhiên coi nằm trong cùng cam kết thời gian.

### 19.2. Mốc đo đề xuất để duyệt

Máy tham chiếu dự kiến: CPU ít nhất 4 lõi vật lý, RAM 16 GB, SSD; dung lượng trống tối thiểu tạm đề xuất 100 GB, đồng thời preflight ước lượng dung lượng nguồn + dữ liệu chuẩn + spill + xuất. Giữ dự phòng cho hệ điều hành; mặc định đề xuất giới hạn DuckDB 4 GB và theo dõi RSS toàn ứng dụng không quá 10 GB trên máy tham chiếu.

| Tác vụ | Mục tiêu đề xuất |
|---|---|
| Toàn pipeline 122,64 triệu giá trị từ CSV/Parquet, bộ benchmark cố định | Không quá 120 phút, không gồm thời gian người dùng rà soát |
| Đổi bộ lọc biểu đồ đã tính/cached | 95% thao tác không quá 2 giây |
| Mở dự án đã hoàn thành và hiện tổng quan | Không quá 10 giây, không quét lại toàn bộ MDMS |
| Phản hồi yêu cầu huỷ | UI ghi nhận trong 1 giây; worker thoát an toàn trong 30 giây ở checkpoint hoặc ngắt tác vụ có hỗ trợ |
| Giao diện khi job đang chạy | Không có tác vụ nặng trên UI thread làm mất phản hồi quá 1 giây |

Đây là **mục tiêu cần benchmark và duyệt**, chưa phải cam kết đã được chứng minh. Ghi cấu hình CPU/OS/RAM/SSD, phiên bản, định dạng nguồn, số dòng, số ngành, thuật toán, thời gian từng bước, RSS toàn cây tiến trình và dung lượng tạm đỉnh. Chạy cả dữ liệu phân bố qua nhiều ngành và trường hợp một ngành chứa toàn bộ 7.000 khách hàng. XLSX được đo riêng vì chi phí đọc khác CSV/Parquet; DBSCAN được đo theo cấu hình eps cụ thể.

### 19.3. Tin cậy, riêng tư và khả dụng

- Không cần tài khoản đám mây để nghiên cứu; không tự gửi dữ liệu khách hàng ra mạng hoặc bật telemetry chứa dữ liệu.
- Không lưu thông tin định danh không cần thiết vào log; bộ xuất tổng hợp mặc định không có tên/địa chỉ khách hàng.
- Xuất danh sách thành viên cụm là lựa chọn riêng, hiển thị rõ phạm vi dữ liệu trước khi lưu.
- Không thực thi macro, mã nhúng hoặc công thức từ tệp nguồn. Ô văn bản xuất Excel/CSV phải được xử lý để không trở thành công thức ngoài ý muốn; giá trị số vẫn giữ đúng kiểu số.
- Không ghi đè tệp nguồn; tên bộ xuất theo run để tránh ghi đè kết quả khác. Dọn cache không xoá nguồn hoặc artifact cần tái lập.
- Dự án chuyển giữa hai hệ điều hành phải đọc được cùng schema. Nâng schema dữ liệu dự án cần bản sao lưu và đường khôi phục; chưa có đồng bộ cộng tác.
- Installer/app bundle chạy được trên máy sạch không cài Python. Ma trận OS/CPU tối thiểu và yêu cầu ký bộ cài cần chốt trước khi đóng gói phát hành.

## 20. Quy cách xuất và báo cáo

### 20.1. Bộ xuất của một run

```text
<export-name>-<run_id>/
  profiles.xlsx
  profiles.csv
  charts/                  # PNG/SVG theo lựa chọn
  quality-summary.csv
  excluded-data.csv        # tóm tắt loại; có thể tách chi tiết nếu lớn
  methodology.md
  run-config.json
  export-manifest.json
```

XLSX gồm các sheet: `Readme`, `Profiles`, `Cluster_Contributions`, `Quality`, `Balance_Checks`, `Parameters`. Thành viên cụm chỉ xuất khi được chọn. CSV có lựa chọn dạng rộng hoặc dài; dữ liệu chi tiết lớn có thể xuất Parquet thay vì ép vào workbook.

Mỗi sheet Excel có giới hạn **1.048.576 dòng** theo [Microsoft Excel specifications](https://support.microsoft.com/en-us/excel/excel-specifications-and-limits). Nếu vượt giới hạn, ứng dụng phải báo trước và tách file/sheet theo quy tắc hoặc chuyển sang CSV/Parquet theo lựa chọn; không cắt dữ liệu âm thầm.

### 20.2. Schema bảng đường cong

Các trường bắt buộc: `run_id`, `organization_scope`, `industry_code`, `industry_name`, `year_month`, `day_type`, `profile_scope`, `profile_kind`, `cluster_id`, `interval_minutes`, `unit`, `result_status`.

- `profile_scope`: `sample_portfolio` hoặc `industry_scaled`.
- `profile_kind`: `overall`, `cluster_contribution` hoặc `normalized_shape`; nhãn chuẩn hoá đi kèm phương pháp Q/U/V.
- Dạng rộng: thêm `slot_01` … `slot_48` hoặc `slot_24`, định nghĩa giờ ở metadata.
- Dạng dài: thêm `slot_index`, `start_time`, `end_time`, `value`.
- Đường cong đại diện không gán một ngày cụ thể giả; `year_month` và `day_type` mô tả ngữ cảnh.
- Mọi biểu đồ phải có đơn vị, phạm vi, tháng, loại ngày, run và trạng thái chất lượng. Hình dạng chuẩn hoá không dùng đơn vị vật lý.

Đầu ra mặc định là **ngày đại diện theo loại ngày**. Nếu sau này cần chuỗi ngày thực của cả tháng, có thể dựng lịch bằng đường cong tương ứng từng ngày; phải gắn nhãn chuỗi mô hình, không gọi là MDMS thực đo.

### 20.3. Nội dung phương pháp xuất kèm

`methodology.md` ghi nguồn đầu vào và checksum, kỳ nghiên cứu/cơ sở thương phẩm, lịch, cách ghép, điều kiện đủ mẫu, VEE/bù, chuẩn hoá, phân cụm, trọng số, công thức suy rộng, ngưỡng, phiên bản và giới hạn diễn giải. Có bảng A/S/α và kiểm tra cân bằng trong kết quả.

Một run có ô không đủ dữ liệu vẫn xuất được các ô hợp lệ, nhưng manifest phải liệt kê ô thiếu và bộ xuất mang trạng thái `partial`. Không xuất toàn bộ như một bộ hoàn chỉnh. Kết quả xem thử được phép xuất có nhãn rõ; không được bỏ nhãn để thành kết quả chính thức.

Lưu dữ liệu tính đầy đủ độ chính xác trong artifact/Parquet. Bảng phục vụ báo cáo có thể làm tròn; sai lệch do làm tròn được báo riêng, không sửa một chu kỳ để che sai số phương pháp.

## 21. Chiến lược kiểm thử và tiêu chí nghiệm thu

### 21.1. Cấp kiểm thử

- Unit: đơn vị, thời gian, lịch, VEE, điều kiện mẫu, chuẩn hoá, trọng số, cộng chu kỳ và suy rộng.
- Tích hợp: nhập → ghép → chất lượng → đường cong → cụm → suy rộng → xuất, với fixture nhỏ có kết quả tính tay.
- Bất biến số học: kiểm tra tổng điện năng, cộng thành phần và tính độc lập với thứ tự tệp; sinh nhiều tổ hợp dữ liệu nhỏ có seed cố định.
- UI với pytest-qt: điều hướng, tham số không hợp lệ, xem chất lượng, job nền/huỷ và trạng thái xuất.
- Hiệu năng: bộ dữ liệu tổng hợp 7.000 khách hàng × 365/366 ngày; không chứa thông tin khách hàng thật.
- Đa nền tảng: chạy cùng fixture và smoke test bản đóng gói trên Windows/macOS, từng CPU được công bố hỗ trợ.
- UAT: chuyên viên thực hiện một nghiên cứu bằng tệp thực đã thống nhất phạm vi, kiểm tra phương pháp, biểu đồ và khả năng đưa vào báo cáo.

### 21.2. Dung sai

- Bảo toàn điện năng và cộng thành phần trên số chưa làm tròn: `abs(actual - expected) <= max(1e-6 kWh, 1e-9 × abs(expected))`.
- Chuẩn hoá Q/U: sai số tuyệt đối không quá `1e-9` đối với tổng/trung bình mong đợi.
- Kết quả đường cong giữa hai hệ điều hành: dung sai đề xuất `atol = 1e-6`, `rtol = 1e-7` trên cùng đơn vị; không dùng để che thay đổi thành viên cụm trên bộ fixture chuẩn.
- Mức hiển thị/làm tròn không được dùng làm số đầu vào của bước tính tiếp theo.

### 21.3. Kịch bản nghiệm thu bắt buộc

| ID | Kịch bản | Kết quả kỳ vọng |
|---|---|---|
| AC-01 | Nhập khách hàng `000123`, tên giống khách hàng khác | Giữ mã, ghép theo khoá, không ghép nhầm theo tên |
| AC-02 | MDMS gắn dấu cuối chu kỳ lúc 00:00 | Quy về chu kỳ/ngày trước đúng theo khai báo |
| AC-03 | Hai giá trị 30 phút 10 và 20 kWh | Xuất 60 phút 30 kWh và công suất trung bình 30 kW |
| AC-04 | Nguồn 60 phút yêu cầu 48 chu kỳ | Báo không đủ độ phân giải, không tạo dữ liệu giả |
| AC-05 | Dòng trùng giống nhau và dòng trùng mâu thuẫn | Khử trùng có truy vết; mâu thuẫn không tự chọn dòng cuối |
| AC-06 | Áp hệ số công tơ và nguồn đã áp sẵn | Hệ số chỉ áp một lần; chưa rõ phải chặn nguồn |
| AC-07 | Thiếu 1–2 chu kỳ nội ngày so với mất cả ngày | Bù ngắn khi đủ điều kiện; không tự bù cả ngày |
| AC-08 | Ngày 0 thật và đoạn đỉnh cao nhưng hợp lệ | Giữ ngày 0; không tự cắt đỉnh; chuẩn hoá 0 là N/A |
| AC-09 | Đổi lịch một ngày lễ và tháng 2 năm nhuận | Đúng loại ngày, đúng số ngày; kết quả sau lịch được tính lại |
| AC-10 | Một khách hàng thiếu dữ liệu Chủ nhật | Không âm thầm để thành phần mẫu giữa các loại ngày khác nhau |
| AC-11 | Khách hàng có số ngày đo khác nhau | Mỗi khách hàng được tính trung bình riêng trước khi tổng hợp |
| AC-12 | Hai khách hàng cùng hình dạng nhưng quy mô khác nhau | Chuẩn hoá có hình dạng giống nhau; đóng góp năng lượng vẫn khác nhau |
| AC-13 | Hai cụm và một nhóm DBSCAN noise | Tổng đóng góp gồm noise khớp đường cong chung từng chu kỳ |
| AC-14 | Chỉ một cụm hoặc toàn vector 0 | Không gọi silhouette sai miền; xử lý trạng thái rõ ràng |
| AC-15 | Mức ngày thường/ngày nghỉ khác nhau | Suy rộng giữ tỷ lệ mức mẫu và cân bằng đúng A tháng |
| AC-16 | Thiếu A, A âm, A=0, S=0 | Đúng từng tình huống mục 12.4, không chia cho 0 |
| AC-17 | So sánh 48 và 24 chu kỳ cùng run | Tổng điện năng ngày/tháng bằng nhau trong dung sai |
| AC-18 | Thay tham số và chạy lại | Có run/config mới; kết quả cũ và nguồn không bị sửa |
| AC-19 | Huỷ hoặc mất dung lượng khi đang ghi kết quả | Không công bố artifact dở; kết quả cũ mở được |
| AC-20 | Xuất lô có ô lỗi hoặc vượt giới hạn XLSX | Có manifest ô thiếu; không cắt dữ liệu hoặc ghi như bộ đầy đủ |
| AC-21 | Chạy lại cùng fixture, seed và cấu hình | Đường cong tương đương; thành viên cụm fixture đúng sau chuẩn hoá nhãn |
| AC-22 | Mở dự án với nguồn bị thay đổi | Phát hiện checksum khác, không dùng nguồn mới như nguồn cũ |
| AC-23 | Bản đóng gói trên máy sạch hai nền tảng | Mở app, nhập, tính, xem, xuất được mà không cài Python |
| AC-24 | Benchmark quy mô chuẩn | Báo thời gian/RSS/disk; so với mục tiêu đã duyệt, không suy diễn từ fixture nhỏ |

Mỗi FR phải được truy vết tới kiểm thử phù hợp. Không dùng tỷ lệ coverage đơn lẻ làm bằng chứng đúng công thức; mọi nhánh tính toán và trường hợp biên được liệt kê phải có kiểm thử có ý nghĩa. Không đặt ngưỡng coverage toàn dự án tuỳ ý trong bước viết spec; nếu cần quality gate số học, thống nhất trước khi triển khai.

## 22. Cấu trúc mã nguồn và quy ước triển khai đề xuất

```text
load-research.md
pyproject.toml
src/load_research/
  __main__.py
  domain/                  # đơn vị, kiểu dữ liệu, công thức và quy tắc thuần
  application/             # pipeline, job, hợp đồng service
  workspace/               # run/config/manifest/artifact
  importers/               # CSV/XLSX/Parquet, ánh xạ và ghép
  calendar/                # lịch và loại ngày
  quality/                 # kiểm tra, bù, eligibility
  profiles/                # đường cong khách hàng và chuẩn hoá
  clustering/              # K-Means/DBSCAN, chẩn đoán và nhãn
  scaling/                 # tổng hợp, suy rộng và kiểm tra cân bằng
  exports/                 # bảng, hình, phương pháp, manifest
  infrastructure/          # DuckDB, SQLite, filesystem và worker
  ui/                      # Qt views/models/controllers
tests/
  unit/
  integration/
  ui/
  fixtures/                # dữ liệu tổng hợp có expected results
  performance/
packaging/                 # cấu hình build Windows/macOS
docs/                      # schema, hướng dẫn và quyết định kỹ thuật sau này
```

### 22.1. Lệnh dự kiến sau khi scaffold

Các lệnh dưới đây **chưa chạy được trong thư mục hiện tại**. Bước triển khai phải tạo package, dependency lock và entry point tương ứng trước khi dùng chúng làm kiểm tra bắt buộc.

```bash
# Trong môi trường ảo Python 3.12 đã tạo và kích hoạt
python -m pip install -e ".[dev]"

# Chạy ứng dụng
python -m load_research

# Kiểm tra thông thường, không vô tình chạy benchmark lớn
python -m pytest tests/unit tests/integration tests/ui -q
python -m ruff check src tests
python -m ruff format --check src tests
python -m mypy src/load_research

# Benchmark riêng; phải có dataset và ghi cấu hình máy trong báo cáo
python -m pytest tests/performance -m performance -v

# Build gói Python
python -m build --wheel

# Build ứng dụng native trên chính nền tảng đích, sau khi cài đủ build deps đã khóa
pyside6-deploy src/load_research/__main__.py --mode standalone --no-install
```

Lệnh tạo installer/ký ứng dụng được bổ sung khi chốt OS/CPU và hình thức phân phối; chưa bịa tên script chưa có. Không chạy cài đặt, build hoặc benchmark chỉ để hoàn thành việc viết tài liệu này.

### 22.2. Code style

- PEP 8, type hints ở ranh giới module; `snake_case` cho hàm/biến, `PascalCase` cho kiểu; formatter là nguồn thống nhất định dạng.
- Dùng tên gắn đơn vị (`energy_kwh`, `interval_hours`), tránh `value` khi ý nghĩa không rõ.
- Công thức thuần không truy cập UI/filesystem; adapter chịu trách nhiệm đọc/ghi.
- Phân biệt `None`/N/A, thiếu và 0; không điền 0 để làm phép tính chạy qua.
- Lỗi có mã, ngữ cảnh và hành động xử lý; bắt lỗi ở ranh giới thích hợp, không `except: pass`.

Ví dụ phong cách cho hợp đồng số học, chưa phải mã đã được triển khai:

```python
import math


def average_power_kw(energy_kwh: float, interval_hours: float) -> float:
    if not math.isfinite(energy_kwh) or energy_kwh < 0:
        raise ValueError("energy_kwh must be finite and non-negative")
    if not math.isfinite(interval_hours) or interval_hours <= 0:
        raise ValueError("interval_hours must be finite and positive")
    return energy_kwh / interval_hours
```

## 23. Ranh giới làm việc

### Luôn thực hiện

- Giữ yêu cầu đã xác nhận, đối chiếu đơn vị/kỳ/phạm vi trước khi tính.
- Lưu phiên bản dữ liệu/phương pháp và lý do thay đổi có tác động nghiệp vụ.
- Kiểm thử công thức và bất biến trước khi đưa vào quy trình nghiên cứu.
- Chạy các kiểm tra phù hợp với thay đổi; báo trung thực những gì đã/chưa xác minh.
- Dùng dữ liệu tổng hợp hoặc dữ liệu được phép cho fixture và tài liệu công khai.

### Cần thống nhất lại khi phát sinh

- Thay đổi mục tiêu, công thức chuẩn, phạm vi chọn mẫu hoặc tiêu chí nghiệm thu đã duyệt.
- Bổ sung gửi dữ liệu ra mạng, kết nối hệ thống khác hoặc cơ chế làm việc nhiều người.
- Thu hẹp hỗ trợ hệ điều hành/CPU so với ma trận được duyệt.
- Nâng schema làm dự án cũ không đọc được hoặc thay đổi chính sách lưu nguồn/tái lập.
- Hạ ngưỡng chất lượng/hiệu năng đã duyệt để làm kết quả có vẻ đạt.

Các lựa chọn triển khai thường lệ phù hợp đặc tả không cần một vòng phê duyệt riêng.

### Không được thực hiện

- Sửa/ghi đè dữ liệu nguồn, xoá dấu vết chỉnh sửa hoặc thay kết quả run đã chốt tại chỗ.
- Tự xem thiếu là 0, tự cắt dữ liệu xuất, gán kW cho đường cong không thứ nguyên.
- Tự loại DBSCAN noise khỏi tổng ngành hoặc cộng sai công suất khi đổi chu kỳ.
- Khẳng định kiểm định đại diện/độ tin cậy khi thiếu cơ sở thiết kế mẫu và bộ đối chứng.
- Bỏ kiểm thử thất bại hoặc giảm tiêu chí âm thầm để báo hoàn thành.

## 24. Rủi ro và cách xử lý

| Rủi ro | Hệ quả | Cách xử lý trong đặc tả |
|---|---|---|
| Mẫu chốt nhưng chưa có hồ sơ thiết kế | Không thể xác nhận tính đại diện chỉ từ dữ liệu mẫu | Báo giới hạn, giữ nguồn trọng số, chưa tuyên bố sai số tổng thể |
| Ngành/kỳ/phạm vi A không khớp MDMS | Suy rộng đúng số học nhưng sai ý nghĩa nghiệp vụ | Bắt buộc khai báo phạm vi, kỳ và mapping |
| Mất dữ liệu lễ hoặc mẫu lệch giữa loại ngày | Hình dạng và tỷ lệ năng lượng bị lệch | Tập khách hàng chung, báo độ phủ và chặn phần thiếu |
| Khách hàng lớn bị loại | Cơ cấu năng lượng và hình dạng ngành thay đổi | Báo thành phần mẫu, đối soát sản lượng khi có |
| Kênh tổng/phụ hoặc CT/PT bị tính hai lần | Tổng năng lượng sai nhiều lần | Hợp đồng kênh/quan hệ đo/hệ số và kiểm thử đếm đôi |
| Phân cụm có vẻ đẹp nhưng không phản ánh ca thực | Giải thích nghiệp vụ quá mức | Nhãn trung tính, chuyên viên xác nhận tên ca |
| Dữ liệu lớn trên máy cá nhân | Hết RAM/disk, UI treo | Xử lý theo phần, worker, cache, preflight và benchmark |
| Hỗ trợ hai OS khác CPU/thư viện | Sai khác tính toán hoặc đóng gói | Lock phiên bản, fixture chung, build/smoke test theo ma trận |

## 25. Điểm cần làm rõ bằng dữ liệu hoặc khi duyệt spec

Những điểm này không ngăn việc lưu bản đặc tả; chúng cần được xử lý trước khi triển khai phần liên quan.

| ID | Nội dung chưa chốt | Mặc định/ảnh hưởng |
|---|---|---|
| OQ-01 | Tệp CMIS/MDMS mẫu, tên cột, kiểu dài/rộng, đơn vị, kênh và quy ước thời gian | Cần trước khi hoàn thiện adapter nhập |
| OQ-02 | MDMS thực tế là 15/30/60 phút; có phải công suất trung bình hay chỉ số tích luỹ | Quyết định khả năng xuất 48 chu kỳ và phạm vi chuyển đổi |
| OQ-03 | Cơ sở tháng thương phẩm và mức khớp kỳ/thông tin CMIS từng mẫu | Quyết định đối soát và nhãn suy rộng |
| OQ-04 | Danh mục ngành, số ngành, phạm vi đơn vị và quan hệ nhiều công tơ | Cần trước khi chốt khoá và mapping nghiệp vụ |
| OQ-05 | Hồ sơ chọn mẫu/trọng số hiện có | Mặc định w=1, thiết kế mẫu chưa xác minh |
| OQ-06 | Lịch lễ, làm bù và quy tắc ngày ngừng sản xuất của đơn vị | Lịch nhập/hiệu chỉnh có phiên bản |
| OQ-07 | Duyệt ngưỡng VEE/đủ mẫu, tập chung, phân cụm và công thức suy rộng đề xuất | Các giá trị hiện tại là mặc định đề xuất, chưa phải quy định đơn vị |
| OQ-08 | Phiên bản Windows/macOS, Intel/Apple Silicon, CPU/RAM/SSD và quyền cài đặt | Cần chốt ma trận trước khi đóng gói và benchmark nghiệm thu |
| OQ-09 | Mẫu bảng/hình báo cáo, cách gọi “ngành nghề” và nhãn nhóm hành vi | Mặc định XLSX/CSV, PNG/SVG và thuật ngữ trong tài liệu |
| OQ-10 | Duyệt stack, mục tiêu 120 phút/10 GB RSS và cách đo thời gian tiết kiệm | Cần benchmark thực và UAT, không coi đã đạt |

## 26. Nguồn tham khảo và cách sử dụng

Các nguồn được đối chiếu ngày 23/10/2026. Mục tiêu sản phẩm lấy từ yêu cầu người dùng; công thức tổng hợp/suy rộng, ngưỡng và kiến trúc là đề xuất trong tài liệu, không được mô tả như trích nguyên một chuẩn bên ngoài.

1. [EIA — Measuring electricity](https://www.eia.gov/energyexplained/electricity/measuring-electricity.php): phân biệt đơn vị công suất và điện năng.
2. [AEMO — Metrology Procedures and Unmetered Loads](https://www.aemo.com.au/energy-systems/electricity/national-electricity-market-nem/market-operations/retail-and-metering/metrology-procedures-and-unmetered-loads): tham khảo khái niệm kiểm tra, thay thế/ước lượng và quản lý chất lượng đo đếm. Không áp dụng tự động như quy định tại Việt Nam.
3. [EPRI — Identifying Commercial Demand Response Candidates Using Load Profile Clustering, 3002018090](https://restservice.epri.com/publicdownload/000000003002018090/0/Product): ví dụ chuẩn hoá hình dạng phụ tải và phân cụm.
4. [scikit-learn — Clustering](https://scikit-learn.org/stable/modules/clustering.html): cơ sở thuật toán K-Means/DBSCAN và lưu ý tài nguyên.
5. [scikit-learn — silhouette_score](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.silhouette_score.html): điều kiện áp dụng chỉ số đánh giá phân cụm.
6. [Statistics Canada — Use of nonprobability samples for official statistics, state of the art](https://www150.statcan.gc.ca/n1/pub/12-001-x/2025001/article/00008-eng.htm): giới hạn và nguy cơ sai lệch trong suy luận từ mẫu khi thiếu cơ sở lựa chọn.
7. [DuckDB — Memory Management](https://www.duckdb.org/2024/07/09/memory-management), [Out-of-Memory Issues](https://www.duckdb.org/docs/current/guides/performance/oom): kiểm soát bộ nhớ và xử lý lớn hơn bộ nhớ.
8. [Qt for Python — Deployment](https://doc.qt.io/qtforpython-6/deployment/index.html), [pyside6-deploy](https://doc.qt.io/qtforpython-6/deployment/deployment-pyside6-deploy.html): phương án đóng gói desktop.
9. [Microsoft — Excel specifications and limits](https://support.microsoft.com/en-us/excel/excel-specifications-and-limits): giới hạn dòng khi nhập/xuất workbook.

## 27. Điều kiện chuyển sang lập kế hoạch

Bản đặc tả được xem là sẵn sàng lập kế hoạch khi người dùng duyệt mục tiêu, ranh giới module, quy trình và các đề xuất phương pháp chính; các câu hỏi phụ thuộc tệp thực được gắn rõ với bước cần giải quyết. Chỉ triển khai bộ nhập thực tế sau khi có thông tin nguồn cần thiết; chỉ cam kết hiệu năng hoặc ma trận phát hành sau khi đã chốt điều kiện đo/kiểm thử.

Việc lưu tài liệu này hoàn thành yêu cầu viết spec. Kế hoạch công việc, task triển khai và mã ứng dụng được thực hiện ở bước tiếp theo sau khi người dùng duyệt hoặc yêu cầu điều chỉnh đặc tả.

## 28. Bổ sung được chốt ngày 26/10/2026

Phạm vi mở rộng: ẩn cửa sổ dòng lệnh khi mở desktop Windows; Việt hóa lỗi nhập và nội dung trình bày/báo cáo; mở rộng tab Kết quả và tài liệu phương pháp. Bản đồ khả năng và thứ tự ở `tasks/plan.md`; nghiệm thu T35–T48 trong `tasks.md`.

- Cho chọn nhiều mã ngành và nhiều loại ngày, xem cả đường tổng hợp và các đường so sánh. Thành phần phụ tải là một tập mã ngành do người dùng chọn/đặt tên; toàn đơn vị là tất cả ngành thuộc phạm vi có thể xác minh của nghiên cứu. Các tập phải khử mã trùng; nhóm hành vi vẫn là kết quả phân cụm bên trong ngành/loại ngày.
- Với tập ngành G và tập loại ngày T: E_G,t,k = tổng_g E_g,t,k; E_G,T,k = tổng_t(N_t × E_G,t,k) / tổng_t N_t. Số ngày bằng 0 là không áp dụng. Tổng ngành thiếu dữ liệu phải được ghi rõ/chặn đường tổng đầy đủ. Giữ riêng A/S/alpha ngành; không suy rộng lại tổng đã suy rộng.
- Hai chế độ suy rộng ngày: (1) lịch ngày d dùng E_g,type(d),k; (2) biến thiên ngày dùng F_g,d,k = tổng_i(w_i × x_sau_xử_lý_i,d,k), D_g = tổng_d,k F_g,d,k, beta_g = A_g/D_g, E_ngày_g,d,k = beta_g × F_g,d,k. Chế độ (2) yêu cầu cohort cố định và mọi ngày đều đủ điều kiện; không tự bù ngày thiếu. Hai mô hình có thể khác hệ số, phải ghi rõ phương pháp và kiểm tra cân bằng tháng.
- Xem và xuất mẫu trước/sau VEE, mô hình ngày lịch và mô hình biến thiên ngày; phân biệt số liệu nguồn, giá trị ước lượng và mô hình. Hỗ trợ kW/kWh, 24/48 chu kỳ theo độ phân giải thực có. Không đổi ngày thiếu thành số 0 và không cộng trực tiếp kW khi đổi chu kỳ.
- Biểu đồ co giãn theo canvas sau resize và sau mọi đổi bộ lọc; click vào điểm xem khoảng thời gian, tên đường, trị số và đơn vị. Bộ xuất phải khớp chính xác phép tổng hợp đang xem, có phạm vi/ngày/phương pháp/độ phủ và công thức.
- Nội dung người dùng đọc và báo cáo GUI dùng tiếng Việt chuyên ngành: điện năng tác dụng, công suất trung bình chu kỳ, điện năng thương phẩm, hệ số suy rộng, tập mẫu chung, độ phủ dữ liệu và đóng góp nhóm. Tên trường kỹ thuật trong nguồn/schema/manifest vẫn được giữ để ánh xạ và tái lập, kèm diễn giải tiếng Việt.
- Tài liệu mới giải thích đầy đủ mọi chỉ tiêu ở tab Kết quả, công thức đơn vị/thời gian/chuẩn hóa/phân cụm/suy rộng/tổng hợp/ngày, điều kiện áp dụng, số 0/thiếu và ví dụ số đối chiếu được bằng test.

## 29. Bổ sung ngày 27/10/2026 — khoảng ngày, danh mục và khách hàng

- Biểu đồ tự xác định dải trục Y theo các đường đang hiện, có khoảng đệm, không
  ép về 0 hoặc cắt giá trị âm. Có danh sách tên đường để bật/tắt riêng và hiện/ẩn
  tất cả. Bật/tắt chỉ đổi hình, bảng số liệu giữ đầy đủ; click bỏ qua đường ẩn.
- Có chế độ từ ngày đến ngày, bao gồm hai đầu, mỗi ngày từ 00:00 đến 24:00;
  có thể xuyên tháng trong phạm vi các tháng đã nghiên cứu. Trục thời gian ghi
  ngày/giờ, ngày không thuộc bộ lọc được ngắt đường thay vì nối qua khoảng trống.
  Hai mô hình ngày vẫn dùng α/β của từng ngành-tháng từ đầy đủ tháng; không tính
  hệ số từ riêng khoảng đang xem. Đổi 48/24 chu kỳ bảo toàn điện năng từng ngày.
- Chuẩn hóa trên toàn chuỗi của khoảng chọn sau khi tổng hợp vật lý/chuyển chu kỳ.
  Chuỗi thiếu chưa có hình dạng chuẩn hóa; không loại ô thiếu để giả đủ dữ liệu.
  Metadata và thành viên xuất giữ đúng phạm vi ngành/loại ngày riêng từng tháng.
- Nhập danh mục gồm Mã ngành nghề, Tên ngành nghề, Mã thành phần, Tên thành phần
  phụ tải (chấp nhận tên cột kỹ thuật tương đương). Mỗi ngành thuộc một thành phần;
  mã và tên phải nhất quán. Có CSV/XLSX mẫu, chọn sheet/dấu phân cách và xem trước.
  Danh mục lưu riêng theo phiên bản/checksum tại dự án, không sửa snapshot đã chốt;
  báo cáo ghi đúng phiên bản đã dùng. Chọn thành phần xác định chính xác tập ngành;
  vẫn suy rộng từng ngành rồi cộng, không tạo một hệ số chung. Ngành thiếu vẫn thiếu.
- Ẩn bộ chọn Nhóm không cần thiết trên hàng bộ lọc. Các đường đóng góp nhóm hành
  vi và nhãn đã lưu vẫn xem được bằng điều khiển đường dữ liệu.
- Có tìm mã khách hàng mẫu, xem một ngày hoặc khoảng ngày trước/sau VEE, cùng
  lý do bù, ngày cho, cờ chất lượng và điều kiện ngày. Đọc từ catalog/cache xác
  minh và cấu hình đã lưu theo từng tháng; không nhân trọng số hoặc hệ số suy rộng.
  Khách hàng bị loại khỏi cohort vẫn tra cứu được. Ngoài thời gian hiệu lực ghép
  công tơ là thiếu, không phải 0; VEE tra cứu không thay đổi tập mẫu hoặc kết quả run.
- Xử lý dữ liệu ngày/khách hàng và nhập danh mục trong worker có hủy. Câu trả lời
  worker phải khớp run, token và toàn bộ phạm vi đang chọn để không hiện dữ liệu cũ.

## Bổ sung 28/10/2026 — thời điểm MDMS và VEE hoàn chỉnh

- Nguồn mới mặc định làm tròn thời điểm xuống đầu khoảng chu kỳ nguồn trước đó
  trong múi giờ khai báo, kể cả khi lệch gần hết chu kỳ; có lựa chọn kiểm tra
  nghiêm ngặt. Hiệu chỉnh trước khi áp quy ước thời điểm đầu/cuối. Xung đột sau
  ghép bị từ chối; giữ nhật ký nguồn và cho phép xuất toàn bộ trong kỳ nghiên cứu.
- VEE hoàn chỉnh chỉ dùng căn cứ cùng khách hàng, tháng và loại ngày, dựa trên
  quan sát gốc đủ số ngày cho; ghi phương pháp, ngày cho và hệ số. Điểm chặn bù,
  thiếu căn cứ hoặc hệ số ngoài giới hạn không được tự tạo. Khách hàng-tháng còn
  chu kỳ thiếu bị loại khỏi tập mẫu và báo lý do; ngưỡng độ phủ và tỷ lệ ước tính
  vẫn áp dụng. 100% đầy đủ không có nghĩa 100% là số đo thực.
- Lần nghiên cứu mới ghi phiên bản phương pháp `class-profile-v2` và tham số;
  cấu hình cũ thiếu các trường mới giữ quy tắc kiểm tra thời điểm, ghép mã và VEE
  cũ khi nạp/chạy lại. Snapshot kết quả đã lưu không bị sửa.
