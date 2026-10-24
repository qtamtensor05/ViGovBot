# TASK-20261023-08 - in_progress, viết báo cáo phân tích mô hình QLoRA + RAG

- Nhiệm vụ: Phân tích kết quả thực tế từ đợt chấm qlora-rag (run qlora-rag-partial-682-20261023) trong ackups/vigovbot-qlora-rag-partial-682-20261023-041931/ và bổ sung vào hệ thống docs.
- Tiến độ: Đã trích xuất số liệu 682 mẫu, ma trận metrics offline, phân tích router vs rag_search subset (Key Fact 51,30%); đang biên soạn báo cáo chi tiết.
- Việc còn lại: Xuất báo cáo docs/reports/bao-cao-danh-gia-chi-tiet-model-qlora-rag.md, cập nhật tài liệu tổng hợp và mục lục docs/README.md.

## Mốc trước

# TASK-20261023-07 - completed, hoàn thành 4 báo cáo phân tích chi tiết 3 mô hình Base, Base+RAG, QLoRA

- Đã hoàn tất 4 bài báo cáo phân tích chuyên sâu tại `docs/reports/`:
  1. `docs/reports/bao-cao-danh-gia-chi-tiet-model-base.md` (Đánh giá chi tiết Standalone Base)
  2. `docs/reports/bao-cao-danh-gia-chi-tiet-model-base-rag.md` (Đánh giá chi tiết Base + RAG)
  3. `docs/reports/bao-cao-danh-gia-chi-tiet-model-qlora-finetuning.md` (Quá trình huấn luyện V100 & đánh giá QLoRA)
  4. `docs/reports/bao-cao-so-sanh-tong-hop-3-model-base-rag-qlora.md` (So sánh tổng hợp & đối sánh đa chiều 3 model)
- Toàn bộ ma trận số liệu (30+ metrics) được trích xuất 100% từ artifact thật trong `backups/vigovbot-stage-offline-pass-20261023-005223/`.
- Đã cập nhật mục lục tài liệu tại `docs/README.md`; kiểm chứng link test `test_documentation` PASS 100%.
- Hồ sơ dự án tại `docs/project/requests.md`, `docs/project/current-stage.md`, `docs/project/implementation-history.md` đã cập nhật đầy đủ.

## Mốc trước

# TASK-20261023-05 - partial, tối ưu capture QLoRA + RAG

- Runtime ghi nhận 18/53 HTTP 502 do câu trả lời structured của QLoRA rỗng;
  decomposition fallback đã hoạt động, lỗi nằm ở generation chính.
- Đã thêm `min_new_tokens=8` cho các lượt structured, giới hạn decomposition
  còn 128 token và bỏ lượt repair thứ ba khi retry vẫn rỗng.
- Local compileall/diff-check PASS; unit test local SKIPPED do thiếu `filelock`.
  Cần đồng bộ ba source và test một case lỗi thật trên container trước khi resume.

## Mốc trước

# TASK-20261023-06 - completed, đã vẽ biểu đồ training QLoRA

- Đã xác định run thực tế tại
  `backups/vigovbot-stage-offline-pass-20261023-005223/outputs/qlora/qlora-v100-optimized`.
- Đã tạo 9 PNG và `plot_manifest.json` trong thư mục `plots/` của run, gồm loss,
  learning rate, gradient norm, GPU memory, thời gian/epoch, throughput và tỷ lệ
  tham số. Toàn bộ PNG đọc được; test plotting 2/2 PASS.
- `evaluation_comparison.png` không tạo vì run chưa có post-training test artifact;
  manifest ghi rõ unavailable. Không chạy lại training/model hoặc sửa checkpoint.

## Mốc trước

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
# TASK-20261023-08 - completed, QLoRA không treo và đã trả API 200

- Web/Ollama đang healthy; `/` và `/api/models` trả 200.
- Hai 404 quan sát được là `/favicon.ico` và `/.well-known/appspecific/com.chrome.devtools.json`, chưa liên quan endpoint chat.
- Lần gọi đầu tải đủ 4 shard `Qwen/Qwen2.5-7B-Instruct` trong 7 phút 48 giây, sau đó nạp 4/4 checkpoint shard trong khoảng 27 giây.
- Khi sinh câu trả lời, GPU RTX 4050 dùng 5.884/6.141 MiB; không có OOM, container không restart và request kết thúc bằng `POST /api/chat HTTP/1.1 200`.
- Adapter 170 MB mount đúng tại `/app/models/qlora`; không sửa code, checkpoint hoặc adapter. Cache Hugging Face được giữ trong volume nên lần gọi sau không cần tải lại các shard này.
# TASK-20261023-09 - in_progress, nâng cấp ASGI và HTTP pooling

