# TASK-20261018-19 — completed

- Đã nối trace pipeline → Web Chat opt-in → run-v2 → export-v2; không đổi inference settings.
- Route thực thi, rewritten query, context, citation khi bật và timing thực có được lưu.
- Citation thiếu trace trả null/missing_input; scorer offline version 2. Token estimate giữ riêng.
- PASS: 217 tests (212 pass, 5 skip), gồm HTTP localhost với model fixture; Ruff, compileall, diff-check.
- Docker runtime chưa nạp bản sửa: docker compose ps không kết nối được dockerDesktopLinuxEngine (daemon không sẵn sàng). Không chạy model/GPU; chưa commit. Không sửa Golden/checkpoint hoặc artifact cũ.

## Mốc trước

# TASK-20261018-18 — completed

- Discovery Python tối giản: 38 tests, 10 pass, 28 skip đúng dependency.
- Venv Python 3.12 offline: 213 tests, 208 pass, 5 skip có lý do.
- Chunker tách headings/splitter, class 178 dòng; 48 parity cases giữ nguyên.
- Ba evaluation adapter dùng chung execution engine, giữ output/resume contracts.
- Training runtime dùng TrainingConfig; 7 profile snapshot parity với source cũ.
- Ruff, compileall, pip check, documentation và diff-check pass.
- Chưa chạy GPU/model/Mypy/Docker; không commit. Không còn việc triển khai trong phạm vi task.
- Chi tiết: [lịch sử](implementation-history.md), [yêu cầu](requests.md), [lỗi](failure-journal.md).

## Mốc trước

# TASK-20261018-17 - partial

- Đổi scoring_legacy thành judgment_scoring, cập nhật caller/docs và format scorer.
- Fingerprint bao phủ toàn bộ Python package; thay đổi helper/new nested module
  cũng invalidates run. Conservative: thay đổi Python không liên quan cũng đổi hash.
- Bỏ override RTX trùng; Ollama URL dùng YAML anchor; skills inventory/test đủ 16.
- BLEU đã chung backend; evaluation dataset đã null từ task trước.
- Chưa hợp nhất ba runner; chưa đổi tên toàn bộ namespace theo domain.
  Smoke config chỉ chứa experiment override, kế thừa hardware environment.
- PASS: 64 tests trong uv tạm, Ruff, compileall và diff-check.
  Không chạy model/GPU/Docker.

## Mốc trước: TASK-20261018-16 - partial

- Đã alias SHA-256 v2 về artifacts; baseline normalization và ROUGE tokenizer
  dùng helper chung, contract baseline-vi-lexical-v3. Đã gom fixture masking.
- 26 test liên quan: 23 pass, 3 skip do dependency/model không sẵn có.
- Git xác nhận .gitattributes/.gitignore/stage archive/ingestion.yaml đã commit
  trong 8a65476; JSONL readers đã gom ở TASK-15, recovery log giữ riêng.
- Còn: chunker chưa tách tiếp; training runtime vẫn dùng validated dict.
  Giữ lock bảo vệ unload/switch GPU và opt-in model experimental.
- Chưa kiểm chứng GPU/model/Docker; không commit hoặc thay index của task trước.

## Mốc trước: TASK-20261018-15 - completed

- BLEU dùng chung SacreBLEU; baseline version mới giữ scale 0–1 và macro
  sentence aggregation. Không so trực tiếp với corpus BLEU hoặc report cũ.
- JSONL file/ZIP/scoring/multi-turn/training logs/corpus fallback dùng parser
  chung; recovery log giữ riêng và không áp dụng cho dataset.
- PASS: 11 test (shared contracts + multi-turn), Ruff và diff-check.
  SKIPPED: 1 test cần dataset v4. Chưa chạy model/GPU/Docker hoặc full suite.
- Các thay đổi đã stage từ TASK-14 được giữ nguyên; task này chưa commit.

## Mốc trước: TASK-20261018-14

- Commit `8a65476` đã theo dõi các module/test mới; không còn file untracked để
  `git add`. Các sửa đổi của TASK-14 đã được stage, chưa commit.
- Dataset v2 hiện có không tương thích loader legacy; không thay bằng path v2
  chỉ để file tồn tại. `vigov eva` tiếp tục chọn dataset qua `--dataset`.
- PASS: test metric khi có ROUGE; skip đúng khi thiếu ROUGE; ba profile load với
  dataset null; documentation, Ruff, compileall và diff-check pass.
- Docker Desktop đang tắt nên không chạy test container; kiểm chứng dùng môi
  trường `uv` tạm. Không chạy model, GPU hoặc benchmark.
- [Lịch sử triển khai](implementation-history.md) · [Stage archive](stage-history-20261018.md).
