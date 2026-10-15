# Báo cáo kiểm thử Agent Skills

Ngày kiểm thử: 2026-10-15 (Windows/PowerShell, Codex CLI 0.160.0).

## Routing scenarios

| Skill | Prompt phù hợp | Boundary không kích hoạt | Kết quả source contract |
|---|---|---|---|
| `rag-architecture-review` | review boundary toàn RAG | bug hẹp | PASS |
| `document-ingestion-validation` | audit extraction/chunks | chấm answer | PASS |
| `retrieval-debugging` | top-k thiếu/sai | generation-only | PASS |
| `rag-evaluation` | tính/diễn giải metric | composite tùy ý | PASS |
| `dataset-validation` | schema/split/leakage | tự sửa data | PASS |
| `chatbot-api-testing` | local API/session | production load test | PASS |
| `rag-security-review` | synthetic injection/access | exfiltration thật | PASS |
| `context-navigation` | chưa rõ implementation/nhiều module | known one-file edit | PASS |
| `task-planning` | migration nhiều phase | typo | PASS |
| `minimal-diff-development` | scoped fix/feature | broad refactor | PASS |
| `code-change-verification` | chọn gate cho diff | compile = E2E | PASS |
| `context-handoff` | chuyển phiên | chứa secret | PASS |
| `usage-benchmark` | paired telemetry thật | synthetic savings | PASS |

`tests.test_agent_skills` kiểm tra boundary trong description, manifest/name,
layout discovery một cấp, UI prompt, absence của ba skill retired, metric contract,
và fixture valid/invalid cho ba script. Đây là deterministic source-level routing
test; không phải quan sát model tự chọn skill trong một phiên mới.

## Lệnh và kết quả

| Lệnh/gate | Kết quả |
|---|---|
| `python -m unittest tests.test_agent_skills -v` | PASS, 6/6 |
| `quick_validate.py` cho 13 skill migration với `PYTHONUTF8=1` | PASS, 13/13 |
| `quick_validate.py` cho toàn bộ skill repo-local | PASS, 16/16 |
| Ba script `--help` trên PowerShell/Windows | PASS |
| `python -m unittest discover -s tests -v` | PASS, 166; SKIPPED 1 optional dataset |
| `python -m ruff check .agents/skills tests/test_agent_skills.py` | PASS |
| `python -m compileall -q .agents/skills tests/test_agent_skills.py` | PASS |
| `git diff --check` | PASS sau khi sửa blank line cuối file |

Lần validator đầu không bật UTF-8 đã FAIL với `UnicodeDecodeError` trên ba skill
tiếng Việt ngoài bộ migration; chạy lại bằng `PYTHONUTF8=1` PASS. Lỗi và cách
tránh được ghi tại `ERR-20261015-22`.

## NOT VERIFIED / NOT RUN

- Implicit discovery và correct/incorrect routing của `context-navigation` trong
  một phiên Codex mới hoàn toàn: **NOT VERIFIED**.
- Paired baseline-vs-skills với provider token telemetry: **NOT RUN**; không có
  số liệu tiết kiệm thật để tuyên bố.
- Production API, model inference, GPU, web UI và external services: **NOT RUN**
  vì migration không thay đổi các bề mặt đó.
