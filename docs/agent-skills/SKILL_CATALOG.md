# Catalog Agent Skills

Chọn một skill chính theo outcome; chỉ thêm skill hỗ trợ khi trách nhiệm khác
biệt rõ. Codex chỉ cần đọc `SKILL.md` của skill đã chọn và reference được route
từ đó, không nạp toàn bộ catalog.

## RAG và chatbot

| Skill | Dùng khi | Không dùng khi |
|---|---|---|
| `rag-architecture-review` | Audit boundary/coupling hoặc đề xuất thay đổi kiến trúc RAG | Sửa bug hẹp đã biết vị trí |
| `document-ingestion-validation` | Audit extraction, metadata, section, chunk hoặc Bronze/Silver/Gold | Chấm câu trả lời RAG |
| `retrieval-debugging` | Chunk thiếu, sai hoặc xếp hạng không đúng | Context đúng nhưng generation sai |
| `rag-evaluation` | Thiết kế, chạy hoặc diễn giải benchmark RAG | Gộp metric thành điểm tùy ý |
| `dataset-validation` | Kiểm tra schema, split, duplicate, leakage trước train/eval | Tự sửa hoặc rebalance dữ liệu |
| `chatbot-api-testing` | Kiểm tra contract, stream, session, isolation, timeout/error | Load test hoặc production chưa được phép |
| `rag-security-review` | Threat model injection, authorization, exposure, session isolation | Pentest production ngoài phạm vi |

## Workflow repository/Codex

| Skill | Dùng khi | Không dùng khi |
|---|---|---|
| `context-navigation` | Chưa rõ entry point, task nhiều module hoặc cần kiểm soát context | Edit một file đã xác định |
| `task-planning` | Task nhiều phase, rủi ro hoặc lệnh dài | Typo/thay đổi đơn giản |
| `minimal-diff-development` | Implement fix/feature có phạm vi rõ | Refactor rộng được yêu cầu rõ |
| `code-change-verification` | Chọn và chạy gate cho diff/readiness | Dùng compile làm bằng chứng E2E |
| `context-handoff` | Tạm dừng, chuyển phiên hoặc cần handoff | Thay nhật ký dự án bắt buộc |
| `usage-benchmark` | Có thể thu run A/B thật và telemetry so sánh được | Dùng text length hoặc dữ liệu giả |

Ba skill cũ `context-management`, `repository-navigation` và
`token-budget-optimization` đã hợp nhất vào `context-navigation`; xem
[migration report](MIGRATION_REPORT.md).
