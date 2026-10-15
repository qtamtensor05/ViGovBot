---
name: rag-architecture-review
description: Review RAG architecture boundaries and coupling in ViGovBot. Use for architecture audits or proposed structural changes; do not trigger for a narrow bug fix.
---

# RAG Architecture Review

Đánh giá kiến trúc, không tự ý refactor.

## Hợp đồng

- Input: Sơ đồ luồng hoặc entry point; phạm vi review; ràng buộc tương thích.
- Output: Bản phát hiện có bằng chứng theo ingestion, retrieval, generation, API, evaluation; mức độ ảnh hưởng; đề xuất nhỏ nhất.

## Quy trình

+1. Đọc entry point và cấu hình liên quan trước, rồi lần theo dependency bằng `rg`.\n2. Vẽ ranh giới module và luồng dữ liệu; kiểm tra SOLID, coupling, vòng phụ thuộc và business logic bị nhân đôi.\n3. Tách phát hiện đã xác nhận khỏi giả thuyết; ưu tiên thay đổi tương thích và không sửa nếu người dùng chỉ yêu cầu review.

## Ví dụ

Yêu cầu phù hợp: "review the current RAG architecture." Thực hiện quy trình trên và báo rõ bằng chứng.

## Giới hạn và kiểm chứng

Không dùng để review style hoặc tự tái cấu trúc toàn hệ thống. Không suy luận runtime từ source-only. Kiểm chứng bằng scenario tương ứng trong
`docs/agent-skills/TEST_REPORT.md`; nếu có script, chạy cả fixture hợp lệ và input lỗi.
