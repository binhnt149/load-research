"""Actionable Vietnamese diagnostics at UI/report boundaries."""

import re

from load_research.presentation import field_label

MESSAGES = {
    "inconsistent research calendar": "Các ngành có số ngày theo lịch khác nhau. Hãy dùng cùng một lịch nghiên cứu trước khi tổng hợp.",
    "date does not match selected day type": "Ngày đã chọn không thuộc loại ngày đang lọc. Hãy chọn lại ngày lịch phù hợp.",
    "date is outside the saved research periods": "Ngày nằm ngoài các tháng nghiên cứu đã lưu. Hãy chọn ngày trong phạm vi kết quả.",
    "excel row limit would be exceeded; select csv-only export or a smaller scope": "Số dòng vượt giới hạn Excel. Bỏ chọn Excel để xuất CSV, hoặc thu hẹp phạm vi báo cáo.",
    "ambiguous or empty table header": "Tiêu đề có tên cột trùng hoặc trống. Mỗi cột phải có một tên riêng.",
    "table has no header": "Tệp chưa có hàng tiêu đề. Hãy bổ sung tên các cột theo mẫu.",
    "mapping references a missing source column": "Ánh xạ đang tham chiếu cột không có trong nguồn. Chọn lại đúng tên cột.",
    "mapping uses reserved provenance fields": "Tên cột ánh xạ trùng trường truy vết dành riêng của ứng dụng. Hãy đổi ánh xạ.",
    "invalid input file or table options": "Tệp không tồn tại hoặc thiết lập đọc bảng không hợp lệ. Kiểm tra đường dẫn và dấu phân cách.",
    "unsupported input format; expected csv, xlsx or parquet": "Định dạng tệp chưa được hỗ trợ. Hãy dùng CSV UTF-8, XLSX hoặc Parquet.",
    "excel formula has no cached value; export values before import": "Công thức Excel chưa có giá trị tính sẵn. Tính lại và lưu bằng Excel, hoặc xuất tệp chỉ chứa giá trị.",
    "excel archive exceeds safe expansion limit; use csv/parquet": "Tệp Excel vượt giới hạn giải nén an toàn. Hãy chia nhỏ hoặc dùng CSV/Parquet.",
    "excel archive has an unsafe compression ratio": "Tệp Excel có tỷ lệ nén vượt giới hạn an toàn. Hãy xuất lại từ nguồn tin cậy.",
    "customer scope does not match study scope": "Mã đơn vị trong CMIS không khớp phạm vi nghiên cứu. Kiểm tra mã đơn vị và cấu hình.",
    "billing scope does not match study scope": "Phạm vi bảng thương phẩm không khớp đơn vị nghiên cứu. Kiểm tra trường phạm vi đơn vị.",
    "sampling weight must be positive": "Trọng số mẫu phải lớn hơn 0. Kiểm tra sampling_weight.",
    "number must be finite and non-negative": "Giá trị số phải hữu hạn và không âm. Không dùng NaN, vô cực hoặc số âm.",
    "conflicting industry names": "Cùng mã ngành đang có các tên ngành khác nhau. Hãy thống nhất danh mục ngành nghề.",
    "meter mapping requires meter_id or measurement_point_id": "Thiếu mã công tơ hoặc mã điểm đo. Cần meter_id hoặc measurement_point_id để ghép khách hàng.",
    "mapping validity must be an ordered local [from,to) interval": "Khoảng hiệu lực ghép công tơ không hợp lệ. Ngày bắt đầu phải trước ngày kết thúc, theo giờ địa phương.",
    "ambiguous meter mapping": "Một công tơ đang ghép với nhiều khách hàng trong cùng thời gian. Kiểm tra quan hệ công tơ và khoảng hiệu lực.",
    "missing or ambiguous meter mapping": "Không xác định được duy nhất khách hàng của công tơ. Kiểm tra mã công tơ và thời gian hiệu lực trong CMIS.",
    "sample catalog is empty": "Danh mục mẫu CMIS không có khách hàng hợp lệ. Kiểm tra tệp và ánh xạ cột.",
    "invalid sample billing basis": "Cơ sở kỳ điện năng CMIS mẫu chưa hợp lệ. Khai báo tháng dương lịch hoặc tháng ghi sổ.",
    "conflicting sample billing": "Điện năng CMIS mẫu bị mâu thuẫn cho cùng khách hàng-tháng. Kiểm tra dòng trùng.",
    "billing basis must be explicitly declared": "Chưa khai báo cơ sở kỳ thương phẩm. Chọn calendar_month (tháng dương lịch) hoặc billing_label_month (tháng ghi sổ).",
    "billing energy unit must be declared": "Chưa khai báo đúng đơn vị điện năng thương phẩm. Dùng Wh, kWh hoặc MWh.",
    "billing energy overflow": "Điện năng thương phẩm vượt giới hạn tính toán. Kiểm tra giá trị và đơn vị.",
    "duplicate industry-month billing total": "Có nhiều tổng điện năng thương phẩm cho cùng ngành-tháng. Hãy giữ một tổng đúng phạm vi.",
    "missing interval timestamp": "Thiếu thời điểm chu kỳ đo. Kiểm tra timestamp và quy ước đầu/cuối chu kỳ.",
    "wide row date must be a local calendar date": "Ngày trong MDMS dạng rộng phải là ngày địa phương YYYY-MM-DD, không kèm giờ hoặc múi giờ.",
    "mdms scope differs from study scope": "Phạm vi đơn vị MDMS không khớp nghiên cứu. Kiểm tra dữ liệu và mã đơn vị.",
    "mdms channel differs from declared import channel": "Kênh MDMS không khớp kênh điện năng tác dụng nhận đã khai báo. Kiểm tra channel.",
    "mdms unit differs from declared source unit": "Đơn vị trong MDMS không khớp đơn vị nguồn đã khai báo. Kiểm tra kW/kWh và loại đại lượng.",
    "mdms direction is not active import": "Chiều đo MDMS không phải điện năng tác dụng nhận từ lưới. Kiểm tra kênh và chiều đo.",
    "missing meter mapping key": "Thiếu khóa ghép công tơ. Bổ sung meter_id hoặc measurement_point_id.",
    "repair_blocked must be an explicit boolean": "Cờ không cho phép bù phải được khai báo rõ đúng/sai. Kiểm tra repair_blocked.",
    "customer id contradicts meter mapping": "Mã khách hàng MDMS mâu thuẫn quan hệ công tơ trong CMIS. Kiểm tra mã và hiệu lực ghép.",
    "timestamp must be aligned to interval boundaries": "Thời điểm đo không nằm trên biên chu kỳ đã khai báo. Kiểm tra bước 15/30/60 phút và quy ước thời gian.",
    "measurement kind and unit are incompatible": "Loại đại lượng không phù hợp đơn vị. Điện năng chu kỳ dùng Wh/kWh/MWh; công suất trung bình dùng W/kW/MW.",
    "measurement must be finite and non-negative": "Giá trị đo phải hữu hạn và không âm. Kiểm tra số liệu và dấu thập phân.",
    "measurement overflow": "Giá trị đo sau quy đổi vượt giới hạn. Kiểm tra đơn vị và hệ số nhân công tơ.",
    "values_already_scaled must be explicitly declared": "Cần xác nhận nguồn đã nhân hệ số công tơ hay chưa. Không để trống lựa chọn này.",
    "only declared active import channel is supported": "Chỉ hỗ trợ kênh điện năng tác dụng nhận đã khai báo. Kiểm tra channel và direction.",
    "invalid source convention/layout": "Quy ước thời điểm, loại đại lượng hoặc dạng MDMS chưa hợp lệ. Kiểm tra thiết lập nguồn.",
    "invalid delimiter/decimal convention": "Dấu phân cách cột hoặc dấu thập phân chưa hợp lệ. Kiểm tra thiết lập CSV.",
    "mapping must contain string column names": "Tên cột trong ánh xạ phải là chuỗi văn bản. Chọn đúng tiêu đề của tệp nguồn.",
    "periods must be non-empty and unique": "Cần ít nhất một tháng nghiên cứu; các tháng không được trùng nhau.",
    "scope must be a non-empty string up to 128 characters": "Phạm vi đơn vị không được trống hoặc dài quá 128 ký tự.",
    "analysis interval must be 30 or 60 minutes": "Chu kỳ nghiên cứu phải là 30 phút (48 chu kỳ/ngày) hoặc 60 phút (24 chu kỳ/ngày).",
    "unknown clustering algorithm": "Thuật toán phân cụm chưa hợp lệ. Chọn K-Means hoặc DBSCAN.",
    "invalid cluster range": "Khoảng số nhóm chưa hợp lệ. Số nhóm nhỏ nhất từ 2 và số nhóm lớn nhất không quá 50.",
    "manual_k must be an integer from 1 to 50": "Số nhóm cố định phải là số nguyên từ 1 đến 50.",
    "four positive minimum day counts are required": "Cần bốn số ngày tối thiểu dương, tương ứng ngày làm việc, thứ Bảy, Chủ nhật và ngày lễ.",
    "invalid donor scaling bounds or common fraction": "Giới hạn hiệu chỉnh ngày tương đồng hoặc tỷ lệ chu kỳ chung chưa hợp lệ. Kiểm tra các ngưỡng bù.",
    "eps must be finite and positive": "Bán kính eps của DBSCAN phải hữu hạn và lớn hơn 0.",
    "dbscan requires an explicit eps": "DBSCAN cần khai báo rõ bán kính lân cận eps lớn hơn 0.",
    "invalid random seed": "Hạt giống ngẫu nhiên phải là số nguyên hợp lệ. Kiểm tra seed.",
    "cmis and mdms sources are required": "Cần chọn cả tệp CMIS mẫu và ít nhất một nguồn MDMS trước khi chạy.",
    "mdms resolution cannot produce the requested analysis resolution": "Độ phân giải MDMS không đủ để tạo chu kỳ nghiên cứu. Nguồn 60 phút chỉ tạo được 24 chu kỳ/ngày.",
    "source and analysis timezone must agree": "Múi giờ nguồn và nghiên cứu phải thống nhất. Kiểm tra cấu hình múi giờ.",
    "canonical cache is missing or changed": "Dữ liệu chuẩn đã lưu bị thiếu hoặc thay đổi checksum. Khôi phục bản sao đúng hoặc tạo lần nghiên cứu mới.",
    "import issue journal is missing or changed": "Nhật ký lỗi nhập bị thiếu hoặc thay đổi checksum. Cần khôi phục nhật ký trước khi dùng lại cache.",
    "artifact is missing or changed": "Kết quả lưu bị thiếu hoặc thay đổi checksum. Kiểm tra bản sao lưu của dự án.",
    "no completed result is loaded": "Chưa mở kết quả nghiên cứu đã hoàn thành. Chọn một lần trong lịch sử trước khi xuất.",
    "another task is running": "Một tác vụ khác đang chạy. Hãy đợi hoặc hủy trước khi tiếp tục.",
    "export destination already exists": "Thư mục báo cáo đã tồn tại. Chọn thư mục mới để giữ nguyên báo cáo cũ.",
    "comparison requires the same organization scope": "Hai lần nghiên cứu phải cùng phạm vi đơn vị để so sánh.",
    "requested resolution is unavailable": "Độ phân giải đã chọn không có trong kết quả. Chọn chu kỳ phù hợp dữ liệu nguồn.",
    "insufficient free space for source size, canonical data and temporary work": "Dung lượng trống chưa đủ để lưu dữ liệu chuẩn và tệp tạm. Giải phóng dung lượng rồi chạy lại.",
    "cannot increase temporal resolution": "Không thể tăng độ phân giải từ dữ liệu thưa hơn. Chọn chu kỳ bằng hoặc dài hơn nguồn.",
}