- Đang thay `ThreadingHTTPServer` bằng FastAPI/Uvicorn, giữ nguyên contract Web API.
- Đang chuyển adapter evaluation sang connection pool sống theo context `http_rag`.
- Source và fixture Uvicorn đã cập nhật; Ruff, compileall và documentation pass. Runtime server chưa xác nhận do thiếu dependency; evaluation-v2 có 2 lỗi thiếu sacrebleu. Trạng thái partial.
- Bổ sung FastAPI/Uvicorn và dependency trực tiếp vào lock inference Docker sau khi runtime báo `ModuleNotFoundError: fastapi`; đang rebuild riêng service web và chờ readiness.
- Tách dependency FastAPI/Uvicorn sang `locks/web-linux-py312.txt` và di chuyển `pyproject.toml` xuống sau layer inference; thay đổi source/web sau này không còn invalid layer Torch/CUDA.
# TASK-20261023-10 - completed, đã thêm format policy có điều kiện

- Đã xác nhận retrieval/corpus không làm mất toàn bộ xuống dòng: 117.871 chunk runtime đều có newline; chunk mẫu còn tiêu đề, bảng và nhãn Bước.
- Web UI giữ newline bằng `white-space: pre-wrap`; request RAG mẫu trả 3 bước tách đoạn đúng.
- Đã thêm contract trình bày theo ý định câu hỏi: trình tự/các bước tách từng dòng; hồ sơ và phí/thời hạn tách từng mục; câu hỏi giải thích không bị ép thành danh sách.
- PASS: 3 test mới, multi-turn 5 pass + 1 skip, Ruff, compileall và diff-check. `test_rag_pipeline` chưa chạy do host thiếu `faiss`; chưa restart container/chạy model sau sửa.
- Không sửa ingestion hoặc rebuild corpus; một số PDF chunk vẫn có thể dính ranh giới bước từ dữ liệu nguồn và cần audit riêng nếu còn tái diễn.
# TASK-20261023-11 - completed, exact lookup source_code đã chạy runtime

- Đáp án có trong corpus: mã `1.116222` có số quyết định `3826/QĐ-UBND`.
- Request thực tế không lấy chunk `1.116222` vào top-5; model abstain đúng vì context thiếu bằng chứng.
- Đã thêm exact filter theo mã, semantic ranking trong đúng thủ tục và SQLite expression index tự nâng cấp cache cũ sau checksum.
- Runtime PASS: `1.116222` trả `3826/QĐ-UBND`, top-5 đều đúng mã; `9.999999` không lấy mã gần giống. Web healthy sau restart.
- Ruff, compileall, parser mã và diff-check PASS. Unit FAISS mới chưa chạy trên host vì thiếu dependency, nhưng đường chạy thực trong container đã được xác minh end-to-end.
# TASK-20261023-12 - completed assessment, chưa triển khai engine

- vLLM khả thi nhất cho PoC nhờ adapter OpenAI-compatible sẵn có; SGLang để so sánh sau.
- Chưa thể kỳ vọng tăng throughput ở evaluation v2 vì client hiện gửi tuần tự; cần concurrency có giới hạn trước khi continuous batching có tải để gom batch.
- RTX 4050 6 GB không phù hợp mục tiêu 8-16 request Qwen 7B/context 8k; V100 32 GB có triển vọng hơn nhưng là thông tin lịch sử, chưa xác minh runtime hiện tại.
- Không cài dependency, tải model, sửa Docker hoặc chạy benchmark. Bước tiếp theo nếu được duyệt: PoC riêng vLLM + concurrency 1/2/4/8, khóa contract JSON schema và đo A/B với Ollama.
# TASK-20261023-13 - completed measurement, không cleanup

- Docker logic: images 25,43 GB + volumes 25,94 GB + containers 0,08 GB + build cache 17,08 GB.
- ViGovBot chiếm chính: web image 12,63 GB unique, Ollama image 9,375 GB, HF cache 19,81 GB, model Ollama 4,683 GB, RAG cache 1,164 GB.
- Docker Desktop VHDX thực tế 93,99 GB. Build cache 17,08 GB được báo reclaimable; chưa xóa vì người dùng mới yêu cầu kiểm tra.
- Compose ViGovBot hiện dừng; không suy diễn trạng thái inference từ artifact còn trên disk.
# TASK-20261023-14 - completed cleanup, volume được bảo toàn

