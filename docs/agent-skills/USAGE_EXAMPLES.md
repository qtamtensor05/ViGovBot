# Ví dụ sử dụng

- `$rag-architecture-review review boundaries từ ingest đến API, chỉ báo cáo.`
- `$document-ingestion-validation kiểm tra chunks.jsonl và báo denominator.`
- `$retrieval-debugging phân tích top-5, tách retrieval/generation.`
- `$rag-evaluation thiết kế Recall@5, MRR và generation metrics.`
- `$dataset-validation kiểm tra split leakage.`
- `$chatbot-api-testing kiểm tra local API và session isolation.`
- `$rag-security-review thiết kế synthetic injection tests.`
- `$context-management lập context map cho lỗi loader.`
- `$token-budget-optimization tối ưu context, không bỏ verification.`
- `$minimal-diff-development sửa lỗi và giữ API contract.`
- `$task-planning chia migration thành phase có gate.`
- `$code-change-verification chọn test cho diff hiện tại.`
- `$context-handoff tạo handoff không chứa secret.`
- `$repository-navigation tìm entry point và callers.`
- `$usage-benchmark thiết kế A/B, chưa chạy khi thiếu telemetry.`

Không dùng skill chuyên biệt cho câu hỏi một bước. Implicit invocation dựa trên
`description`; có thể gọi rõ bằng `$skill-name`.