def _cause(message: str, context: dict, error_type: str) -> str:
    if message.startswith(
        ("Hãy ", "Không ", "Một ", "Chọn ", "Chưa ", "Cần ", "Tệp ", "Thư mục ")
    ):
        return message
    if match := re.fullmatch(r"missing or invalid (\w+)", message):
        key = match[1]
        return f"Thiếu hoặc không hợp lệ: {field_label(key)} ({key}). Kiểm tra giá trị và ánh xạ cột."
    if message == "requested Excel sheet does not exist":
        name = str(context.get("sheet") or "được yêu cầu")
        return (
            f"Trang tính “{name}” không tồn tại. Hãy chọn đúng trang tính chứa dữ liệu."
        )
    if match := re.fullmatch(
        r"column count differs from header at source row (\d+)", message
    ):
        context.setdefault("row", int(match[1]))
        return "Số cột dữ liệu khác số cột tiêu đề. Kiểm tra dấu phân cách, dấu ngoặc kép và các ô thừa/thiếu."
    if message.casefold() in MESSAGES:
        return MESSAGES[message.casefold()]
    if match := re.fullmatch(
        r"(\w+) must be (a positive integer|finite and positive|a finite fraction)",
        message,
    ):
        requirement = {
            "a positive integer": "số nguyên dương",
            "finite and positive": "số hữu hạn lớn hơn 0",
            "a finite fraction": "tỷ lệ hữu hạn từ 0 đến 1",
        }[match[2]]
        return f"{field_label(match[1])} ({match[1]}) phải là {requirement}. Kiểm tra tham số."
    if match := re.fullmatch(r"(\w+) must align with analysis resolution", message):
        return f"{field_label(match[1])} phải là bội số của độ dài chu kỳ nghiên cứu."
    if message.startswith("missing wide interval column "):
        return (
            "Thiếu cột chu kỳ MDMS dạng rộng: "
            + message.removeprefix("missing wide interval column ")
            + ". Kiểm tra độ phân giải và ánh xạ."
        )
    if message.startswith("could not convert string to float:"):
        return (
            "Giá trị số không hợp lệ: "
            + message.partition(":")[2].strip()
            + ". Kiểm tra dấu thập phân và bỏ ký tự không phải số."
        )
    if message.startswith("Invalid isoformat string:"):
        return (
            "Giá trị ngày/giờ không hợp lệ: "
            + message.partition(":")[2].strip()
            + ". Dùng ngày YYYY-MM-DD và thời điểm đúng định dạng đã khai báo."
        )
    if match := re.fullmatch(r"['\"](\w+)['\"]", message):
        return f"Thiếu trường {field_label(match[1])} ({match[1]}). Kiểm tra tiêu đề và ánh xạ cột."
    if "DayType" in message:
        return "Loại ngày không hợp lệ. Dùng weekday, saturday, sunday hoặc holiday theo hướng dẫn tệp lịch."
    if (
        error_type in ("UnicodeDecodeError", "UnicodeError")
        or "codec can't decode" in message
    ):
        return "Không đọc được mã hóa văn bản. Hãy lưu tệp CSV bằng UTF-8 rồi đọc lại."
    if error_type == "FileNotFoundError" or "[Errno 2]" in message:
        return "Không tìm thấy tệp hoặc thư mục. Kiểm tra đường dẫn và chọn lại nguồn."
    if error_type == "PermissionError" or "[Errno 13]" in message:
        return "Không có quyền đọc/ghi tệp. Kiểm tra quyền truy cập và đóng tệp đang bị khóa."
    if error_type == "BadZipFile":
        return "Tệp Excel bị hỏng hoặc không phải XLSX hợp lệ. Hãy xuất lại từ hệ thống nguồn."
    return "Không thể xử lý dữ liệu hoặc cấu hình này. Hãy kiểm tra định dạng tệp và các tham số đã khai báo."


