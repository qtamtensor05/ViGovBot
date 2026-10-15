# Báo cáo migration hai bộ Agent Skills

Ngày thực hiện: 2026-10-15 (Asia/Saigon). Baseline: Codex CLI `0.160.0`, nhánh
`main`; file prompt của người dùng được giữ nguyên và không đưa vào migration.

## Kết quả kiểm kê và ánh xạ

| Đường dẫn gốc | Trigger/chức năng chính | Resource/phụ thuộc | Chồng lấn | Quyết định và đích |
|---|---|---|---|---|
| `rag-architecture-review` | Audit kiến trúc RAG | instruction | thấp | giữ, rút gọn tại chỗ |
| `document-ingestion-validation` | Audit extraction/chunk | script stdlib + quality contract | thấp | giữ script/reference, nâng cấp entrypoint |
| `retrieval-debugging` | Chẩn đoán top-k/rerank | instruction | thấp | giữ, làm rõ retrieval vs generation |
| `rag-evaluation` | Metric/benchmark RAG | metric contract; dependency metric tùy chọn | thấp | giữ, bổ sung retrieval, generation, groundedness, resource |
| `dataset-validation` | Schema/split/leakage | script stdlib | thấp | giữ script, bổ sung cohort hội thoại |
| `chatbot-api-testing` | Contract/stream/session | local test client nếu có | thấp | giữ, bổ sung multi-turn/no-answer/isolation |
| `rag-security-review` | Injection/access/isolation | synthetic fixtures | thấp | giữ, làm rõ trust boundary và authorization |
| `context-management` | Progressive context | instruction | cao với navigation/token | hợp nhất vào `context-navigation` |
| `repository-navigation` | Tìm entry point/callers | `rg` | cao với context | hợp nhất vào `context-navigation` |
| `token-budget-optimization` | Kiểm soát context/token | provider telemetry nếu đo | cao với context | hợp nhất vào `context-navigation` |
| `minimal-diff-development` | Scoped implementation | Git/diff/tests | thấp | giữ và rút gọn |
| `task-planning` | Task nhiều phase | acceptance evidence | thấp | giữ, kích hoạt có điều kiện |
| `code-change-verification` | Test/readiness gate | test tools dự án | thấp | giữ, chuẩn hóa trạng thái kiểm chứng |
| `context-handoff` | Chuyển phiên | Git/test/artifact evidence | thấp | giữ và rút gọn |
| `usage-benchmark` | Paired A/B thật | script stdlib + provider telemetry | thấp | giữ; không chạy benchmark giả/tốn phí |

Đường dẫn migration đều ở `.agents/skills/<name>`. Không archive ba skill cũ vì
Git lưu lịch sử và mọi caller trong repository đã chuyển sang skill hợp nhất;
giữ bản sao song song sẽ tiếp tục gây routing chồng lấn.

## Thành phần bảo toàn

- `validate_dataset.py`, `validate_ingestion.py`, `summarize_benchmark.py` và
  hành vi fixture hiện có;
- `quality-contract.md`, metric contract và mọi `agents/openai.yaml` có ích;
- chính sách bảo mật, project structure/task journal/long-running workflow;
- toàn bộ source ứng dụng, test RAG, dataset, model, checkpoint và `outputs/`.

## Thay đổi hành vi skill

- Entry point ngắn hơn, bỏ template `Hợp đồng/Ví dụ` và chuỗi `\n` literal.
- Reference chỉ đọc khi workflow cần; metric thiếu input/dependency trả
  `null`/`unavailable`, không biến thành 0.
- Trigger phân biệt rõ hơn; không áp token cap làm giảm correctness.
- Không thêm `policy.allow_implicit_invocation: false`; giữ implicit invocation.

Chi tiết nguồn và giới hạn xác minh ở [SOURCE_VERIFICATION.md](SOURCE_VERIFICATION.md),
kết quả lệnh ở [TEST_REPORT.md](TEST_REPORT.md).