- Đã thu hồi 17,08 GB build cache và xóa 1,31 GB image không còn container tham chiếu.
- Trạng thái logic sau dọn: images 24,12 GB; volumes 25,94 GB; containers 80,01 MB; build cache 0 B.
- Ba volume ViGovBot model/HF/RAG vẫn nguyên vẹn. Không xóa container, database volume hoặc adapter/checkpoint host.
- VHDX Docker Desktop vẫn 93,99 GB; chưa compact vì thao tác đó cần dừng Docker/WSL và nằm ngoài cleanup cache hiện tại.

# TASK-20261023-15 - completed, Web healthy sau cold start

- Docker Desktop đã khởi động Compose; Web không crash/restart mà đang nạp FAISS, 117.871 vector và `BAAI/bge-m3` trước khi mở cổng HTTP.
- Trong pha này, `health: starting`, `ConnectionRefusedError` và PowerShell `ResponseEnded` là do server chưa bind cổng, không phải Ollama hay model bị xóa.
- Đã chờ không restart; Web tự chuyển `healthy` và `/api/health` trả `status: ok`.
- Không sửa source/config, rebuild image hay xóa volume.

# TASK-20261023-16 - completed diagnosis, chưa sửa ranking

- Exact lookup đúng mã nhưng semantic ranking trong 10 chunk cùng mã đặt `procedure_step` ở hạng 7, ngoài top-5.
- Corpus giữ nguyên đủ Bước 1-3; top-5 chỉ có thời hạn/phí, metadata và hồ sơ nên model ghép sai chúng thành bốn bước.
- Kết luận: retrieval ranking failure kéo theo unsupported generation; format policy chỉ làm câu trả lời sai trông có cấu trúc rõ hơn, không tạo ra lỗi dữ liệu.
- Chưa sửa code/index. Hướng tiếp theo: intent-aware section filtering/boosting sau exact-code filter và regression mã `1.000020`.

# TASK-20261023-17 - completed, intent-aware exact lookup

- Exact-code retrieval nay ưu tiên section theo ý định cho trình tự, hồ sơ và phí/thời hạn/cách thức; semantic score vẫn xếp trong nhóm và lấp top-k bằng các chunk còn lại.
- Runtime mã `1.000020`: `procedure_step` từ hạng thô 7 lên nguồn đầu; API trả đúng ba bước trong corpus, 5/5 nguồn cùng mã. Web healthy sau restart.
- PASS: Ruff, compileall, diff-check, mapping container và API end-to-end. Unit FAISS host skip do thiếu dependency; không rebuild corpus/index.
# TASK-20261024-01 - Phân luồng RAG đã triển khai, chờ runtime

- Ngoài phạm vi trả thông báo cố định, không hỏi lại; mixed truy hồi phần thủ tục và thông báo phần ngoài phạm vi; thiếu đối tượng vẫn clarify.
- Không có hit cho mã cụ thể: thông báo giới hạn dữ liệu; retriever kiểm tra SQLite trước embedding. Thiếu context bỏ qua generation; prompt phân biệt thiếu nội dung với thiếu đối tượng.
- Kiểm chứng: 40 test pass, 1 skip do thiếu dataset v4; Ruff pass. Docker daemon đang tắt nên chưa restart/đo tốc độ hoặc kiểm chứng phân loại bằng model thật.
# TASK-20261024-02 - completed source/test, benchmark Retrieval-only

