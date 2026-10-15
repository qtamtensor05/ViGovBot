---
name: document-ingestion-validation
description: Validate document and PDF ingestion quality across extraction, cleaning, metadata, sections and chunks. Use for pipeline quality audits or Bronze/Silver/Gold comparisons.
---

# Document Ingestion Validation

Kiểm tra chất lượng dữ liệu theo từng tầng.

## Hợp đồng

- Input: Artifact từng bước hoặc mẫu record cùng schema/config tạo ra chúng.
- Output: Báo cáo số lượng, mất nội dung, thứ tự, duplicate, metadata và mẫu lỗi theo từng stage.

## Quy trình

+1. Xác nhận lineage và tổng số record từng stage.\n2. Kiểm tra text rỗng, thứ tự trang/section, metadata bắt buộc, duplicate và tỷ lệ giữ nội dung.\n3. Dùng `scripts/validate_ingestion.py` khi có JSONL; đọc `references/quality-contract.md` để diễn giải ngưỡng.\n4. Báo cáo denominator và ví dụ, không biến heuristic thành sự thật.

## Ví dụ

Yêu cầu phù hợp: "validate a document ingestion run." Thực hiện quy trình trên và báo rõ bằng chứng.

## Giới hạn và kiểm chứng

Không đánh giá câu trả lời RAG hoặc sửa tài liệu nguồn. OCR quality chưa được chứng minh nếu không có ground truth. Kiểm chứng bằng scenario tương ứng trong
`docs/agent-skills/TEST_REPORT.md`; nếu có script, chạy cả fixture hợp lệ và input lỗi.
