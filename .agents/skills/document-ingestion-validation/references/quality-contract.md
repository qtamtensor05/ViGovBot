# Hợp đồng chất lượng ingestion

Đối chiếu từng stage bằng cùng `document_id` và thứ tự nguồn. Báo số tuyệt đối,
denominator và mẫu lỗi cho: text rỗng, metadata thiếu, thứ tự trang/section,
duplicate exact, độ dài chunk và content retention. Ngưỡng cảnh báo là tham số
của lần audit, không phải chuẩn chất lượng mặc định. OCR accuracy cần ground truth.

JSONL tối thiểu cho script: mỗi dòng là object, nên có `document_id`, `text` và
có thể có `page`, `section`, `chunk_id`, `metadata`.
