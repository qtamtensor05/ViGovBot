# Phát triển ViGovBot

> Đây là môi trường tùy chọn dành cho sửa code và chạy test, không phải runtime
> web hiện hành. Dùng [Docker Compose](docker.md) cho web, Base/RAG/QLoRA và
> Ollama; chỉ tạo lại `.venv` khi cần phát triển hoặc chạy test trên host.

## Thiết lập

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[test,dev]"
.venv\Scripts\vigov doctor
```

Linux dùng `.venv/bin/python` và `.venv/bin/vigov`. CLI tự tìm project root từ
package đã cài, nên có thể gọi ngoài thư mục repository. Có thể đặt rõ
`VIGOVBOT_PROJECT_ROOT` khi dùng bản cài không editable.

## Gate trước khi gửi thay đổi

```powershell
.venv\Scripts\python -m unittest discover -s tests -v
.venv\Scripts\python -m ruff check .
.venv\Scripts\python -m compileall -q src tests
.venv\Scripts\python -m pip check
git diff --check
```

Repository không còn workflow CI tự động. Trước khi bàn giao thay đổi, chạy thủ
công các gate ở trên; test GPU phải được ghi riêng như artifact thực nghiệm.

Implementation canonical nằm trong `src/vigovbot`; QLoRA chỉ dùng namespace
`vigovbot.training`. PowerShell lifecycle cũ chỉ là compatibility entry point và
không chứa business logic training.

## Đo coverage và ranh giới kiểm chứng (2026-10-18)

Suite dùng `unittest`; không cần pytest.ini/tox.ini/conftest.py để discovery.
Fixture dùng chung đặt trong `tests/tokenizer_fixtures.py`; tokenizer QLoRA
mô phỏng role/EOS giữ riêng, không thay bằng bộ đếm ký tự. Cấu hình branch
coverage nằm trong `[tool.coverage.*]` của pyproject.toml.

Trong môi trường đã cài các extra test/dev và dependency integration cần thiết:

```powershell
python -m pip install coverage
python scripts/verify_tests.py --output outputs/verification/coverage
```

Script chạy offline, ghi tests.log (verbose, gồm lý do skip), coverage.json và
coverage.txt, giữ exit code thất bại. Coverage chưa nằm trong lock dependency;
cần ghi phiên bản công cụ khi dùng báo cáo để so sánh. Không tự đặt threshold
cao hoặc bỏ module GPU để làm đẹp tỷ lệ. CI đã chủ động xóa trước đó, task này
không khôi phục workflow hay thêm CD.

Snapshot full-suite trong container Python 3.12: 194 test, 3 skip; line coverage
69,1% (3887/5624), branch 59,2% (1062/1794), tổng line+branch 66,7%.
Đây là coverage thực thi kể cả các luồng mock, không phải mức đảm bảo chất lượng.
Artifact đo ở `outputs/verification/task-20261018-11/` (không commit).

| Module trong review | Line chạy / tổng statement | Line+branch coverage |
|---|---:|---:|
| `chunking/markdown.py` | 245/329 | 68% |
| `training/train.py` | 41/180 | 22% |
| `training/control.py` | 88/115 | 74% |
| `cli/main.py` | 128/239 | 49% |
| `ingestion/recovery.py` | 24/42 | 52% |
| `pipelines/indexing.py` | 139/182 | 74% |
| `embeddings/corpus_builder.py` | 114/142 | 77% |
| `configuration.py` | 66/73 | 86% |
| `artifacts.py` | 58/73 | 72% |
| `schemas.py` | 19/21 | 89% |
| `training/evaluate.py` | 46/78 | 57% |
| `training/gpu_diagnostics.py` | 0/51 | 0% |
| `training/preflight.py` | 13/69 | 18% |
| `training/readiness.py` | 43/53 | 80% |
| `evaluation/metrics.py` | 26/28 | 88% |

Integration đã có: FAISS/SQLite thật; HTTP localhost gọi /api/chat và kiểm tra
status/schema với model mock; test_real_peft_cpu dùng Transformers, PEFT,
tokenizers và torch thật, model GPT2 rất nhỏ khởi tạo tại chỗ. Test CPU kiểm tra
assistant masking, loss hữu hạn, gradient adapter, save/reload tokenizer/adapter
và parity logits; không tải checkpoint, không chứng minh Qwen/QLoRA 4-bit CUDA.
Test tokenizer Qwen chính thức chỉ chạy nếu cache có sẵn, nếu không phải skip.

Chưa kiểm chứng E2E đầy đủ PDF → OCR → BGE-M3 → retrieval → Qwen/QLoRA → API;
chưa có bằng chứng GPU training/resume hoặc bitsandbytes thật từ suite này.
Mock loading tests vẫn hữu ích để kiểm tra tham số/policy, không coi là PEFT
integration; test CPU thật bổ sung một lớp bằng chứng riêng.

Unittest tự in expected/actual, traceback và tên test; thiếu msg không đồng
nghĩa thiếu diagnostics. Dùng subTest cho nhiều case; thêm message vào assertion
nghiệp vụ (masking, gradient, logits), không thêm thông báo lặp lại biểu thức.

Lượt xác nhận bằng verify_tests.py: exit 0; 194 test, 3 skip. Skip cụ thể:
thiếu dataset v4, tokenizer Qwen không có cache, container không có Node.js
cho kiểm tra JavaScript UI. Coverage.py 7.16.2.
