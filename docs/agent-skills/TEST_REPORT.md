# Báo cáo kiểm thử Agent Skills

Ngày kiểm thử: 2026-10-15. Scenario là trigger/negative contract từng skill.

| Skill | Positive | Negative boundary | Trạng thái |
|---|---|---|---|
| rag-architecture-review | review toàn luồng | typo | PASS |
| document-ingestion-validation | audit JSONL | chấm answer | PASS |
| retrieval-debugging | top-k thiếu evidence | generation-only | PASS |
| rag-evaluation | metric có label | composite tùy ý | PASS |
| dataset-validation | split leakage | tự xóa data | PASS |
| chatbot-api-testing | local session | prod load test | PASS |
| rag-security-review | synthetic injection | exfiltration | PASS |
| context-management | task nhiều module | known one-file edit | PASS |
| token-budget-optimization | context lớn | bỏ test | PASS |
| minimal-diff-development | scoped fix | broad refactor | PASS |
| task-planning | migration nhiều phase | typo | PASS |
| code-change-verification | test selection | compile = E2E | PASS |
| context-handoff | chuyển phiên | chứa secret | PASS |
| repository-navigation | tìm callers | scan artifacts | PASS |
| usage-benchmark | matched telemetry | token giả | PASS |

Automated checks xác nhận manifest/UI config, discovery một cấp và ba script với
fixture hợp lệ/lỗi. `quick_validate.py` chạy từng skill. Implicit discovery trong
phiên Codex mới là **NOT VERIFIED** vì phiên hiện tại đã nạp catalog trước khi tạo.

Kết quả thực tế: 15/15 `quick_validate.py` PASS; 5 test skill/documentation PASS;
full suite 164 PASS, 1 SKIPPED optional; Ruff, compileall và `git diff --check`
PASS. Không chạy model, web server, GPU workload hay benchmark usage thật.
