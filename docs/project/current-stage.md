# TASK-20261023-04 - completed source, chờ người dùng chạy container

- Đã bổ sung profile `qwen-qlora-rag`, adapter override chung, CLI `noise-v2`
  để capture nhiễu và `score-noise-v2` để tổng hợp robustness offline.
- Không chạy model, train hoặc benchmark trong lượt triển khai; người dùng sẽ
  gọi lệnh trên container V100.

## Mốc trước

# TASK-20261023-02 — completed, complete-v2 tự khóa đủ trace

- `complete-v2` tự bật complete trace và yêu cầu web capability version 2: top-10, sub-query retrieval, citation, token, TTFT, latency, GPU samples, runtime identity và noise replay.
- Thiếu bất kỳ capability nào thì dừng trước inference. Không cần chỉnh YAML hoặc nhớ cờ thủ công.
- Đã đồng bộ lên `/workspace/ViGovBot`; remote 26 test PASS, Ruff PASS, compileall PASS. Không chạy model/evaluation.

## Mốc trước
# TASK-20261023-01 — triển khai V100 đã kiểm chứng, chưa chạy model

- Source, Golden train/validation và Golden evaluation đã được triển khai tại `/workspace/ViGovBot`; không truyền `.env`, checkpoint, cache hoặc vector index.
- Container dùng Python 3.11.17 trong `.venv-v100`, PyTorch 2.9.1+cu128; CUDA nhận Tesla V100-SXM2-32GB, SM70. Readiness `READY`, 2.200 train và 550 validation hợp lệ.
- Kiểm chứng remote: 41 test PASS, Ruff PASS, compileall PASS. Không tải model weights, không chạy smoke/train/evaluation/judge.
- Còn điều kiện vận hành có chủ đích: lần chạy model đầu sẽ tải tokenizer/weights; RAG cần đồng bộ `Data/vector/unified`; complete-v2 cần web service và Ollama judge model do người dùng chọn.
- Lệnh kích hoạt dùng `export PATH="/workspace/ViGovBot/.venv-v100/bin:$PATH"`; người dùng chủ động gọi smoke trước full training.

## Mốc trước

# TASK-20261022-03 — triển khai mở rộng, kiểm chứng offline

- Mốc bổ sung mới nhất: METEOR exact-Vietnamese/cosine, GPU sampling device-wide, local Transformers token/TTFT/allocator peaks, identity endpoint và resume khóa digest/config/index, noise replay có nhãn và paired scoring đã được nối complete-v2.
- Resume retry chỉ ca prediction lỗi, giữ backup lỗi; human riêng. Preflight chặn collector/dependency/judge thiếu trước inference. Chưa chạy model benchmark theo yêu cầu.
- Kiểm chứng cuối: 63 test offline PASS, gồm schema/docs, preflight thiếu GPU không inference, cosine/METEOR fixture, resume và noise replay; Ruff/compileall/diff-check PASS. Giới hạn có chủ đích: allocator Ollama/cost không có nguồn đo; noise không áp dụng ca không có distractor; exact METEOR không dùng tài nguyên synonym tiếng Anh.

- Mốc mới: complete-v2 điều phối prediction → judge resume → supplemental (thêm chrF++) → export; complete.json tổng hợp hai nhóm metric. Capability preflight, complete trace opt-in và provider_calls được lưu.
- Prediction resume và judge hash-bound giữ kết quả cũ; 58 test liên quan PASS trước mốc cập nhật cuối. Human riêng. Chưa hoàn thiện METEOR/cosine, hardware collectors, controlled noise; không cam kết toàn bộ schema có số.

- Đã nối judge-v2 → export-v2 --judgments; claim extraction, sub-query/mapping, MAP@10, citation IDs, TTFT/token usage Ollama và human pairwise.
- Schema result v2 mở rộng tương thích, hướng dẫn: docs/guides/evaluation-extended.md. Config bật tính năng theo hướng dẫn trên máy chạy, giữ mặc định hiện tại.
- PASS: 57 tests evaluation/schema/server/routing/providers/docs; Ruff; compileall; git diff --check.
- Runtime model/GPU/judge chưa chạy theo yêu cầu. Test rag_config_cli chưa chạy vì thiếu faiss trong venv kiểm thử.
- Giới hạn: semantic scores là judge binary/null, sub-query exact-normalized; GPU/VRAM/cost không đo vẫn null; token usage chỉ final generation call. Human calibration cần người thực sự review, không tạo điểm giả.
- Bước tiếp theo: người dùng chạy inference và judge trên máy cấu hình cao theo hướng dẫn; kiểm tra chất lượng judge trước khi công bố metric.

## Mốc trước
# TASK-20261022-02 — completed

- Đã thêm profile Golden SFT và test tùy chọn trong schema/loader/training.
- 12 test PASS: hai/ba split, evaluator, launch với GPU fixture, resume/hash/snapshot và tài liệu.
- Profile đọc đúng 2.200 train/550 validation; Ruff, compileall và diff-check PASS.
- Python host thiếu pydantic; dùng venv tạm có sẵn `vigov-sft-check` để kiểm thử.
- Không chạy GPU/model/tokenizer. Bước tiếp theo: kiểm tra token length và GPU smoke khi chuẩn bị train.
- Không còn việc triển khai trong phạm vi hai chỉnh sửa; giữ nguyên dataset/config base và thay đổi người dùng.