def format_error(
    error: object, context: dict | None = None, *, error_type: str | None = None
) -> str:
    location = {**getattr(error, "source_context", {}), **(context or {})}
    message = str(error)
    if match := re.fullmatch(r"invalid source row (\d+): (.*)", message, re.DOTALL):
        location.setdefault("row", int(match[1]))
        message = match[2]
    cause = _cause(message, location, error_type or type(error).__name__)
    coordinates = []
    if location.get("path"):
        name = str(location["path"]).replace("\\", "/").rsplit("/", 1)[-1]
        coordinates.append(f"Tệp “{name}”")
    if location.get("sheet"):
        coordinates.append(f"trang tính “{location['sheet']}”")
    if location.get("row") is not None:
        coordinates.append(f"dòng {location['row']}")
    return (" · ".join(coordinates) + ": " if coordinates else "") + cause


def import_issue_rows(result: dict) -> list[dict]:
    sources = {source["sha256"]: source["path"] for source in result.get("sources", [])}
    return [
        {
            "source_name": str(sources.get(issue.get("source_id"), "Nguồn MDMS"))
            .replace("\\", "/")
            .rsplit("/", 1)[-1],
            "source_row": issue.get("source_row"),
            "source_slot": issue.get("source_slot"),
            "message": format_error(
                issue["reason"],
                {
                    "path": sources.get(issue.get("source_id")),
                    "row": issue.get("source_row"),
                    "sheet": issue.get("source_sheet"),
                },
            ),
            "policy": "Từ chối cả dòng",
        }
        for issue in result.get("import", {}).get("issues_preview", [])
    ]
