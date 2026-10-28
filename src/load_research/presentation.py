"""Vietnamese presentation labels; stored keys and identifiers stay unchanged."""

import math
import re

FIELDS = {
    "run_id": "Mã lần nghiên cứu",
    "source_name": "Tệp nguồn",
    "source_id": "SHA-256 nguồn",
    "source_row": "Dòng nguồn",
    "source_slot": "Chu kỳ nguồn",
    "original_timestamp": "Thời điểm nguồn",
    "aligned_timestamp": "Thời điểm sau hiệu chỉnh",
    "offset_seconds": "Độ lệch về sau so với mốc (giây)",
    "vee_completion": "Chế độ hoàn chỉnh dữ liệu VEE",
    "original_interval_start": "Đầu chu kỳ nguồn",
    "original_interval_end": "Cuối chu kỳ nguồn",
    "message": "Thông báo và hướng xử lý",
    "policy": "Chính sách xử lý",
    "organization_scope": "Phạm vi đơn vị",
    "organization_code": "Mã đơn vị",
    "scope": "Phạm vi đơn vị",
    "industry_code": "Mã ngành nghề",
    "industry_name": "Tên ngành nghề",
    "year_month": "Năm-tháng",
    "period": "Năm-tháng",
    "periods": "Các tháng nghiên cứu",
    "day_type": "Loại ngày",
    "day_types": "Các loại ngày",
    "date": "Ngày",
    "customer_id": "Mã khách hàng",
    "meter_id": "Mã công tơ",
    "measurement_point_id": "Mã điểm đo",
    "profile_scope": "Phạm vi phụ tải",
    "profile_kind": "Loại đường biểu diễn",
    "cluster_id": "Mã nhóm hành vi",
    "cluster_name": "Tên nhóm hành vi",
    "interval_minutes": "Độ dài chu kỳ (phút)",
    "unit": "Đơn vị",
    "result_status": "Trạng thái kết quả",
    "status": "Trạng thái",
    "reason": "Nguyên nhân",
    "slot_index": "Chu kỳ",
    "start_time": "Bắt đầu chu kỳ",
    "end_time": "Kết thúc chu kỳ",
    "value": "Giá trị",
    "weight": "Trọng số mẫu",
    "sampling_weight": "Trọng số mẫu",
    "days_used": "Số ngày đủ điều kiện",
    "estimated_fraction": "Tỷ lệ chu kỳ ước lượng",
    "unknown_fraction": "Tỷ lệ chu kỳ chưa rõ chất lượng",
    "sample_energy_share": "Tỷ trọng điện năng mẫu",
    "coverage": "Độ phủ dữ liệu nguồn",
    "original_coverage": "Độ phủ dữ liệu nguồn",
    "original_month_coverage": "Độ phủ nguồn toàn tháng",
    "load_factor": "Hệ số phụ tải",
    "customers": "Số khách hàng",
    "customer_count": "Số khách hàng",
    "cohort_size": "Số khách hàng trong tập mẫu chung",
    "sample_daily_kwh": "Điện năng ngày tập mẫu (kWh)",
    "peak_slot": "Chu kỳ phụ tải cực đại",
    "billing_kwh": "Điện năng thương phẩm (kWh)",
    "billing_energy": "Điện năng thương phẩm",
    "billing_basis": "Cơ sở kỳ thương phẩm",
    "basis": "Cơ sở kỳ đối soát",
    "background_kwh": "Điện năng nền mẫu theo lịch tháng S (kWh)",
    "alpha": "Hệ số suy rộng α",
    "beta": "Hệ số suy rộng chuỗi ngày β",
    "balance_error_kwh": "Sai lệch cân bằng điện năng (kWh)",
    "component_error_kwh": "Sai lệch tổng đóng góp (kWh)",
    "expected_intervals": "Số chu kỳ dự kiến",
    "original_valid": "Số chu kỳ nguồn hợp lệ",
    "estimated_intervals": "Số chu kỳ ước lượng",
    "unknown_source_quality": "Số chu kỳ chưa rõ chất lượng nguồn",
    "valid_days": "Số ngày đủ điều kiện",
    "adjustments": "Số giá trị được bù",
    "mad_outliers": "Số cảnh báo ngoại lai MAD",
    "zero_days": "Số ngày không tiêu thụ điện",
    "flat_days": "Số ngày phụ tải không đổi",
    "cmis_kwh": "Điện năng CMIS mẫu (kWh)",
    "mdms_original_kwh": "Điện năng nguồn MDMS (kWh)",
    "difference_kwh": "Chênh lệch điện năng (kWh)",
    "original_kwh": "Điện năng nguồn (kWh)",
    "repaired_kwh": "Điện năng sau xử lý (kWh)",
    "estimated": "Giá trị ước lượng",
    "repair_blocked": "Không cho phép bù",
    "quality_known": "Đã biết chất lượng nguồn",
    "component_code": "Mã thành phần phụ tải",
    "component_name": "Tên thành phần phụ tải",
    "method": "Phương pháp",
    "donor_dates": "Ngày nguồn dùng bù",
    "eligible": "Đủ điều kiện",
    "min_customers": "Cỡ mẫu tối thiểu",
    "min_days": "Số ngày tối thiểu theo loại ngày",
    "min_original_coverage": "Độ phủ nguồn tối thiểu",
    "max_estimated_fraction": "Tỷ lệ ước lượng tối đa",
    "max_linear_minutes": "Độ dài thiếu tối đa để nội suy (phút)",
    "max_like_minutes": "Độ dài thiếu tối đa để bù tương đồng (phút)",
    "min_donors": "Số ngày nguồn bù tối thiểu",
    "donor_scale_min": "Hệ số hiệu chỉnh ngày nguồn nhỏ nhất",
    "donor_scale_max": "Hệ số hiệu chỉnh ngày nguồn lớn nhất",
    "donor_common_fraction": "Tỷ lệ chu kỳ chung tối thiểu",
    "mad_factor": "Hệ số cảnh báo MAD",
    "mad_min_days": "Số ngày tối thiểu để đánh giá MAD",
    "clustering": "Thuật toán phân cụm",
    "manual_k": "Số nhóm cố định",
    "k_min": "Số nhóm nhỏ nhất",
    "k_max": "Số nhóm lớn nhất",
    "min_cluster_fraction": "Tỷ lệ khách hàng tối thiểu mỗi nhóm",
    "eps": "Bán kính lân cận DBSCAN",
    "min_samples": "Số mẫu lân cận tối thiểu DBSCAN",
    "seed": "Hạt giống ngẫu nhiên",
    "random_seed": "Hạt giống ngẫu nhiên",
    "timezone": "Múi giờ",
    "memory_limit_mb": "Giới hạn bộ nhớ (MB)",
    "worker_threads": "Số luồng xử lý",
    "calendar": "Lịch nghiên cứu",
    "request": "Khai báo nguồn dữ liệu",
    "software": "Phiên bản phần mềm",
    "min_cluster_customers": "Cỡ mẫu tối thiểu để phân cụm",
    "algorithm": "Thuật toán phân cụm",
    "n_init": "Số lần khởi tạo K-Means",
    "max_iter": "Số vòng lặp tối đa",
    "silhouette_sample": "Số mẫu đánh giá độ tách biệt cụm",
    "silhouette_min": "Độ tách biệt cụm tối thiểu",
    "silhouette_tie": "Ngưỡng hòa độ tách biệt cụm",
    "min_cluster_size": "Số khách hàng tối thiểu mỗi cụm",
    "max_dbscan_vectors": "Số hình dạng tối đa cho DBSCAN",
    "factor": "Hệ số suy rộng theo ngày",
    "monthly_energy_kwh": "Điện năng chuỗi suy rộng cả tháng (kWh)",
    "sample_billing_kwh": "Điện năng CMIS mẫu (kWh)",
    "sample_billing_basis": "Cơ sở kỳ CMIS mẫu",
}
DAY_TYPES = {
    "weekday": "Ngày làm việc",
    "saturday": "Thứ Bảy",
    "sunday": "Chủ nhật",
    "holiday": "Ngày lễ",
}
STATUSES = {
    "valid": "Hợp lệ",
    "valid_with_warnings": "Hợp lệ, có cảnh báo",
    "completed": "Hoàn thành",
    "completed_with_warnings": "Hoàn thành, có cảnh báo",
    "partial": "Kết quả chưa đầy đủ",
    "preview_insufficient_samples": "Xem tham khảo: chưa đủ cỡ mẫu",
    "no_eligible_samples": "Không có mẫu đủ điều kiện",
    "missing_billing": "Thiếu điện năng thương phẩm",
    "no_positive_shape": "Không có hình dạng phụ tải dương để suy rộng",
    "needs_review": "Cần kiểm tra lại",
    "failed": "Không hoàn thành",
    "cancelled": "Đã hủy",
    "running": "Đang xử lý",
    "draft": "Chưa chạy",
    "comparable": "Đủ điều kiện đối soát",
    "available": "Có dữ liệu",
    "N/A": "Không áp dụng / chưa đủ dữ liệu",
    "insufficient_samples": "Chưa đủ cỡ mẫu",
    "zero_billing_with_positive_sample": "Thương phẩm bằng 0 trong khi mẫu có tiêu thụ",
}
REASONS = {
    "missing_profile": "Chưa có đường phụ tải hợp lệ",
    "missing_daily_profile": "Chưa có đường suy rộng ngày hợp lệ",
    "unknown_industry_universe": "Chưa xác minh đủ danh mục ngành toàn đơn vị",
    "incomplete_cohort_days": "Chuỗi ngày của tập mẫu chung chưa đủ điều kiện",
    "zero_sample_with_positive_billing": "Mẫu bằng 0 nhưng thương phẩm dương",
    "missing_billing": "Thiếu điện năng thương phẩm",
    "insufficient_original_coverage": "Độ phủ dữ liệu nguồn chưa đạt ngưỡng",
    "incomplete_vee": "Không thể bù đủ chu kỳ bằng dữ liệu có căn cứ hoặc có chu kỳ cấm bù",
    "partial_month_or_changed_industry_weight": "Không đủ hiệu lực trọn tháng hoặc đổi ngành/trọng số",
    "period_basis_unconfirmed_or_incomplete_mdms": "Chưa xác nhận cùng kỳ hoặc dữ liệu MDMS chưa đủ tháng",
    "insufficient_daily_cohort": "Chuỗi ngày của tập mẫu chung chưa đủ điều kiện",
}
BASES = {
    "calendar_month": "Tháng dương lịch",
    "billing_label_month": "Tháng ghi sổ thương phẩm",
}
SCOPES = {
    "customer": "Phụ tải từng khách hàng",
    "industry_scaled": "Phụ tải suy rộng",
    "sample_portfolio": "Phụ tải tập mẫu",
    "overall": "Đường phụ tải tổng hợp",
    "cluster_contribution": "Đóng góp nhóm hành vi",
    "normalized_shape": "Đường phụ tải chuẩn hóa",
    "dimensionless": "Không thứ nguyên",
}
METHODS = {
    "customer": "Dữ liệu từng khách hàng trước/sau VEE",
    "source": "Dữ liệu nguồn",
    "linear": "Nội suy tuyến tính",
    "like_day": "Bù bằng ngày tương đồng",
    "same_type_unscaled": "Bù trung vị ngày cùng loại, không điều chỉnh mức",
    "same_type_scaled": "Bù trung vị ngày cùng loại, có hiệu chỉnh mức",
    "representative": "Suy rộng theo loại ngày",
    "daily_variation": "Suy rộng giữ biến thiên ngày",
    "variation": "Suy rộng giữ biến thiên ngày",
}
FRACTIONS = {
    "estimated_fraction",
    "unknown_fraction",
    "sample_energy_share",
    "load_factor",
    "coverage",
    "original_coverage",
    "original_month_coverage",
}


