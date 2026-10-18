# TASK-20261018-20 — partial

- Triển khai local không Docker và đánh giá Golden Dataset.
- Đã xác minh: Python thực/`py`/`uv`/`ollama` chưa có trong PATH; Golden Dataset có `train_golden.jsonl` (2.200), `val_golden.jsonl` (550), `test_golden.jsonl` (1.100); `nvidia-smi` có sẵn.
- Đã cài Python 3.14.7 và Python 3.12.10 bằng winget; Ollama installer vẫn đang hoàn tất. Đang tạo venv Python 3.12 với extras RAG/evaluation/test/dev.
- Phạm vi đã đổi theo yêu cầu: chỉ chuẩn bị môi trường và cung cấp lệnh chấm `base`; không khởi động Web Chat, không tải model, không chạy Golden ở lượt này.
- Hoàn tất chuẩn bị: `.venv` Python 3.12 với `.[rag,evaluation,test,dev]`; `pip check`, `vigov doctor`, compileall PASS. Ollama local chạy nhưng chưa có model. `torch 2.14.1+cpu` chưa nhìn thấy CUDA.
- Bước tiếp: khi người dùng yêu cầu, tải `qwen2.5:7b`, chạy Web Chat localhost port 8001, preflight 1–2 mẫu và chấm đủ Golden `test` theo các lệnh trong lịch sử task.
- Bổ sung kết quả thực tế: Base và RAG đã chạy/được export đủ 1.100 mẫu, 1.100 success mỗi run, trace v1.0 đầy đủ. Stage vẫn partial vì các metric cần telemetry, citation hoặc judgment/scorer bổ sung chưa được thu thập hay triển khai.
- Giai đoạn mới: bổ sung scorer offline riêng cho prediction đã lưu. Mục tiêu: MAP@5 RAG (vì artifact chỉ có top-5), BERTScore và lexical mở rộng; artifact mới, không ghi đè kết quả v2 cũ và không gọi model hỏi đáp.
- Đã hoàn tất supplemental scorer offline: chrF, SacreBLEU, CER/WER, BERTScore (`xlm-roberta-large`, CPU, batch 8) cho cả Base/RAG; MAP@5 RAG = 0,3659166667 trên 1.000 ca relevance. Artifact `offline_scores_v2_bertscore.json` nằm cạnh từng run. Không có inference mới.
- Task partial: các metric semantic/groundedness/citation/judgment, MAP@10/sub-query/multi-intent và telemetry hiệu năng vẫn cần input hoặc trace mới nên không được tính hồi tố.
- Không sửa Golden Dataset hoặc artifact lịch sử. Cần xác minh model, corpus vector và endpoint web trước khi chạy evaluation.

## Mốc trước

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
