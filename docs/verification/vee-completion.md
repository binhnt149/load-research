# Kiểm chứng hiệu chỉnh thời điểm và VEE hoàn chỉnh

Ngày 28/10/2026; mã nguồn tại workspace, chưa phát hành bản cài mới.

- Quy tắc chu kỳ nguồn được kiểm thử với mốc lệch, đầu/cuối chu kỳ, đổi ngày,
  múi giờ, xung đột sau ghép, cache và cấu hình cũ. Nhật ký giữ cả ranh giới
  phụ, cùng SHA-256 để phân biệt các nguồn trùng tên.
- Fixture VEE kiểm tra bù từ quan sát gốc cùng khách hàng và loại ngày, mất cả
  ngày, thiếu căn cứ, điểm cấm bù, hệ số ngoài ngưỡng, đánh dấu ước tính, lưu
  ngày cho và loại khách hàng-tháng còn thiếu. Cấu hình cũ giữ quy tắc cũ.
- Kiểm thử Qt chạy với nền tảng offscreen. Tệp CSV nhật ký được kiểm tra chặn
  công thức trong mã nguồn; cache bị sửa bị từ chối khi xuất. Rà soát độc lập
  phát hiện tương thích mã công tơ, nhật ký ranh giới phụ và SHA-256 nguồn; các
  vấn đề này được sửa và có kiểm thử hồi quy.
- Toàn bộ 357 bài kiểm thử đạt, không lỗi, không bỏ qua; Ruff check/format,
  mypy (59 module) và build wheel đạt. 59 module Python trong wheel khớp mã
  nguồn. Vòng Red/Green của các thay đổi được lưu trong `ci-results/` cục bộ.
- Benchmark dữ liệu giả lập đủ số liệu: 100 khách hàng × 1 tháng, 148.800 chu
  kỳ; xử lý và xuất 7,50 giây, RSS đỉnh đo được khoảng 394 MiB, sai số cân bằng
  lớn nhất 1,87×10⁻⁹ kWh trên máy macOS thử nghiệm. Đây là phép đo nhỏ, không
  phải xác nhận thời gian xử lý với nhiều dữ liệu thiếu hoặc quy mô đầy đủ.

Chưa kiểm thử 7.000 khách hàng × 12 tháng và chưa build/chạy bản native Windows
hoặc macOS trong lượt thay đổi này. Các điều kiện E01/E02/E03 trong kế hoạch vẫn
để mở; kết quả offscreen và wheel không thay thế kiểm thử bản cài trên máy sạch.

Tham khảo nền về các loại giá trị thay thế của AEMO: [Substitution types](https://tech-specs.docs.public.aemo.com.au/Content/TSP_MSATS_September2024/Substitution_Types.htm?TocPath=Electricity%7CMSATS%7CMSATS+Archive%7CSeptember+2024%7C_____8).
Đây là nguồn tham khảo cách phân loại, không phải xác nhận phương pháp này tuân
thủ quy trình hoặc quy định đo đếm của AEMO.