def field_label(key: str) -> str:
    match = re.fullmatch(r"slot_(\d+)", key)
    return f"Chu kỳ {int(match[1]):02}" if match else FIELDS.get(key, key)


def translated_value(key: str, value: object) -> object:
    if isinstance(value, bool):
        return "Có" if value else "Không"
    if key == "day_types" and isinstance(value, (tuple, list)):
        return ", ".join(str(DAY_TYPES.get(kind, kind)) for kind in value)
    if not isinstance(value, str):
        return value
    mapping = (
        DAY_TYPES
        if key == "day_type"
        else STATUSES
        if key in ("status", "result_status")
        else BASES
        if key in ("billing_basis", "basis", "sample_billing_basis")
        else SCOPES
        if key in ("profile_scope", "profile_kind")
        else METHODS
        if key == "method"
        else REASONS
        if key == "reason"
        else {}
    )
    if key == "reason" and value.startswith("insufficient_day_types:"):
        kinds = value.partition(":")[2].split(",")
        return "Chưa đủ ngày theo loại: " + ", ".join(
            DAY_TYPES.get(k, k) for k in kinds
        )
    return mapping.get(value, value)


def format_value(key: str, value: object) -> str:
    value = translated_value(key, value)
    if value is None or isinstance(value, float) and not math.isfinite(value):
        return "—"
    if isinstance(value, float):
        if key in FRACTIONS:
            text = f"{value * 100:.6g}%"
        elif value and abs(value) < 1e-6:
            text = f"{value:.6g}"
        else:
            text = f"{value:,.6f}".rstrip("0").rstrip(".")
        return text.replace(",", "\0").replace(".", ",").replace("\0", ".")
    return str(value)


def event_text(event: dict) -> str:
    stages = {
        "started": "Bắt đầu nghiên cứu",
        "import": "Đang nhập dữ liệu đo đếm",
        "cache": "Đã xác minh dữ liệu chuẩn",
        "analysis": "Đang phân tích",
        "finished": "Đã hoàn tất nghiên cứu",
        "exported": "Đã xuất báo cáo",
        "cancelled": "Đã hủy tác vụ",
        "error": "Tác vụ cần kiểm tra lại",
        "sources_verified": "Đã xác minh tệp nguồn",
        "backed_up": "Đã sao lưu",
        "inspected": "Đã truy vết dữ liệu ngày",
        "daily_loaded": "Đã nạp phụ tải từng ngày",
    }
    parts = [stages.get(event.get("stage", ""), "Đang xử lý")]
    if event.get("period"):
        parts.append(event["period"])
    if "total" in event:
        parts.append(f"{event.get('completed', 0)}/{event['total']}")
    if event.get("status"):
        parts.append(format_value("status", event["status"]))
    return " · ".join(parts)
