"""Vietnamese calculation reference bundled with desktop and exported reports."""

CALCULATIONS = """# Cách tính kết quả nghiên cứu phụ tải

Phiên bản phương pháp hiển thị: 27/10/2026. Các đường suy rộng là mô hình ước tính,
không phải phép đo thực tế của toàn bộ khách hàng. Dữ liệu và tham số của mỗi lần
nghiên cứu được giữ nguyên; thay tham số phải tạo lần nghiên cứu mới.

## 1. Đơn vị, chu kỳ và lịch

Toàn bộ phép tính dùng điện năng tác dụng kWh trên từng khoảng thời gian.
P[k] = E[k] / Δt (kW), Δt = 0,5 giờ cho 48 chu kỳ hoặc 1 giờ cho 24 chu kỳ.
Chu kỳ đánh số từ 1; chu kỳ 1 bắt đầu lúc 00:00, chu kỳ cuối kết thúc lúc 24:00.
Đổi 48 thành 24 chu kỳ bằng cộng hai điện năng kWh liền nhau; công suất 60 phút
bằng trung bình hai công suất 30 phút. Không chia nhỏ dữ liệu giờ thành nửa giờ.

Loại ngày gồm ngày làm việc, thứ Bảy, Chủ nhật, ngày lễ. Phân loại theo lịch đã
lưu trong lần nghiên cứu: ghi đè ngày được ưu tiên trước ngày lễ, rồi ngày tuần.
Ngày làm việc ở đây là loại ngày trong lịch, không khẳng định khách hàng làm việc.
N[t] là số ngày thực tế của loại t trong tháng theo lịch này. Không suy diễn lịch
lễ từ hệ điều hành. Ngày lễ/ghi đè phải được người dùng cung cấp và xác minh.

## 2. Tập mẫu chung và làm sạch

Chỉ khách hàng đã chốt mẫu được xử lý. Một khách hàng đủ điều kiện tháng khi độ
phủ nguồn ban đầu đạt ngưỡng và có đủ ngày hợp lệ cho tất cả loại ngày xuất hiện
trong tháng. Số ngày tối thiểu cho mỗi loại là min(ngưỡng đã đặt, N[t]). Tập khách
hàng và trọng số phải giống nhau giữa các loại ngày của cùng ngành-tháng.

Ngày hợp lệ khi tất cả chu kỳ sau xử lý đều hữu hạn và tỷ lệ chu kỳ ước tính
không vượt ngưỡng. VEE chỉ nội suy khoảng ngắn nằm giữa quan sát có thể dùng;
khoảng dài hơn được xem xét bằng ngày tương đồng với số ngày cho, độ phủ chung
và giới hạn hệ số đã lưu. Không bù cả ngày bị mất. Các ô thiếu vẫn là ô thiếu.
Chất lượng nguồn không biết được giữ thành cảnh báo, không tự coi là nguồn tốt.
MDMS có thể đã chứa số liệu ước tính; “mẫu nguồn trước VEE” không đồng nghĩa với
mọi chu kỳ đều là số đo thực. Nhật ký ghi từng giá trị bù và ngày cho.

## 3. Biểu đồ đại diện ngành và nhóm hành vi

x[i,t,k] = trung bình điện năng chu kỳ k của các ngày hợp lệ loại t của khách
hàng i. Đây là trung bình theo khách hàng trước khi cộng mẫu, tránh để khách
hàng có nhiều ngày quan sát chi phối hình dạng. w[i] là trọng số mẫu đã khai báo
(mặc định 1 khi không có trọng số thiết kế).

F[g,t,k] = Σ(i thuộc tập mẫu ngành g) w[i] × x[i,t,k].
F[g,t,c,k] cộng riêng khách hàng thuộc nhóm hành vi c của loại ngày t.
Σc F[g,t,c,k] = F[g,t,k]. Phân cụm dùng hình dạng chuẩn hóa của từng khách hàng;
K-Means/DBSCAN và các tham số được lưu theo lần nghiên cứu. Nhãn nhóm không
chứng minh ca sản xuất; tên nghiệp vụ cần cơ sở đối chiếu của người nghiên cứu.
Mã nhóm chỉ có nghĩa trong ngành-tháng-loại ngày; nhóm 1 ở hai ngành là hai nhóm.

S[g,m] = Σt N[t] × Σk F[g,t,k] là điện năng nền mẫu theo lịch tháng.
A[g,m] là điện năng thương phẩm toàn ngành được nhập cho tháng.
α[g,m] = A[g,m] / S[g,m]. E[g,t,k] = α[g,m] × F[g,t,k].
Đóng góp suy rộng nhóm = α × F[g,t,c,k], dùng cùng α của ngành-tháng.
Kiểm tra cân bằng: |Σt N[t] Σk E[g,t,k] − A[g,m]|.
Sai số cho phép max(10⁻⁶ kWh, 10⁻⁹ × |A|). Tổng đóng góp nhóm cũng phải khớp
đường chung tại mỗi chu kỳ trong sai số này.

Thiếu A: vẫn xem mẫu, chưa có đường suy rộng. S=0 và A>0: chưa có hình dạng
dương để suy rộng. A=0 và S>0: đường suy rộng bằng 0 kèm cảnh báo. A=S=0:
đường vật lý bằng 0, α không xác định; không có hình dạng chuẩn hóa.
Ít khách hàng hơn ngưỡng: kết quả chỉ để xem trước và phải đọc trạng thái mẫu.
Thương phẩm theo kỳ hóa đơn khác tháng lịch vẫn có thể là cơ sở quy mô mô hình;
không gọi đó là đối soát đo đếm tháng lịch và phải trình bày cơ sở kỳ tương ứng.

## 4. Nhiều ngành, thành phần phụ tải và toàn đơn vị

G là tập mã ngành được chọn, loại bỏ mã trùng. Thành phần phụ tải là G được đặt
tên bởi người dùng. Toàn đơn vị dùng toàn bộ danh mục ngành trong phạm vi nghiên
cứu, gồm cả mã có thương phẩm nhưng thiếu mẫu. Nếu chưa chứng minh đủ danh mục
(ví dụ lần chạy cũ không lưu phạm vi), không khẳng định tổng toàn đơn vị đầy đủ.

E[G,t,k] = Σg E[g,t,k]. T là tập loại ngày được chọn có N[t]>0.
E[G,T,k] = Σt N[t] × E[G,t,k] / Σt N[t]. Đây là một ngày đại diện bình quân theo
lịch của lựa chọn. Đường so sánh từng ngành dùng cùng trọng số N, do đó cộng lại
đúng đường chung ở chế độ vật lý. Đường so sánh từng loại ngày là E[G,t,k], chưa
nhân trọng số N; các đường loại ngày không cộng trực tiếp thành đường chung.
Đóng góp hành vi trên biểu đồ gộp = N[t] × E[g,t,c,k] / Σt N[t].

Điện năng của các ngày đã chọn = Σt N[t] × Σk E[G,t,k]. Tổng thương phẩm tháng
= Σg A[g,m], luôn là toàn tháng dù chỉ chọn thứ Bảy. Hai số khác nhau khi chỉ
chọn một phần loại ngày. Không lấy trung bình hoặc cộng các α thành một α chung.
Thiếu bất kỳ ngành/loại ngày bắt buộc: đường tổng chưa khả dụng; các đường ngành
còn đủ dữ liệu vẫn xem được. Không thay ngành thiếu bằng đường 0.

Ví dụ: tháng có 20 ngày làm việc, 10 thứ Bảy. Điện năng mỗi chu kỳ của ngành 01
là 2/4 kWh và ngành 02 là 10/20 kWh. Gộp: 12/24 kWh; bình quân lịch:
(20×12+10×24)/30 = 16 kWh/chu kỳ 30 phút = 32 kW.
Điện năng tháng = 16×48×30 = 23.040 kWh. Chỉ thứ Bảy: 11.520 kWh.
Đổi 60 phút: 32 kWh/chu kỳ = 32 kW, điện năng tháng không đổi.

## 5. Chuẩn hóa

Chuẩn hóa sau khi cộng điện năng vật lý của phạm vi đã chọn và đổi độ phân giải.
Theo trung bình: u[k]=E[k]/mean(E). Theo đỉnh: u[k]=E[k]/max(E).
Theo tổng: u[k]=E[k]/ΣkE[k]. Tất cả không có thứ nguyên, ghi p.u.; không ghi kW.
Mỗi đường so sánh/đóng góp được chuẩn hóa riêng, nên chúng không còn cộng được
thành đường chung. Vì vậy không xếp chồng các đường chuẩn hóa. Đường 0 không
có hình dạng chuẩn hóa, hiển thị chưa khả dụng thay vì chia cho 0.

## 6. Biểu đồ từng ngày: hai phương pháp suy rộng

Mẫu nguồn và mẫu sau VEE dùng đúng khách hàng của tập mẫu chung đã lưu cùng w[i].
Đường chung theo phạm vi mẫu sử dụng mẫu sau VEE của đúng ngày; theo phạm vi suy
rộng sử dụng phương pháp mô hình đã chọn. Các đường mẫu trước/sau VEE được ghi
nhãn riêng để đối chiếu với mô hình. Mẫu ngày sau xử lý Q[g,d,k] = Σi w[i] × q[i,d,k]. Bất kỳ giá trị thiếu nào trong
phạm vi được cộng cũng làm chu kỳ tổng tương ứng chưa khả dụng. Không dùng tổng
bỏ qua giá trị thiếu để trình bày như một tập mẫu đầy đủ. Cờ đủ điều kiện ngày
là tất cả khách hàng của tập mẫu chung đều có ngày đủ điều kiện.

Phương pháp 1 — Đại diện theo loại ngày: Erep[g,d,k]=E[g,t(d),k]. Hai ngày cùng
loại có cùng đường đại diện. Lặp theo toàn bộ ngày lịch bảo toàn A. Đây là chuỗi
mô hình theo lịch, không thể hiện biến thiên thực tế giữa các ngày cùng loại.

Phương pháp 2 — Giữ biến thiên ngày: D[g,m]=ΣdΣk Q[g,d,k], β[g,m]=A[g,m]/D[g,m].
Evar[g,d,k]=β[g,m]×Q[g,d,k]. Chỉ tính β khi mọi ngày trong tháng của toàn bộ tập
mẫu chung đủ điều kiện, không còn giá trị thiếu. Một ngày không đạt làm phương
pháp này chưa khả dụng cho cả tháng; có thể chuyển sang phương pháp 1. Không bù
cả ngày để làm cân bằng. D=0,A>0: chưa có mô hình; thiếu A: chưa có mô hình;
A=D=0: dùng hệ số quy ước 0 để đường vật lý bằng 0, không có hình dạng chuẩn hóa.
β khác α vì D dùng từng ngày, còn S dùng trung bình theo khách hàng và loại ngày.

Ví dụ Q hai ngày có 48 chu kỳ với mức 1 và 5 kWh/chu kỳ, A=144 kWh: D=288 kWh,
β=0,5; hai đường suy rộng lần lượt 0,5 và 2,5 kWh/chu kỳ; tổng vẫn 144 kWh.
Với nhiều ngành, suy rộng từng ngành bằng α hoặc β riêng rồi cộng; tuyệt đối
không nhân tổng mẫu của các ngành với một hệ số chung không có cơ sở.

## 7. Cách đọc các bảng kiểm tra

- Số khách hàng: số mã khách hàng phân biệt trong tập mẫu hoặc nhóm; không nhân w.
- Số ngày dùng: số ngày hợp lệ dùng tính x của khách hàng/loại ngày đó.
- Tỷ lệ ước tính: số chu kỳ có cờ ước tính / tổng chu kỳ của các ngày đã dùng.
- Tỷ lệ không rõ chất lượng: chu kỳ nguồn có giá trị nhưng không biết chất lượng /
  tổng chu kỳ các ngày đã dùng. Hai tỷ lệ này có thể chồng lấn, không cộng thành 100%.
- Điện năng mẫu ngày của nhóm: Σk F[g,t,c,k]. Tỷ trọng điện năng mẫu của nhóm:
  điện năng nhóm / tổng điện năng mẫu ngày loại t, chưa phải tỷ lệ số khách hàng.
- Chu kỳ đỉnh: argmax của điện năng nhóm + 1; nếu bằng 0 thì chưa xác định.
- Hệ số phụ tải: mean(F nhóm) / max(F nhóm); không xác định khi đỉnh bằng 0.
- Silhouette: độ tách biệt các cụm theo không gian hình dạng, trong [-1,1]; gần 1
  tách biệt tốt hơn; không phải độ chính xác suy rộng hay bằng chứng ca sản xuất.
- Chu kỳ dự kiến/chất lượng toàn tháng: cộng toàn bộ khách hàng đầu vào của tháng,
  có thể rộng hơn các ngành/loại ngày đang xem. Không gọi là chất lượng lựa chọn.
- Độ phủ ban đầu: chu kỳ nguồn hữu hạn / tổng chu kỳ dự kiến khách hàng-tháng.
- Ngày 0, ngày phẳng, ngoại lệ MAD: cảnh báo thống kê từ quan sát nguồn; không tự
  xóa hoặc thay thế giá trị. MAD không tính được khi thiếu ngày/độ phân tán bằng 0.
- Đối soát CMIS: chỉ so điện năng mẫu CMIS và MDMS nguồn khi MDMS đủ cả tháng và
  cơ sở CMIS là tháng lịch. Chênh lệch = MDMS nguồn − CMIS; không ép số liệu khớp.
- So sánh lần chạy: chênh lệch chu kỳ = lần hiện tại − lần so sánh; xem cả thay đổi
  tham số, lịch, nguồn và tập khách hàng trước khi diễn giải nguyên nhân.

## 8. Xuất và truy vết

Bảng CSV/XLSX chứa giá trị số gốc (không làm tròn theo nhãn màn hình), ngày/tháng,
phương pháp, phạm vi, đơn vị và số phút/chu kỳ. Ô thiếu để trống, số 0 giữ là 0.
Manifest lưu bộ lọc, các hệ số riêng, tình trạng thiếu và SHA-256 từng tệp. Snapshot
nghiên cứu, danh mục mẫu và dữ liệu ngày được kiểm tra checksum khi đọc. Lần chạy
cũ dựng lại chuỗi ngày từ cache đo đếm đã xác minh; không sửa snapshot đã chốt.
CSV chặn ô công thức từ chuỗi nguồn; XLSX không diễn giải chuỗi thành công thức/URL.
Không suy luận khoảng tin cậy đại diện quần thể nếu chưa có thiết kế mẫu xác suất.

## 9. Khoảng ngày, danh mục thành phần và từng khách hàng

Khoảng từ–đến bao gồm hai đầu, từ 00:00 ngày đầu đến 24:00 ngày cuối. Từng ngày
vẫn có 48/24 chu kỳ; bảng dài ghi ngày + chu kỳ, bảng rộng có một hàng/đường/ngày.
Trục thời gian dùng ngày/giờ. Khi lọc loại ngày, đường bị ngắt tại các ngày bị bỏ
qua; không nội suy hoặc nối thẳng qua ngày đó. Tháng không thuộc nghiên cứu không
được tự điền. Biểu đồ khách hàng luôn đọc mọi loại ngày trong khoảng đã chọn.

Mỗi ngày dùng đúng Erep hoặc Evar của ngành-tháng tương ứng. α và β vẫn tính từ
đầy đủ tháng, không tính lại từ riêng khoảng đang xem. Điện năng lựa chọn là tổng
điện năng các chu kỳ/ngày thực sự được chọn. Thương phẩm các tháng là tổng A của
các ngành-tháng liên quan, không phải A đã phân bổ riêng cho khoảng. Hai số thường
khác nhau. Danh mục ngành và thành viên xuất giữ đúng ngành/loại ngày riêng từng
tháng, kể cả khi danh mục hoặc lịch thay đổi giữa hai tháng.

Chuẩn hóa của khoảng ngày áp dụng sau tổng hợp/chuyển chu kỳ, trên toàn chuỗi
được chọn. Ví dụ hai ngày 48 chu kỳ ở mức 2 và 6 kWh: chuẩn hóa trung bình cho
mức 0,5 và 1,5; không chuẩn hóa riêng mỗi ngày thành 1. Chuỗi còn ô thiếu hoặc
đường 0 không có hình dạng chuẩn hóa. Giá trị vật lý gốc vẫn xem được khi bỏ
chuẩn hóa; bảng Chi tiết VEE luôn giữ kWh ở chu kỳ nghiên cứu ban đầu.

Danh mục nhập có bốn cột: Mã ngành nghề, Tên ngành nghề, Mã thành phần, Tên thành
phần phụ tải; cũng chấp nhận industry_code, industry_name, component_code,
component_name. Mỗi ngành thuộc một thành phần, tên nhất quán theo mã; dòng trùng
hoàn toàn được gộp, dòng xung đột bị từ chối. Mã là chuỗi, giữ số 0 đầu. Chọn
thành phần xác định tập ngành để cộng các đường đã suy rộng riêng theo mục 4.
Không dùng một hệ số chung cho thành phần. Ngành chưa có mẫu/biểu đồ vẫn được
báo thiếu, không bị bỏ khỏi danh mục để tạo một tổng giả đầy đủ.

Mỗi lần nhập danh mục tạo phiên bản trong dự án, có checksum nội dung chuẩn.
Không cần chạy lại VEE chỉ để đổi cách nhóm ngành. Kết quả nghiên cứu gốc không
bị sửa; báo cáo đóng băng phiên bản/checksum và nội dung danh mục đã áp dụng.
Danh mục vẫn dùng được khi tệp nhập ngoài đã mất và được giữ trong sao lưu dự án.

Tra cứu khách hàng dùng đúng mã trong catalog/cache đã xác minh, theo tham số VEE
và lịch của lần nghiên cứu. Không nhân w, α hoặc β; không dùng tổng ngành để đại
diện khách hàng. Khách hàng bị loại khỏi cohort vẫn có thể tra cứu. Với quan hệ
công tơ chỉ hiệu lực một phần tháng, phần ngoài hiệu lực là thiếu và bị chặn bù,
không phải điện năng 0. VEE của tra cứu được dựng lại từ dữ liệu và cấu hình đã
lưu; việc xem khách hàng bị loại không đưa họ trở lại cohort hoặc đổi snapshot.
Cờ đủ điều kiện và độ phủ toàn tháng phải được đọc cùng số liệu. Ngày có đủ giá
trị sau VEE vẫn có thể không đủ điều kiện nghiên cứu do tỷ lệ ước lượng quá cao.

Đường dữ liệu… bật/tắt từng đường và tự điều chỉnh trục Y theo đường đang hiện;
không ép trục về 0. Dữ liệu âm (ví dụ chênh lệch hai lần nghiên cứu), hằng số, 0
và khoảng thiếu đều được giữ đúng. Bật/tắt chỉ thay hình, không xóa bảng số liệu.
PNG/SVG xuất từ lựa chọn ghi lại trạng thái ẩn đường, CSV/XLSX vẫn đủ các đường.
Với biểu đồ chồng, ẩn một dải giữ nguyên vị trí các dải khác để đối chiếu với
đường tổng; không tính lại tổng của riêng các dải đang hiện.
Đổi phạm vi/bộ lọc thiết lập lại lựa chọn đường để không mang nhầm trạng thái sang
ngành hoặc khách hàng khác. Click ghi ngày/chu kỳ/giá trị của đường đang hiện;
hover phần thông tin để đọc đầy đủ khi nhiều đường, hoặc dùng bảng bằng bàn phím.
Nút Bảng ẩn/hiện biểu đồ để mở rộng bảng số liệu trên cửa sổ nhỏ.

Trong mục 3 · Kết quả: Danh mục thành phần… cho nhập/xem trước hoặc lấy mẫu;
chọn Từ ngày đến ngày hoặc Khách hàng mẫu, chọn Từ/Đến, phương pháp hoặc mã KH,
rồi Nạp khoảng ngày/Nạp khách hàng. Đổi đơn vị/chu kỳ/chuẩn hóa dùng dữ liệu nền
đã nạp. Đổi phạm vi/ngày/phương pháp/mã KH cần nạp lại; câu trả lời nền của lựa
chọn cũ bị bỏ qua. Xuất lựa chọn tạo báo cáo đúng khoảng, kèm customer-vee.csv khi
tra cứu khách hàng. Bộ chọn Nhóm được ẩn; đường đóng góp và nhãn nhóm vẫn còn,
nút Đặt tên nhóm… mở danh sách nhóm khi chọn một ngành và một loại ngày.
"""