- Đã thêm hai lệnh `retrieval-run` và `retrieval-score` trong namespace evaluation hiện có; artifact giữ ranking, nội dung chunk, provenance và timing, scorer báo Hit/Recall/MRR tại nhiều k.
- Luồng chạy chỉ nạp query encoder, FAISS và SQLite; không dùng tokenizer/LLM/router/rewrite/decomposition/generation.
- PASS: 13 test retrieval/review, Ruff evaluation, compileall, documentation test và diff-check. Test cấu hình FAISS/runtime thật SKIPPED vì Python host thiếu `faiss`, `sentence_transformers`, `torch`; dataset `rag_tthc_three_1500` không có trên host.
- Reranker và tối ưu batch nằm ngoài task này. Bước tiếp theo là chạy `retrieval-run` trên máy có dependency + dataset, duyệt mapping rồi chạy `retrieval-score`; không tuyên bố latency/chất lượng thật ở lượt triển khai source.
- Mở lại `in_progress`: đang bổ sung và chạy contract Golden file trực tiếp cho 1.100 mẫu `test_golden.jsonl`; Docker daemon hiện chưa chạy và host không có dependency Retrieval.
- Docker đã sẵn sàng; container Web có FAISS 1.15.1, Sentence Transformers 5.7.0, Torch 2.9.1+cu128 và CUDA. Smoke 2 mẫu Retrieval-only + score hoàn tất, không gọi Ollama; đang chuẩn bị chạy đủ 1.100 mẫu Top-20 vào `outputs/retrieval/golden-test/`.
- Hoàn tất 1.100/1.100: 1.000 answerable được chấm, 100 unanswerable `not_applicable`. Hit@1/3/5/10/20 = 64,1%/85,7%/92,2%/96,6%/97,3%; Recall tương ứng 63,75%/85,2%/91,7%/96,35%/97,2%; MRR = 0,6410/0,7357/0,7507/0,7569/0,7575.
- Warm measured region 48,699 giây, 22,588 query/s; mean/p50/p95/p99 = 41,78/37,61/81,86/99,48 ms. Setup/encoder load bị loại khỏi vùng đo; 27/1.000 answerable miss ở Top-20, gồm 16 multi-intent và 11 single-hop.
- Artifact: `outputs/retrieval/golden-test/golden-test-top20.jsonl`, manifest `.run.json`, và `golden-test-top20-scores.json`. Reranker chưa triển khai.
# TASK-20261024-03 - completed, rerank Golden Top-20

- Dùng ranking cố định `outputs/retrieval/golden-test/golden-test-top20.jsonl`; không chạy lại FAISS và không gọi LLM.
- Đang bổ sung runner offline `BAAI/bge-reranker-v2-m3`, đo model-load/rerank riêng và tổng warm bằng retrieval baseline 48,699 giây.
- Artifact dự kiến nằm cùng `outputs/retrieval/golden-test/`; sau smoke sẽ chạy đủ 1.100 mẫu rồi chấm Top-1/3/5/10/20.
- Smoke 2 mẫu PASS: model 567.755.777 tham số, CUDA FP16, load lần đầu 48,16 giây; rerank 1,22 giây. Evidence mẫu đầu bị đẩy hạng 1 → 2 nên chưa kết luận cải thiện; bắt đầu full 1.100 mẫu vào `golden-test-top20-reranked-bge-v2-m3.jsonl`.
- Full 1.100 hoàn tất: rerank warm 281,010 giây, 3,914 query/s, mean/p50/p95/p99 = 253,50/281,87/386,82/406,42 ms; cached model load 3,820 giây. Retrieval + rerank warm = 329,709 giây, cached cold = 333,529 giây.
- Chất lượng không đạt: Hit@1 64,1% → 62,4%; Hit@3 85,7% → 86,4%; Hit@5 92,2% → 91,3%. Recall@5 91,7% → 90,8%; MRR@5 0,7507 → 0,7426. Tại k=5 có 42 ca cải thiện nhưng 51 ca xấu đi.
- Kết luận: chưa tích hợp `bge-reranker-v2-m3` vào runtime/generation. Giữ artifact để audit/A-B; cần thử model/cấu hình khác hoặc fine-tune theo TTHC nếu tiếp tục.
- Đã A/B model nhẹ `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` trên cùng Top-20, CUDA FP16, batch 20, max length 512; vẫn không gọi LLM.
- MiniLM 117.641.089 tham số hoàn tất 1.100 mẫu trong 45,472 giây, 24,191 query/s; mean/p50/p95/p99 = 39,32/42,65/57,98/65,44 ms. Cached model load 3,184 giây; Retrieval + rerank warm = 94,171 giây.
- Baseline → MiniLM Hit@1/3/5/10/20: 64,1/85,7/92,2/96,6/97,3% → 65,2/87,0/91,2/95,5/97,3%. Recall: 63,75/85,2/91,7/96,35/97,2% → 65,2/86,65/90,85/94,95/97,2%. MRR tăng ở mọi k, MRR@5 = 0,761683.
- Kết luận: MiniLM đáng thử cho mục tiêu nén xuống Top-3 vì Hit@3 tăng 1,3 điểm phần trăm và MRR@3 tăng 0,0162, nhưng không phù hợp nếu KPI chính là Hit/Recall@5 hoặc @10. Chưa tích hợp runtime/generation.