## Mốc trước

# TASK-20261022-01 — completed

- Đã tạo `Data/golden_dataset_sft/train_sft.jsonl` (2.200) và `validation_sft.jsonl` (550), CLI `vigov data golden-to-sft`.
- Train: 2.167 single-turn, 33 follow-up, 200 unanswerable. Validation: 546 single-turn, 4 follow-up, 50 unanswerable.
- Mapping/ID/thứ tự/Unicode, validator training và deterministic bytes PASS toàn bộ. SHA-256 cả ba Golden trước/sau không đổi.
- Exact overlap train/validation: ID=0, conversation=0, prompt history+question=0; question-only=2 (câu follow-up chung, giữ nguyên).
- 14/14 test converter/schema/documentation, Ruff, compileall và git diff --check PASS. Không chạy model/GPU, không sửa config, không tạo test_sft.
- Artifact thuộc Data đang bị Git ignore theo quy tắc sẵn có; không tự force-add. Không commit/push. Không còn bước triển khai; near-duplicate/model/tokenizer không kiểm chứng trong task.
- Hướng dẫn tái tạo: `docs/guides/training.md`; bằng chứng/hash/lệnh: `docs/project/implementation-history.md`.

## Mốc trước

# TASK-20261018-22 - completed analysis

- Đã triển khai phân tích chi tiết, đầy đủ và chuyên sâu toàn bộ kết quả đánh giá 2 mô hình `base-qwen2.5-7b-20261018-173953` và `rag-base-qwen2.5-7b-20261018-192403` trong thư mục `outputs/evaluation_v2/`.
- Hoàn thành báo cáo phân tích toàn diện tại `docs/reports/bao-cao-danh-gia-chi-tiet-base-vs-rag-v2.md` và artifact `bao-cao-danh-gia-base-vs-rag-v2.md`.
- Kết quả đối sánh nổi bật: Win rate của RAG đạt 87,45%; SacreBLEU tăng +1.046% (2,06 lên 23,66); BERTScore F1 đạt 0,9046; Key Fact Coverage tăng từ 21,38% lên 50,40%; CER giảm -88,5% và WER giảm -87,2%. Nhóm Multi-intent Fact Coverage tăng từ 8,5% lên 73,0%. Nhóm Unanswerable đạt Abstention Correctness 93,0%.
- Không can thiệp sửa đổi các artifact và dữ liệu đánh giá gốc.

## Mốc trước

# TASK-20261018-21 - completed verification

- Đã kiểm tra trực tiếp hai thư mục Base/RAG trong `outputs/evaluation_v2`: mỗi run có 1.100 prediction và 1.100 result, ID duy nhất, không thiếu/thừa, execution success và trace v1.0 available toàn bộ.
- Hash Golden `5bf3606d...a127` và hash prediction trong summary/offline scorer đều khớp file thực tế. Supplemental BERTScore cũng khớp cùng input.
- Base BERTScore F1 0,854424; RAG 0,904564. RAG MAP@5 0,365917 trên 1.000 ca có relevance; không có retrieved ID trùng trong artifact.
- RAG citation: 1.098 disabled, 2 unavailable. Token usage, throughput, TTFT, VRAM/GPU và cost đều null; semantic/groundedness/judgment chưa có. Không tuyên bố bộ metric đầy đủ.
- Không chạy lại model/GPU và không sửa artifact. JSON/schema validation bằng package `jsonschema` chưa chạy vì dependency không có trong Python hiện tại.

## Mốc trước

# TASK-20261018-20 - partial

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
# TASK-20261023-03 — completed, profile throughput đã đồng bộ

- Container đo thực tế: V100-SXM2 32 GB P0/300 W, 10 vCPU, 94 GiB RAM, còn 79 GB disk.
- Training: batch 2, eval batch 4, accumulation 4, checkpointing tắt, 4 worker pinned/persistent; effective batch vẫn 8.
- Evaluation: query encoder CUDA, BERTScore mặc định batch 16, complete-v2 tự giải phóng generation/judge trước offline GPU scoring.
- Remote: 48 test PASS, Ruff PASS, compileall PASS, config hiệu lực đã kiểm tra. Không chạy smoke/train/evaluation nên throughput và peak VRAM thực tế chưa đo.

# TASK-20261023-05 - partial, chờ test và resume Base + RAG trên container

- Runtime container xác nhận 21 lỗi đều là `HTTP 502`; web health OK, Ollama và
  GPU hoạt động. Log gốc: citation không tham chiếu exact answer span sau retry.
- Đang giữ contract structured answer nhưng chuyển lỗi thuần citation thành
  prediction thành công có `citations_status=invalid_model_output`; ca thành
  công cũ sẽ được giữ bởi `run-v2 --resume`.
- Local Ruff, compileall và diff-check PASS; chưa kiểm chứng runtime/model sau
  bản vá. Cần đồng bộ 6 file source/test, restart web rồi chạy test tập trung.

## Mốc trước
