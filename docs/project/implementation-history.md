# Lịch sử triển khai

## TASK-20261023-08 — Báo cáo phân tích chuyên sâu mô hình QLoRA + RAG (completed)

- Khai thác dữ liệu đánh giá thực tế của mô hình kết hợp `qlora-rag` (run `qlora-rag-partial-682-20261023`, 682 mẫu thuộc cohort answerable) từ thư mục `backups/vigovbot-qlora-rag-partial-682-20261023-041931/`.
- Thực hiện phân tích định lượng đa chiều và đối sánh trực diện trên cùng lát cắt 682 test cases với 3 cấu hình Base, Base+RAG, QLoRA Standalone:
  - SacreBLEU: 41,97 (gấp 1,78 lần Base+RAG 23,5).
  - Token F1: 0,5715 (cao hơn Base+RAG 0,4251, +34,4%).
  - ROUGE-L F1: 0,5638 (cao hơn Base+RAG 0,4005).
  - BERTScore F1: 0,9215 (cao hơn Base+RAG 0,9037).
  - Character Error Rate (CER): 0,7229 (giảm gần một nửa lỗi so với Base+RAG 1,3192).
  - Độ dài câu trả lời: 36,57 tokens/câu (ngắn gọn nhất trong 4 cấu hình).
- Phân tích bóc tách luồng định tuyến (Router Breakdown):
  - Luồng `rag_search` thực tế (346 ca): Key Fact Coverage vọt lên **51,30%** (kỷ lục cao nhất toàn bộ dự án, vượt Base+RAG 49,63%), Token F1 đạt **67,40%**.
  - Luồng `clarify` (279 ca) và `out_of_scope` (56 ca): Router phân loại quá phòng thủ, kéo Key Fact trung bình toàn tập 682 ca xuống 36,58%.
  - Kết luận: Khi router được tối ưu lên >95%, QLoRA+RAG sẽ dẫn đầu toàn diện cả về độ chính xác sự kiện lẫn phong cách súc tích.
- Xuất bản báo cáo chuyên sâu:
  - `docs/reports/bao-cao-danh-gia-chi-tiet-model-qlora-rag.md`
  - Cập nhật mục 6.1 thực chứng 4 mô hình trong `docs/reports/bao-cao-so-sanh-tong-hop-3-model-base-rag-qlora.md`.
  - Cập nhật mục lục `docs/README.md`.
- Kiểm chứng: `python -m unittest discover -s tests -p test_doc*.py` PASS.

## TASK-20261023-07 — Báo cáo phân tích chuyên sâu 3 mô hình Base, Base+RAG, QLoRA (completed)

- Phân tích toàn diện 1.100 mẫu kiểm thử (1.000 answerable, 100 unanswerable) từ thư mục sao lưu backups/vigovbot-stage-offline-pass-20261023-005223/ cho 3 mô hình:
  1. base (Qwen2.5-7B-Instruct zero-retrieval)
  2. base-rag (Qwen2.5-7B-Instruct + ViGovBot Hybrid FAISS/BM25 RAG)
  3. qlora (Qwen2.5-7B-Instruct + QLoRA adapter v100-optimized)
- Khai thác toàn diện dữ liệu huấn luyện QLoRA:
  - Huấn luyện trên GPU NVIDIA Tesla V100-SXM2-32GB, 2.200 train / 550 val SFT.
  - Tối ưu 4-bit NF4, rank 16, alpha 32, paged_adamw_8bit, cosine scheduler, warmup 0.03, peak LR 2e-4.
  - Hội tụ nhanh: 1.255,66s (~20,9 phút), best checkpoint-500 đạt val loss 0.3928 (perplexity 1.4812), early stopping tại step 700. Peak VRAM 17,34 GB allocated / 18,37 GB reserved.
- Trích xuất ma trận so sánh định lượng đa chiều:
  - SacreBLEU: Base 1,98 | Base+RAG 23,67 (+1.096%) | QLoRA 55,32 (gấp 28 lần Base, 2,3 lần RAG).
  - chrF: Base 21,12 | Base+RAG 43,18 | QLoRA 62,72.
  - Token F1: Base 0,1346 | Base+RAG 0,4318 | QLoRA 0,7431.
  - Exact Match: Base 0,0% | Base+RAG 0,0% | QLoRA 18,36%.
  - Tỷ lệ lỗi ký tự (CER): Base 10,05 | Base+RAG 1,23 (-87,8%) | QLoRA 0,42 (-95,8%).
  - BERTScore F1: Base 0,8536 | Base+RAG 0,9044 | QLoRA 0,9598.
  - Key Fact Coverage: Base 20,40% | Base+RAG 50,52% (cao nhất) | QLoRA 35,30%.
  - Chiều dài phản hồi: Base 247,5 tokens (lan man) | Base+RAG 136,8 tokens | QLoRA 43,4 tokens (siêu ngắn gọn).
  - Phân tích nhóm unanswerable (100 ca): QLoRA đạt Token F1 81,61%, BERTScore 0,9696, CER 0,20; Base+RAG từ chối chuẩn xác (CER 0,75); Base giải thích xã giao dài dòng 170,5 tokens.
  - Phân tích độ trễ: Base 2,75s (TTFT 85ms) | QLoRA 4,70s (TTFT 319ms) | Base+RAG 7,21s (TTFT 976ms, prompt phình to 3.377 tokens).
- Xuất 4 bài báo cáo chuyên sâu hoàn chỉnh tại:
  1. docs/reports/bao-cao-danh-gia-chi-tiet-model-base.md
  2. docs/reports/bao-cao-danh-gia-chi-tiet-model-base-rag.md
  3. docs/reports/bao-cao-danh-gia-chi-tiet-model-qlora-finetuning.md
  4. docs/reports/bao-cao-so-sanh-tong-hop-3-model-base-rag-qlora.md
- Cập nhật mục lục tại docs/README.md.
- Kiểm chứng: python -m unittest discover -s tests -p test_doc*.py PASS. Không sửa đổi dữ liệu thô, không chạy lại inference giả lập.

## TASK-20261022-02 — Golden SFT hai split (completed)

- Thêm `configs/training/experiments/golden_sft.yaml`: kế thừa base, chọn
  train/validation mới và `test: null` để xóa đường dẫn test kế thừa.
- Schema chấp nhận test bỏ qua/null; dataset_paths lọc null, train chỉ đọc test
  khi có cấu hình. control_cli/validate_data dùng chung loader nên hỗ trợ hai split.
- Readiness hiển thị split thực tế; evaluator báo lỗi rõ khi yêu cầu test chưa cấu hình.
- Hash/snapshot giữ nguyên hợp đồng ba split; resume từ bộ cũ bị chặn theo config/hash.
- Kiểm chứng bằng Python trong `%TEMP%/vigov-sft-check`: unittest
  `tests.test_optional_training_test tests.test_training_schema tests.test_documentation
  tests.test_qlora_audit.ResumeAndStoppingTests.test_resume_rejects_config_or_dataset_drift`:
  12/12 PASS. Ruff trên 5 module sửa và test mới PASS; compileall, git diff --check PASS.
- Đọc artifact qua config/validator thật: train=2.200, validation=550, không có test.
- Không sửa dataset, base config hoặc checkpoint. GPU/model/tokenizer NOT RUN;
  launch dùng fixture CUDA, không suy diễn thành GPU readiness. Hướng dẫn ở `docs/guides/training.md`.

## TASK-20261018-22 — Phân tích chi tiết và đầy đủ kết quả đánh giá Base vs Base+RAG (completed)

- Phân tích toàn diện 1.100 mẫu kiểm thử của `base-qwen2.5-7b-20261018-173953` và `rag-base-qwen2.5-7b-20261018-192403` từ `outputs/evaluation_v2/`.
- Thực hiện trích xuất, tổng hợp định lượng đa chiều và đối sánh từng cặp qua script độc lập:
  - Tỷ lệ chiến thắng: RAG thắng 87,45% (962 ca), Base thắng 4,18% (46 ca, hầu hết ở nhóm unanswerable do đặc thù n-gram overlap), Hòa 8,36% (92 ca).
  - So sánh định lượng: SacreBLEU (2,06 lên 23,66, +1046%), BERTScore F1 (0,854 lên 0,905), Key Fact Coverage (21,38% lên 50,40%, +135,7%), CER giảm 88,5% (9,81 xuống 1,13), WER giảm 87,2% (9,95 xuống 1,27).
  - Phân tích retrieval: Hit@1 32,5%, Hit@5 43,8%, MRR@5 0,3693, NDCG@5 0,3838, MAP@5 0,3659; Router Accuracy 99,82%, Query Rewrite Similarity 99,67%; Retrieval latency trung bình 77,38 ms.
  - Phân tích taxonomy: Multi-intent Fact Coverage tăng từ 8,5% lên 73,0% (+64,5% tuyệt đối); Follow-up Fact Coverage tăng từ 12,5% lên 87,5%.
  - Phân tích Unanswerable (100 ca): RAG đạt Abstention Correct 93,0%, Unsupported Answer chỉ 7,0%; giải thích rõ hiện tượng "Nghịch lý Token F1" khi Base lặp lại câu hỏi lan man khiến n-gram overlap cao giả tạo.
  - Phân tích độ trễ: Generation latency của RAG giảm 31,3% (5.471 ms xuống 3.757 ms do trả lời súc tích); tổng độ trễ toàn trình tăng 1,45s (5.471 ms lên 6.919 ms) để đổi lại độ chính xác pháp lý vượt trội.
- Xuất báo cáo canonical tại `docs/reports/bao-cao-danh-gia-chi-tiet-base-vs-rag-v2.md` và artifact `bao-cao-danh-gia-base-vs-rag-v2.md`.
- Kiểm chứng: toàn bộ bảng dữ liệu khớp tuyệt đối với `results.jsonl.summary.json` và `offline_scores_v2_bertscore.json` của cả 2 run. Không có can thiệp hoặc thay đổi file đánh giá gốc.

## TASK-20261018-20 — Chuẩn bị chấm Base local (partial)

- Đã cài Python 3.12.10 trong `C:\Users\ezycloudx-admin\AppData\Local\Programs\Python\Python312` và tạo `.venv` tại gốc repository. Cài editable `.[rag,evaluation,test,dev]`; `pip check` PASS, `vigov doctor` PASS, compileall `src` PASS.
- Đã cài Ollama 0.40.5 local; process đang hoạt động tại `%LOCALAPPDATA%\Programs\Ollama\ollama.exe`. `ollama list` xác nhận chưa có model, nên chưa tải hoặc chạy model.
- Dataset/corpus giữ nguyên: Golden `test_golden.jsonl` có 1.100 ID; corpus unified manifest ghi BGE-M3 revision `5617a9f61b028005a4858fdac845db406aefb181`, 117.871 chunk. Không có output cũ dưới `outputs/evaluation_v2`.
- Xác minh GPU bằng `nvidia-smi`: NVIDIA GeForce RTX 5060 Ti, 16.311 MiB, driver 596.49. Torch cài từ extra RAG là `2.14.1+cpu`, nên `torch.cuda.is_available()` false; chưa có CUDA PyTorch runtime. Chấm Base qua Ollama không cần torch CUDA, còn web server vẫn sẽ tải encoder BGE-M3 nếu cache chưa có.
- Phạm vi đổi theo người dùng: chỉ chuẩn bị và cung cấp lệnh chấm `base`; không khởi động Web Chat, không tải `qwen2.5:7b`, không gọi API, không chạy Golden hay export-v2. Không sửa source, config, Golden, corpus, cache/checkpoint hoặc commit.

### Kết quả runtime do người dùng chạy sau chuẩn bị

- Base `base-qwen2.5-7b-20261018-173953`: `run-v2` và `export-v2` hoàn tất 1.100/1.100 success; trace 1.0 sẵn có 1.100/1.100. Artifact nằm tại `outputs/evaluation_v2/base-qwen2.5-7b-20261018-173953/`.
- RAG `rag-base-qwen2.5-7b-20261018-192403`: `run-v2` và `export-v2` hoàn tất 1.100/1.100 success; trace 1.0 sẵn có 1.100/1.100. Artifact nằm tại `outputs/evaluation_v2/rag-base-qwen2.5-7b-20261018-192403/`.
- Cả hai dùng Golden test SHA-256 `5bf3606d87690e3b1625f7dc31c593d4226d4b19c79aa9cd75e31aaca102a127`; không thiếu prediction, không lỗi/timeout/OOM. Export v2 là offline, không chạy BERTScore hoặc judge.
- Còn thiếu: BERTScore/các metric lexical mở rộng và embedding similarity (scorer v2 chưa triển khai); semantic, groundedness, claim/citation support và behavioral judgments (thiếu judgment có provenance); telemetry TTFT/token/throughput/VRAM/GPU/cost và rerank (trace trả null); citation trace (citations đang unavailable); MAP@10, sub-query và multi-intent coverage (scorer/trace chưa có đủ dữ liệu). Không được suy ra chúng từ số 0.

### Chấm bổ sung offline từ prediction cache

- Thêm `vigov eva score-v2-offline` tại `evaluation/offline_v2.py`; lệnh chỉ đọc Golden/prediction có hash và ghi JSON mới bằng exclusive create. Không gọi Web Chat, Ollama/Qwen hay sửa `results.jsonl` v2.
- Contract mới tách riêng: chrF và corpus SacreBLEU (0–100), mean CER/WER trên văn bản đã normalize NFC/casefold; MAP@5 dùng binary relevance, top-5 đã lưu và mẫu số AP `min(5, known_relevant)`. Không gọi MAP@5 là MAP@10. Base là `not_applicable` cho retrieval.
- BERTScore chạy sau đó bằng `xlm-roberta-large`, CPU, batch 8, toàn bộ 1.100 prediction/run. Base: P=0.822171, R=0.890069, F1=0.854424; RAG: P=0.901628, R=0.908594, F1=0.904564. Đây là similarity, không phải factual correctness/groundedness.
- Metric lexical bổ sung: Base chrF=21.4384, SacreBLEU=2.0640, CER=9.8085, WER=9.9533; RAG chrF=41.3178, SacreBLEU=23.6626, CER=1.1314, WER=1.2744. RAG MAP@5=0.365917 trên 1.000 ca có relevance labels; 100 unanswerable không áp dụng.
- Artifact mới: `outputs/evaluation_v2/base-qwen2.5-7b-20261018-173953/offline_scores_v2_bertscore.json` SHA-256 `daa24d1ae8a63fa10e407a30d27be960e3f1d2bb21731f6b4a820c35fe8bd886`; `outputs/evaluation_v2/rag-base-qwen2.5-7b-20261018-192403/offline_scores_v2_bertscore.json` SHA-256 `ea29f2a5d17438d198834adec915135e30939525e6db29866736a6f4a21e1315`.
- PASS: 14 `tests.test_evaluation_v2`, Ruff `src/vigovbot/evaluation`/test, compileall. Không chạy full suite. `embedding_cosine_similarity` và METEOR vẫn unavailable theo contract; semantic/judgment, citations, MAP@10/sub-query/multi-intent, telemetry không thể tái tạo từ artifact hiện có.

## TASK-20261018-17 — Scoring/fingerprint/config/skills (partial)

- PASS: 64 unittest thuộc test_agent_skills, test_qa_v4, test_qa_v4_review,
  test_shared_contracts, test_qlora_local, test_documentation, test_rag_config_cli;
  Ruff các file đổi, compileall và git diff --check. Môi trường uv tạm có
  dependency RAG/evaluation nhẹ; generation và BERTScore trong smoke được mock.

- Đổi module scoring_legacy thành judgment_scoring, sửa import và tài liệu;
  format scoring.py để tách semicolon/one-line blocks. Không đổi công thức.
- source_fingerprint duyệt toàn package Python, path POSIX ổn định; test thêm/
  sửa helper và nested chunking làm đổi hash. Phạm vi bảo thủ có thể invalidates
  run khi source không liên quan đổi; không sửa manifest lịch sử.
- Profile RTX kế thừa gpu thay vì copy giá trị base. Smoke profile đã tách
  hardware qua extends; giữ entry point. URL Ollama dùng YAML anchors.
- Doc skills phân biệt mốc hai skill cũ và inventory 16 hiện tại; test kiểm tra
  equality inventory và manifest của cả 16. UI metadata được kiểm tra nếu có.
- Các runner khác schema/history/resume vẫn riêng; namespaces theo domain không
  phải collision Python. Chưa thực hiện refactor rộng hai mục này.
- Không commit/push; giữ index công việc trước. Không chạy model/GPU/Docker.

## TASK-20261018-16 — Đối chiếu consolidation (partial)

- v2._sha256 alias artifacts.file_hash; regression xác nhận identity và đọc
  chunk thay vì read_bytes. Baseline normalize_answer dùng normalize_vietnamese;
  ROUGE dùng VietnameseTokenizer; version baseline-vi-lexical-v3 yêu cầu rescore.
- FakeTokenizer/MappingTokenizer chuyển vào tests/tokenizer_fixtures.py;
  audit không còn import fixture từ test module khác. Tokenizer tensor/generation
  và tokenizer kiểm tra mutation padding là test doubles khác hợp đồng, giữ riêng.
- JSONL ad-hoc đã xử lý TASK-15; experiments recovery riêng có truncate có chủ ý.
  git ls-files và git log xác nhận các mục 2.9–2.12 đã nằm trong commit 8a65476.
  Git ghi nhận rename bằng nội dung; không cần chạy lại git mv trên path đã đổi.
- Không bỏ GPU lock vì _switch_provider unload trọng số dùng chung; giữ model
  experimental opt-in do chưa xác minh tương thích. Chunker còn nhiều trách nhiệm
  và training runtime còn dict: chưa refactor, không tuyên bố hoàn tất hai mục này.
- Kiểm chứng: uv unittest tests.test_shared_contracts tests.test_qlora_local
  tests.test_qlora_audit: 26 test, 23 pass/3 skip. Không chạy model/GPU/Docker.

## TASK-20261018-15 — Hợp nhất BLEU và JSONL

- Chuyển BLEU baseline từ NLTK sang factory SacreBLEU chung, normalization
  Unicode chung; giữ output 0–1 và macro sentence aggregation để không đổi
  schema/biểu đồ. Version mới: baseline-sacrebleu-v2; comparison từ chối report
  khác version. EM/ROUGE baseline không thay đổi; cần rescore cached prediction.
- Mở rộng utils/jsonl.py thành parser stream dùng chung cho file và ZIP.
  Scoring, multi-turn, dataset, training plot/epoch và corpus JSONL fallback
  không còn tự parse từng dòng. Dòng trắng có policy rõ; báo lỗi kèm nguồn/số
  dòng; experiments recovery vẫn riêng vì có chức năng truncate khi được bật.
- Kiểm chứng trong môi trường uv tạm: unittest discover test_shared_contracts.py
  6/6 pass; test_multiturn.py 5 pass, 1 skip (thiếu dataset v4); Ruff các file
  đổi và git diff --check pass. Chưa chạy full suite, model/GPU hoặc Docker.
- Giữ nguyên index đã stage của TASK-14; không commit/push.

## TASK-20261015-14 - migration hai bộ Agent Skills theo Codex hiện hành

- Đối chiếu bốn nguồn OpenAI được yêu cầu, Codex CLI 0.160.0, layout repo/global
  và 15 skill hiện hữu; lập mapping trigger, resource, overlap và migration.
- Hợp nhất `context-management`, `repository-navigation` và
  `token-budget-optimization` thành `context-navigation`; cập nhật mọi caller,
  catalog, ví dụ và test trước khi bỏ bản song song.
- Rút gọn 12 skill còn lại, sửa chuỗi `\n` literal, mở rộng contract RAG cho
  ingestion, retrieval, dataset, API, security, single/multi-turn, no-answer,
  retrieval/generation/groundedness/performance metric và unavailable values.
- Giữ ba script, references, UI metadata, implicit invocation, chính sách dự án
  và toàn bộ application/data/model/artifact; không cài dependency hoặc chạy
  service/model/GPU/benchmark tốn phí.
- Bổ sung migration/source/catalog/test/benchmark docs và chuyển test khỏi
  heading/wording sang invariant manifest, discovery, routing, metric, valid và
  invalid fixture.
- Kiểm chứng: validator 16/16 PASS với UTF-8 mode; targeted 7/7; full suite 166
  PASS, 1 optional SKIP; Ruff, compileall và diff-check PASS. Phiên Codex mới và
  usage benchmark thật được ghi NOT VERIFIED/NOT RUN, không suy diễn savings.

## TASK-20261015-13 - cô lập CI khỏi dataset và artifact local

- Tái hiện CI từ checkout chỉ chứa file Git và xác nhận ba test dựa vào
  `Data/outputs` có sẵn trên máy phát triển.
- Chuyển test `data stats` và readiness sang JSONL/output fixture tạm; giữ nguyên
  hành vi trả lỗi của CLI khi dataset thật bị thiếu.
- Link test vẫn kiểm tra tài liệu/source nhưng không yêu cầu artifact runtime
  không version-control phải tồn tại trên runner.
- Kiểm chứng: 10 targeted test và full suite sạch 164 pass, 1 optional skip;
  Ruff, compileall và diff-check đạt. Không thay đổi workflow hoặc runtime.

## TASK-20261015-12 - Agent Skills RAG và tối ưu Codex

- Xác minh OpenAI/Codex, Agent Skills spec, Anthropic, Vercel và các skill RAG
  cộng đồng; phân loại OFFICIAL, COMMUNITY_VERIFIED, CUSTOM_REQUIRED, REJECTED.
- Tạo 7 skill RAG/chatbot và 8 skill tối ưu Codex ở cấp trực tiếp dưới
  `.agents/skills/` để phù hợp discovery, mỗi skill có contract, workflow, ví dụ,
  negative boundary và `agents/openai.yaml`.
- Thêm script standard-library cho ingestion JSONL, dataset leakage và benchmark
  summary; thêm metric/quality references theo progressive disclosure.
- Thêm `docs/agent-skills/`, test manifest/discovery/script, mục lục docs và
  routing ngắn trong `AGENTS.md`; không thay đổi application business logic.
- Kiểm chứng: 15 validator PASS; full suite 164 PASS, 1 optional SKIP; Ruff,
  compileall và diff-check PASS. Implicit trigger ở phiên Codex mới chưa được
  kiểm chứng nên task giữ trạng thái partial thay vì completed.

## TASK-20261015-11 - skill cấu trúc và README tổng quan

- Tạo skill `vigovbot-project-structure` quy định vị trí canonical cho source,
  CLI, configs, docs và artifact; quy định migration path, link validation và
  ranh giới kiểm chứng runtime.
- Cập nhật `AGENTS.md` để bắt buộc dùng skill khi thêm, di chuyển, đổi tên hoặc
  hợp nhất cấu trúc. Task journal tiếp tục chỉ quản lý hồ sơ triển khai.
- Viết lại README gốc thành trang tổng quan ngắn: khả năng chính, ba lệnh quick
  start, cấu trúc cấp cao và liên kết tới docs; bỏ giải thích dài về môi trường,
  RAG, GPU, lifecycle và command options khỏi README.
- Kiểm chứng: skill validator đạt với UTF-8 mode; 9 test documentation/CLI,
  Ruff, compileall và diff-check đạt. Không thay đổi hoặc chạy runtime.

## TASK-20261015-10 - hoàn thiện CLI ngắn cho web, dữ liệu và RAG

- Bổ sung `vigov web`, `vigov ask`, `vigov data ingest`, `vigov data embed` và
  nhóm `vigov rag prepare/smoke/evaluate/report/run`.
- Các handler chỉ chuẩn hóa option/path rồi gọi lại entry point hiện có; không
  sao chép business logic. Path tương đối được resolve từ project root nên lệnh
  dùng được ngoài repository sau editable install.
- Giữ nguyên compatibility CLI `python -m vigovbot ingest|embed|rag|qa-v4`.
- Cập nhật README, guide vận hành RAG và thêm `docs/guides/cli.md` làm bảng lệnh
  ngắn cho web, data, RAG, GPU, training, evaluation và reporting.
- Kiểm chứng: routing mock và 9 leaf help đạt; full suite 160 test pass,
  1 optional skip; Ruff, compileall và diff-check đạt. Không khởi động server,
  model, embedding, benchmark hoặc training thật.

## TASK-20261015-09 - phân nhóm tài liệu và kiểm tra liên kết

- Chuyển tài liệu ở gốc `docs/` vào `setup/`, `architecture/`, `guides/`,
  `training/`, `reports/`; chuyển roadmap vào `project/`. Gốc `docs/` chỉ còn
  `README.md` làm mục lục duy nhất.
- Viết lại mục lục theo luồng sử dụng và cập nhật tham chiếu trong README gốc,
  CONTRIBUTING, requirements, notebook README và README các module.
- Sửa liên kết tương đối sau khi tăng độ sâu thư mục; thay `file:///c:/Users/...`
  trong báo cáo QLoRA bằng đường dẫn repository portable; sửa đường dẫn dataset
  báo cáo theo layout thực tế.
- Thêm `tests/test_documentation.py` để kiểm tra mọi local Markdown link trong
  source/docs. Hồ sơ lịch sử `docs/project/` được giữ nguyên nội dung cũ.
- Kiểm chứng: 158 test pass, 1 optional skip; Ruff, compileall và diff-check đạt;
  không còn tham chiếu hoạt động tới đường dẫn tài liệu cũ.

## TASK-20261015-08 - phân nhóm toàn bộ cấu hình theo chức năng

- Chuyển cấu hình nguồn thành ba miền: `configs/ingestion/`, `configs/rag/` và
  `configs/training/`; loại bỏ các YAML phẳng trùng vai trò ở gốc repository và
  gốc `configs/`.
- Sửa đường dẫn tương đối trong pipeline ingestion và RAG để tiếp tục resolve
  đúng `Data/` và `outputs/`; giữ nguyên giá trị QLoRA cùng chuỗi `extends`.
- Cập nhật default/path trong CLI, loader, PowerShell, Python script, notebook,
  test, README và tài liệu vận hành. Snapshot `config.yaml` trong run lịch sử
  không bị di chuyển hay sửa đổi.
- Thêm `configs/README.md` và test khóa cấu trúc/đường dẫn mới; `vigov doctor`
  cùng `vigov data stats` đã chạy thành công từ ngoài repository.
- Kiểm chứng: 157 test pass, 1 optional skip; Ruff, compileall và
  `git diff --check` đạt. Không chạy training, không tải model.

## TASK-20261015-02 — cập nhật kết quả benchmark test set vào báo cáo QLoRA

- Cập nhật tài liệu `docs/bao-cao-phan-tich-qlora-qwen2-5-7b.md` với toàn bộ kết quả
  chạy kiểm thử và chấm điểm 1.000 ca test `tthc_test_case_v1` từ artifact
  `outputs/tthc_test_case_v1/scores_qwen_qlora_batch4.json` và run log.
- Nội dung cập nhật chi tiết:
  + Thay thế ghi chú "chưa có kết quả test" tại Mục 6 bằng phân tích chuyên sâu gồm:
    * Bảng đối chiếu 3 chiều giữa Qwen Base, RAG và QLoRA trên cùng 1.000 ca test.
    * Phân tích per-action breakdown cho 5 nhóm hành động: `answer` (600 ca), `partial` (140 ca),
      `correct_premise` (70 ca), `abstain` (130 ca), `clarify` (60 ca).
    * Phân tích tốc độ suy luận (latency, p50, max) và lợi ích của batch inference (batch_size=4).
    * Tổng hợp ưu nhược điểm so sánh giữa QLoRA và RAG: QLoRA vượt trội về câu văn pháp lý chuẩn xác,
      độ mượt ngữ nghĩa (Sentence BLEU 61,38 vs 31,15, ROUGE-L 0,7169 vs 0,5069, BERTScore 0,9514 vs 0,9041,
      EM 26,30% vs 0%), đặc biệt là khả năng phát hiện tiền đề sai (BLEU 84,17).
  + Cập nhật bảng tóm tắt kết quả tại Mục 7 (Kết luận & Đề xuất).
- Kiểm chứng: số liệu khớp 100% với `scores_qwen_qlora_batch4.json`, `scores_c4_full.json`,
  và `scores_qwen_baseline_schema_c4.json`.

## TASK-20261014-09 — báo cáo phân tích triển khai QLoRA Qwen2.5-7B

- Tạo tài liệu `docs/bao-cao-phan-tich-qlora-qwen2-5-7b.md` phân tích toàn bộ quá trình
  triển khai QLoRA trên `Qwen/Qwen2.5-7B-Instruct` với dữ liệu thực nghiệm thật từ
  run `outputs/qlora/qlora-full-20261014-153839-desktop-7pkpjrj-ea78be2d`.
- Nội dung báo cáo phân tích:
  + Cấu hình kiến trúc: 4-bit NormalFloat (NF4), double quantization, bfloat16 compute dtype,
    LoRA rank r=16, alpha=32, target all 7 linear projections (q, k, v, o, gate, up, down).
  + Thống kê tham số: 40.370.176 tham số LoRA có thể huấn luyện (0,919%), giảm 99,08% so với full fine-tuning.
  + Diễn biến học tập: bảng chi tiết 13 mốc evaluation (mỗi 100 steps). Train loss giảm từ 2,117 xuống 0,1015;
    Validation loss giảm từ 0,4077 và đạt điểm cực tiểu 0,24649 tại step 1.100 (Epoch 2.93, perplexity 1.2795).
  + Cơ chế Early Stopping: kích hoạt tại step 1.300 do validation loss tăng lên 0,2585 (step 1200) và 0,2541 (step 1300),
    patience=2, generalization gap 0,1450. Tự động phục hồi trọng số checkpoint-1100 thành best_adapter.
  + Hiệu năng tài nguyên: VRAM đỉnh 12,86 GB / 16 GB RTX 5060 Ti; throughput 1,127 samples/s; tổng thời gian ~3h41m.
  + Nêu rõ hiện tại chưa chạy inference evaluation trên 1.000 ca test độc lập (`test_sft.jsonl`) và sẽ bổ sung sau.
- Cập nhật liên kết tài liệu trong `docs/README.md`.
- Kiểm chứng: số liệu và đường dẫn đối chiếu khớp 100% với `config.yaml`, `parameter_report.json`,
  `training_metrics.json`, `timing_report.json` và `training_log.csv`. Không có lỗi chính tả hay link hỏng.

## TASK-20261007-08 — tài liệu hóa so sánh RAG và Base trên tthc_test_case_v1

- Tạo tài liệu báo cáo `docs/bao-cao-danh-gia-rag-vs-base-tthc-v1.md` tổng hợp và
  phân tích toàn diện kết quả 1.000 ca benchmark giữa RAG (`predictions_c4_full.jsonl`,
  `scores_c4_full.json`) và Base (`predictions_qwen_baseline_schema_c4.jsonl`,
  `scores_qwen_baseline_schema_c4.json`).
- Báo cáo phân tích chi tiết hiệu năng thông lượng, so sánh chỉ số tương đồng văn
  bản (Corpus BLEU 23.91 vs 8.27, Sentence BLEU 31.15 vs 15.41, ROUGE-L 0.5069 vs
  0.3188, BERTScore 0.9041 vs 0.8816, Action Acc 66.63% vs 46.70%), phân tích
  khả năng dập tắt ảo giác ở nhóm `abstain` (61.5% vs 12.3%), phân tích điểm yếu
  tiếng Việt không dấu (`no_diacritics`) và nghịch lý gán nhãn ở nhóm `correct_premise`.
- Cập nhật liên kết tài liệu trong `docs/README.md`.
- Kiểm chứng: file Markdown tạo đúng quy chuẩn, đường dẫn tương đối và số liệu
  khớp 100% với các file artifact kết quả trong `outputs/tthc_test_case_v1/`.

## TASK-20261006-03 — áp dụng đa dạng hóa câu hỏi

- Thêm `Data/qa_test_v4/rag_tthc_three_1500/diversify_questions.py` và áp dụng
  cho các nhóm mẫu chuẩn hóa có ít nhất 10 case. Script chỉ viết lại bề mặt câu hỏi,
  bỏ qua augmentation typo/no-diacritics và khóa `--apply` theo hash input v1.
- Cập nhật 3.772 câu; đồng bộ `runner_queries.jsonl` và 1.684 user-message trong
  history multi. Assistant-message, Gold, required facts và evidence không nằm
  trong phép gán của script.
- Vòng đầu phát sinh 821 câu single trùng do tổ hợp biến thể quay vòng; đã sửa
  bằng tiền tố hỏi trung tính, kiểm tra cuối còn 0 trùng. Số mẫu tăng 258 → 1.997,
  nhóm lớn nhất giảm 357 → 27. Chỉnh thêm văn phong cho 134 câu sinh tự động còn gượng.
- Nâng manifest thành `4.1-three1500-v2-diverse`; cập nhật validation, README,
  checksum và các báo cáo/CSV trong `outputs/testset_review/`.
- Kiểm chứng: đủ 4.500 ID và 1.500 ID/view; 381 chuỗi multi liên tục, user-history
  khớp; query export khớp case; tất cả checksum đạt; `test_evaluation.py` đạt 3/3,
  `test_resume.py` đạt. Không chạy RAG.
- Giới hạn kiểm chứng: `cases.jsonl` không có trong Git và không còn snapshot cùng
  hash cũ sau khi ghi, nên không thể diff độc lập mọi trường với bản v1. Báo cáo
  nêu rõ giới hạn và không tuyên bố benchmark cũ là kết quả của v2-diverse.

## TASK-20261006-02 — rà soát mẫu câu và Gold cần duyệt

- Tạo `outputs/testset_review/build_review.py` để tính lại offline từ `cases.jsonl`
  và dùng artifact verification/judgment hiện có làm tín hiệu triage.
- Tạo `bao-cao-ra-soat-testset.md`, `mau-cau-can-da-dang-hoa.csv` và
  `gold-can-duyet.csv`. CSV mẫu câu có bộ, nhãn, số lượng/mẫu số, tỷ lệ, ID/câu ví dụ,
  gợi ý và ví dụ viết lại cho từng mẫu.
- Quy tắc mẫu: thay nội dung trong ngoặc kép bằng `<THU_TUC>`, thay số độc lập/chuỗi
  số bằng `<SO>`, chuẩn hóa khoảng trắng rồi nhóm theo bộ và `expected_action`.
- Hàng đợi Gold chỉ chọn tín hiệu có khả năng hành động: xung đột được judgment nêu,
  source literal chưa `passed`, cờ section completeness, hoặc bất thường cấu trúc
  reference/facts/evidence. Trạng thái pending phổ quát không tự động đưa case vào hàng đợi.
- Kết quả: 4.500 case, 258 mẫu theo bộ/nhãn, 78 mẫu có ít nhất 10 case; hàng đợi
  1.318 ca (P0=1, P1=1.074, P2=243). Không có thay đổi dataset hay Gold.
- Kiểm chứng: script chạy exit 0; tổng count mẫu 4.500; ID review duy nhất và thuộc
  dataset; hash dataset `6ef2458020f12378ab86906a1e793c828d553687b2ecdeb8ed5a748931dbd02f`.
- Lỗi thực tế: lần chạy đầu lỗi cú pháp khi ghép f-string báo cáo; đã tách chuỗi tổng
  hợp ra biến và chạy lại thành công. ACL sandbox với `outputs/` yêu cầu thao tác trực tiếp.

## TASK-20261004-02 - Rà soát bộ ba tập 1.500

- Xác nhận dataset cục bộ là `Data/qa_test_v4/rag_tthc_three_1500`, gồm
  4.500 case test và ba view `views_single_1500.json`,
  `views_multi_1500.json`, `views_coverage_1500.json`, mỗi view 1.500 ID.
- Dùng trực tiếp loader/selector hiện hành để kiểm tra: cả ba view đều
  chọn đúng 1.500 query/case theo cùng thứ tự; chuỗi multi qua
  `validate_sequence` thành công.
- Kết luận: pipeline/adapter/scorer không bắt buộc sửa nếu CLI truyền
  `--dataset`, `--view`, `--split test` tường minh. Mặc định hiện tại không
  phù hợp vì dataset này không có `views_balanced.json`.
- Nếu chuyển notebook Colab chính thức thì cần đổi `DATASET_DIR`, danh sách
  `VIEW`, tên output và tài liệu. Nếu chạy nhiều phiên, cần tích hợp
  resume hoặc dùng `run_resume.py` kèm dataset qua endpoint; runner `qa-v4 run`
  hiện tại từ chối output đã tồn tại.
- Không thay đổi mã nguồn runtime trong task rà soát này; chưa chạy model
  thật hay chấm 4.500 lượt.
- Bổ sung triển khai theo yêu cầu sau rà soát: CLI nhận alias
  `rag_tthc_three_1500`/`test_rag_three_1500` và tự chọn
  `views_single_1500.json` khi phù hợp. Notebook Colab chuyển dataset mặc định,
  dropdown ba view, mode mặc định `reference_history` và tên output smoke mới.
- Tài liệu QA nêu rõ mode cho từng view; notebook đã sinh lại từ source.
  Không tích hợp resume; runner vẫn yêu cầu output mới cho mỗi lượt.
- Kiểm chứng: 13 test `tests.test_qa_v4` và `tests.test_colab_runtime` đạt;
  Ruff đạt; notebook JSON có đủ dataset, ba view và run name mới;
  `git diff --check` đạt (chỉ cảnh báo LF/CRLF).
- Commit đề xuất: `feat: switch Colab QA evaluation to three 1500 sets`.


## TASK-20261004-01 — Đánh giá ZIP thứ hai và sửa generation

- Theo điều chỉnh của người dùng, chỉ xét ZIP `_rag_2`: 23 lượt, 12 thành công,
  4 lỗi hợp đồng evidence/action và 7 lượt bị chặn sau lỗi gốc. Đối chiếu 23 câu
  với dataset cục bộ khớp; action đúng 4/23, không đồng nghĩa đúng nội dung.
- Phân tích chi tiết và giới hạn: `docs/project/colab-rag-2-assessment.md`.
- Thay đổi: routing.py thêm answer_schema và StructuredAnswerError; pipeline.py
  dùng schema generation, retry một lần trong ngân sách context, giữ lỗi thực
  và diagnostics; giữ câu hỏi gốc khi follow-up. Provider bọc schema answer
  riêng; adapter giữ diagnostics; runner ghi error_kind/blocked_by_id.
- Prompt bổ sung giới hạn trạng thái cá nhân, câu hỏi nhiều ý, tiền đề sai và
  nhiều thủ tục mơ hồ. Không đổi dataset hoặc ánh xạ nhãn theo đáp án chuẩn.
- Pipeline version 5, cập nhật migration và README QA v4. Không sửa artifact gốc.
- Kiểm chứng: `env/Scripts/python.exe -m unittest tests.test_conversation_routing
  tests.test_qa_v4 tests.test_routing_providers tests.test_rag_pipeline
  tests.test_server tests.test_rag_config_cli`: 54 test đạt. Sau bổ sung test
  retry context: chạy lại ba module đầu, 34 test đạt. Ruff đạt.
- Kiểm tra cuối: giữ lỗi các lượt reference_history độc lập; thêm hồi quy và
  chạy lại 10 test QA v4 đạt. Ruff và git diff --check đều đạt.
- Giới hạn: model Qwen thật/Colab chưa chạy lại; Ollama local từ chối kết nối.
  Prompt chỉ là thay đổi cần xác nhận thực nghiệm; retrieval thiếu mục căn cứ
  pháp lý chưa được điều chỉnh do chưa kiểm chứng lại corpus/index của Colab.
- Trạng thái partial: hoàn tất đánh giá và sửa kỹ thuật, còn kiểm chứng chất
  lượng model thật. Tiếp theo dùng RUN_NAME mới và LIMIT=23 hoặc 30 trên Colab.

## TASK-20261003-09 — ETA cho toàn bộ lượt chạy QA RAG

- Hành vi: sau mỗi câu, runner tuần tự ước lượng thời gian còn lại bằng thời gian
  tường trung bình của các câu đã hoàn tất nhân số câu còn lại; hiển thị cả thời
  lượng và giờ hoàn thành dự kiến. Tập tổng là danh sách sau view/split/limit.
- Báo cáo: `.run.json` bổ sung `started_at`, `completed_at` và `eta_method`;
  không thay đổi schema từng prediction hoặc cách chấm điểm.
- File: `src/vigovbot/qa_v4/runner.py`, `tests/test_qa_v4.py`, README QA v4 và
  hồ sơ project.
- Quyết định: dùng toàn bộ wall time quan sát trong runner để phản ánh cả lỗi và
  các bước xử lý mỗi câu; ETA chỉ xuất hiện sau câu đầu và sẽ ổn định dần.
- Kiểm chứng: `env\Scripts\python.exe -m unittest tests.test_qa_v4` đạt 8 test;
  Ruff đạt; `git diff --check` giới hạn các file task đạt.
- Chưa kiểm chứng: chưa chạy toàn bộ corpus/model thật vì không cần cho phép tính
  và sẽ tiêu tốn đáng kể thời gian; độ chính xác ETA phụ thuộc độ biến thiên từng câu.
- Bổ sung Colab: nguồn sinh và `ipynb/base_rag/lqwen2_5_7B_rag.ipynb` thông báo
  ETA từng câu, quản lý `predictions.jsonl.run.json` như một output của lượt chạy
  và in tổng thời gian/mốc hoàn tất; README Colab mô tả cách đọc kết quả.
- Kiểm chứng bổ sung: tái sinh notebook thành công; 3 test `test_colab_runtime`
  và Ruff cho script sinh notebook đạt; nội dung ETA/report có trong artifact.

## TASK-20261003-08 - 2026-10-03

- Đồng bộ README dự án, kiến trúc và roadmap: hệ thống hiện có CLI, Colab và web
  UI/API; hỗ trợ RAG nhiều lượt, Qwen base so với Qwen + RAG, routing schema,
  retry/fallback và diagnostics. Nêu đúng giới hạn persistence, auth/TLS và judge.
- Cập nhật trạng thái corpus thực tế: `Data/vector/unified/` có đủ index, metadata
  và manifest; cấu hình mặc định có thể xác minh corpus. Giữ hướng dẫn legacy cho
  corpus cũ khác không có manifest.
- Cập nhật hướng dẫn triển khai về Retriever read-only/khóa nội bộ khi phục vụ
  thread HTTP; sửa ID trùng trong sơ đồ Mermaid.
- Cập nhật README module RAG: kiến trúc router/retrieval/evidence, đủ bảy nhóm cấu
  hình, lệnh `web`, trường output routing và vòng đời tài nguyên đa luồng.
- Sửa mục lục docs trỏ tới `verification.md` không tồn tại, thay bằng lịch sử
  triển khai có kết quả kiểm chứng thực tế.
- Kiểm chứng: quét 45 liên kết tương đối trong sáu tài liệu, tất cả đích tồn tại;
  tìm mô tả cũ về web/một lượt/manifest; `git diff --check` thành công. Không chạy
  test ứng dụng hoặc model vì task chỉ sửa Markdown.
- Commit đề xuất: `docs: synchronize RAG deployment and architecture`.

## TASK-20261003-07 - 2026-10-03

- `rag/routing.py`: thêm schema anyOf theo nhánh, bỏ follow_up nếu không có
  history; prompt có ví dụ câu hỏi độc lập/chuyển chủ đề/hỏi tiếp/mơ hồ;
  validator vẫn kiểm tra JSON, không tự sửa nhãn. Out-of-scope không có query
  hoặc clarification. `rag/pipeline.py` dùng schema ở cả initial/retry,
  retry có lỗi cụ thể và rejected_json (tối đa 2.000 ký tự) trong dữ liệu user.
- Hai JSON sai giữ nguyên câu mặc định, thêm decision_reason routing_fallback,
  fallback_reason và routing_attempts, không truy hồi. Budget vẫn kiểm tra và
  lỗi HTTP vẫn báo riêng. Pipeline version tăng 3 → 4, cập nhật migration.
- `server/providers.py`: Ollama truyền schema qua adapter có sẵn; provider
  OpenAI-compatible gửi strict json_schema root object bọc route, tháo wrapper
  cho validator và giữ raw gốc; không downgrade nếu API không hỗ trợ.
- `server/app.py` trả routing_diagnostics; raw_routing chỉ khi web.debug_routing
  bật (mặc định false). UI phân biệt fallback và mơ hồ thật, hiển thị debug JSON.
  History giữ câu hỏi user và thay câu fallback bằng thông báo trung tính rằng
  lượt chưa được giải đáp, vẫn đúng hợp đồng cặp user/assistant.
- Kiểm chứng: `env\Scripts\python -m unittest tests.test_conversation_routing
  tests.test_routing_providers tests.test_server tests.test_web_ui
  tests.test_rag_config_cli tests.test_rag_pipeline -v`: 42 test đạt, gồm
  truyền schema HTTP, retry/fallback, chẩn đoán API và helper/syntax JavaScript.
  Sau tăng version, test smoke/evaluate/resume/report được chạy lại và đạt.
- Ruff check trên các file Python đổi/thêm và security check trên các module
  routing/server đổi đều đạt; `env\Scripts\python -m pip check` không có lỗi.
  `git diff --check` thành công (chỉ cảnh báo chuyển LF/CRLF của Git).
- Smoke: `env\Scripts\python scripts\smoke_routing_live.py oil` (2 ca) và
  `... basic` (4 ca), Qwen qwen2.5:7b thật, tất cả đúng nhãn/hợp lệ ngay lần đầu,
  fallback null. Artifact outputs/qa_v4/routing_implemented_{oil,basic}.json
  lưu cấu hình, model digest, tokenizer revision, pipeline version và source hash.
- Một lượt smoke đầu gặp Ollama HTTP 500, kiểm tra schema riêng và chạy lại
  thành công; nguyên nhân chưa xác định, ghi ERR-20261003-09.
- Giới hạn: smoke chỉ router với retriever rỗng, không suy ra đáp án corpus;
  provider ngoài chỉ kiểm chứng mock; chưa restart server của người dùng.
- Tài liệu: README, rag-multi-turn, hướng dẫn triển khai, migration và báo cáo
  điều tra trước sửa được cập nhật; không đổi corpus/embedding.

## TASK-20261003-06 - 2026-10-03

- Kiểm tra UI/backend/provider: history riêng theo model được truyền vào router;
  API bỏ chẩn đoán routing, UI đưa cả fallback vào history và reset khi reload.
- Thêm script probe routing, chạy Qwen thật hai kịch bản với đúng câu hỏi trong
  ảnh. Không history: retry sửa thành công; history giả chủ đề hộ chiếu: JSON
  cả hai lần có follow_up và clarification không rỗng, tái hiện fallback.
- Thử schema anyOf ràng buộc theo nhánh: hai kịch bản hợp lệ ngay lần đầu;
  kịch bản có history vẫn chọn follow_up nên chưa giải quyết phân loại ngữ nghĩa.
- Lệnh: `env\Scripts\python scripts\probe_oil_spill_routing.py` và thêm
  `--with-history`, cả hai exit 0. Artifact ở outputs/qa_v4/oil_spill_routing_probe*.json.
- Chỉ thử router với retriever rỗng, không tải encoder hoặc xác minh đáp án corpus;
  không có history gốc của ảnh. Chưa thay đổi code production.
- Đề xuất và giới hạn: docs/project/routing-fallback-investigation.md.
- Lỗi Qwen thực tế cập nhật ERR-20261003-08.

## TASK-20261003-05 - 2026-10-03

- Kiểm tra `outputs/qa_v4/local_smoke.jsonl`: 10 dòng, 9 có raw routing,
  4 lượt retry, 3 lượt fallback tại dòng 8–10; dòng 7 retry sửa thành công.
- Qwen `qwen2.5:7b` trả JSON hợp lệ về cú pháp nhưng chọn `follow_up` đồng thời
  điền cả query và clarification. Validator yêu cầu clarification rỗng ở nhánh
  truy hồi. Ba lượt fallback đều lặp lỗi ở lần retry, có marker
  `invalid_routing_after_retry`; không truy hồi hay sinh đáp án sau routing.
- Thêm `scripts/verify_routing_artifact.py` để kiểm tra artifact bằng validator
  hiện hành; dùng history giả không rỗng chỉ để cô lập lỗi schema, không khẳng
  định tái dựng lịch sử gốc. Lỗi lịch sử gốc được đọc từ initial_error đã lưu.
- Lệnh kiểm chứng: `env\Scripts\python scripts\verify_routing_artifact.py
  outputs\qa_v4\local_smoke.jsonl` thành công sau sửa encoding stdout UTF-8.
- Không gọi model mới: bằng chứng là raw response Qwen thật đã lưu ngày 2026-10-03;
  tỷ lệ 3/10 chỉ mô tả artifact này, không đại diện benchmark tổng thể.
- Lỗi thực tế: ERR-20261003-06 và ERR-20261003-07.

## TASK-20261003-04 - 2026-10-03

- Sửa `Retriever` để kết nối SQLite read-only dùng được từ thread HTTP khác thread
  khởi tạo bằng `check_same_thread=False`.
- Thêm khóa nội bộ bảo vệ toàn bộ `search()` và `close()`, qua đó tuần tự hóa
  encoder, FAISS và SQLite ngay cả khi Retriever được dùng ngoài web server.
- Thêm test hồi quy tạo Retriever ở main thread và gọi truy hồi từ worker thread;
  test xác nhận trả đúng chunk thay vì lỗi affinity SQLite.
- Cập nhật tài liệu module retrieval về hợp đồng đa luồng.
- Kiểm chứng: `env\Scripts\python -m unittest tests.test_server
  tests.test_rag_config_cli tests.test_rag_pipeline -v` chạy 20 test, tất cả đạt;
  `git diff --check` thành công. Chưa chạy lại web với Ollama thật.
- Lỗi và nguyên nhân được ghi tại `ERR-20261003-05`.
- Commit đề xuất: `fix: allow web RAG retrieval across request threads`.

## TASK-20261003-03 - 2026-10-03

- Thêm `web.models[].mode` nhận `base` hoặc `rag`, mặc định `rag` để giữ tương
  thích cấu hình cũ. Mode không hợp lệ bị Pydantic từ chối.
- `ChatApplication` cho nhánh base gửi lịch sử và câu hỏi thẳng tới provider,
  không gọi `answer_question`, retriever hay prompt RAG; nhánh RAG giữ nguyên
  router, FAISS/SQLite, xét bằng chứng và nguồn. API công khai trả thêm `mode`.
- `configs/inference.yaml` nay có hai lựa chọn cùng dùng `qwen2.5:7b`:
  `qwen-base` và `qwen-rag`. UI chọn sẵn cả hai và ghi rõ có/không truy hồi để
  hiển thị hai câu trả lời cạnh nhau.
- Cập nhật README và hướng dẫn triển khai, làm rõ "base" là cùng model instruction
  gọi trực tiếp, không phải một checkpoint base khác.
- Kiểm chứng: `env\Scripts\python -m unittest tests.test_server
  tests.test_rag_config_cli tests.test_rag_pipeline -v` chạy 19 test, tất cả đạt;
  tải cấu hình xác nhận hai tuple `qwen-base/base` và `qwen-rag/rag`;
  `py_compile` và `git diff --check` thành công. Chưa gọi Ollama/model thật.
- Lỗi chọn nhầm Python hệ thống trước khi dùng `env` được ghi tại
  `ERR-20261003-04`.
- Commit đề xuất: `feat: compare base Qwen and RAG responses in web UI`.

## TASK-20261003-02 - 2026-10-03

- Cập nhật `docs/trien-khai-rag-co-ban.md` từ mô hình một lượt cũ sang luồng RAG
  hiện hành: router phân loại phạm vi/quan hệ, viết lại câu hỏi nối tiếp, truy hồi
  dense, xét bằng chứng có cấu trúc và các nhánh answer/partial/clarify/abstain.
- Bổ sung cách truyền history cho CLI, các trường response mới, cấu hình
  `conversation.routing_enabled`, web server/API cục bộ và so sánh provider
  Ollama/OpenAI-compatible. Nêu rõ history nằm ở client và giới hạn production.
- Sửa tham chiếu lỗi đến `verification.md` không tồn tại; kiểm tra 16 liên kết
  tương đối trong tài liệu và tất cả đích đều tồn tại.
- Kiểm chứng: `git diff --check` thành công. Lệnh unit test RAG dừng ở import vì
  Python hiện tại thiếu `faiss`; không cài dependency cho task tài liệu và đã ghi
  `ERR-20261003-03`. Không chạy model, corpus hoặc web server thật.
- Commit đề xuất: `docs: align RAG deployment guide with current pipeline`.

## TASK-20261003-01 - 2026-10-03

- Bổ sung skill ghi hồ sơ task và skill chờ lệnh dài, áp dụng qua AGENTS.md.
- Hồ sơ lưu trong repository để các phiên sau tiếp tục và review được bằng Git.
- Quy tắc chờ ưu tiên completion event; fallback chờ session tối đa 60 giây,
  không tail log liên tục. Server dùng readiness thay vì chờ exit.
- Kiểm chứng: chạy quick_validate.py cho cả hai skill, đều trả `Skill is valid!`;
  `git diff --check` thành công. Đã kiểm tra đường dẫn dẫn chiếu trong AGENTS.md
  và docs/README.md. Không thay đổi code ứng dụng, không chạy pipeline/model.
- Validator ban đầu thiếu PyYAML; cài dependency vào thư mục tạm riêng rồi chạy
  với PYTHONPATH và PYTHONUTF8 trong process kiểm chứng, không sửa dependency dự án.
- Giới hạn: chưa thử hành vi skill trên task pipeline dài thực tế; completion
  notification tùy công cụ, skill không tự tạo cơ chế đánh thức agent.
- Commit đề xuất: `docs: add ViGovBot task journals and long-command skills`.

## TASK-20261004-03 — Báo cáo single_1500

- Ngày: 2026-10-04. Phân tích offline artifact three1500_single_smoke_rag_1.
- Tạo outputs/result_qa/bao-cao-single-1500.md: completeness, ma trận nhãn, lexical, routing, mẫu lỗi, latency và đề xuất ưu tiên.
- Kết quả: 1.500 ID duy nhất, 1 lỗi JSON, 459 đúng nhãn; 277/278 ca correct_premise kết thúc trước evidence_assessment. Phân biệt nhãn với ngữ nghĩa, nêu mapping/citations và semantic judgments còn thiếu.
- Kiểm chứng: Python stdlib đọc JSON/CSV, assert ID khớp view và tổng accuracy; đối chiếu 1.500 câu hỏi/nhãn/reference/field; liên kết báo cáo và UTF-8 hợp lệ. Không chạy lại model hoặc toàn bộ lexical scorer.
- Giữ nguyên artifact đầu vào và các thay đổi mã/notebook có sẵn.

## TASK-20261004-04 — Chấm bổ sung

- Ngày: 2026-10-04. Đã chấm BERTScore đủ 944 ca bằng xlm-roberta-large CPU, batch 1, không IDF/rescale; F1 0,891086, 5 reference bị cắt ở 512 token. Script 932,48 giây, session 59548 exit 0.
- Lệnh: env/Scripts/python.exe -u outputs/result_qa/supplemental_single_1500/score_bertscore.py. Script lưu checkpoint theo ca, cấu hình/hash input và summary. Không chạy lại Qwen.
- Đã lưu provenance, điểm từng ca, summary, mapping audit và README; cập nhật mục 9 báo cáo chính.
- Kiểm chứng Python: đủ 944 ID khớp tập cần chấm, tất cả điểm hữu hạn, trung bình tính lại khớp, toàn bộ SHA-256 artifact gốc không đổi; kiểm tra Markdown links và diff-check.
- Mapping audit chỉ có 1.461/3.313 chunk khớp nguyên nội dung unit cùng mã thủ tục; 1.852 chưa xác định. Chưa đủ mapping đã duyệt để chấm retrieval; trạng thái partial. Không coi BERTScore cao là tỷ lệ đúng kiến thức.

## TASK-20261005-01

- Phân tích offline multi/cover, tạo outputs/result_qa/bao-cao-multi-cover.md và kiem-chung-multi-cover.json.
- Kiểm chứng ID duy nhất, view, câu hỏi/nhãn/reference và tính lại action accuracy; liên kết báo cáo hợp lệ. Multi: 1.500 ca, 381 hội thoại; cover: 1.113 dòng CSV/predictions so với 1.500 per_case. Không ghi đè artifact.
- Chưa có BERTScore/retrieval/semantic judgments trong hai run; không chạy lại model.


## TASK-20261005-02 — Chấm bổ sung multi/cover (partial)

- Hoàn tất session 63478 exit 0: BERTScore xlm-roberta-large L17 CPU batch 1 no-IDF/no-rescale; multi 1.143 cặp F1=0,8949523699, cover 1.112 cặp F1=0,9031523112. Multi 1 cặp/cover 12 cặp quá giới hạn 512 token. Không chạy lại RAG.
- Mapping candidates session 63968 exit 0: 3.453 chunk multi, 4.496 chunk cover; không tự duyệt mapping. Document Recall@5/MRR@5 trên hạng chunk gốc: 0,852890/0,826416 (multi n=1.142), 0,956757/0,935736 (cover n=1.110). Tách ca thiếu nguồn/không rõ retrieval/chưa chạy.
- Duyệt nội dung AI 360 ca multi (357 personal-status abstentions đầy đủ theo 5 dạng answer đã đọc + 3 ca nội dung) và 3 ca cover (1 chờ phân xử Gold). Evidence-unit retrieval 6 ca có chủ đích. Không công bố pooled sample mean thành độ đúng toàn tập; không gọi AI review là human gold.
- Tạo outputs/result_qa/score_supplemental_review.py, finalize_supplemental.py, bao-cao-bo-sung-multi-cover.md, kiem-chung-bo-sung-multi-cover.json và artifact mỗi bộ trong supplemental/. Báo cáo cũ có liên kết cập nhật.
- Kiểm chứng: finalize_supplemental.py exit 0; ID BERT đúng tập đủ điều kiện, không trùng, điểm hữu hạn, mean/truncation tính lại khớp; retrieval mẫu số đủ 1.500 trạng thái và hạng mẫu khớp đối chiếu; judgment hash validator đạt; toàn bộ SHA-256 artifact gốc không đổi.
- Còn thiếu: duyệt mapping bằng chứng toàn tập, phân xử Gold, duyệt nội dung các ca còn lại và bổ sung 387 prediction cover nếu muốn đánh giá đủ 1.500. Không đánh dấu completed cho các chỉ số chưa có.

## TASK-20261006-01 - Hợp nhất và dọn `outputs/result_qa` (completed)

- Tạo `outputs/result_qa/tong-hop-danh-gia.md` làm báo cáo chính duy nhất: cấu hình chạy, 7 nhóm nội dung đánh giá, bảng kết quả 3 bộ, ma trận nhầm lẫn single, bảng theo lượt multi, lưu ý diễn giải, việc còn lại, danh sách file giữ.
- Bổ sung số liệu tự tính: single Document Recall@5/MRR@5 trên 615 ca có truy hồi ≈ 0,885/0,867 (328/943 ca dừng ở routing bị tính 0 trong điểm 0,577/0,565).
- Xóa theo lựa chọn người dùng: `bao-cao-single-1500.md`, `bao-cao-multi-cover.md`, `bao-cao-bo-sung-multi-cover.md`, `supplemental_single_1500/README.md`, `source_review/` v1, `pdf_text_cache.json`/`review_packets*`/`generation_review_packets.jsonl`/`mapping_candidates.json`, `visual_review/`, `review_multi_cover/`, mọi `*.log` và `*.py` trong thư mục. Giữ dữ liệu gốc run, kiểm chứng, judgments, BERTScore.
- Kiểm chứng: 101 → 54 file, 93,2 → 45,2 MB; mọi liên kết tương đối trong báo cáo chính tồn tại. Thư mục bị gitignore nên không khôi phục qua git; tái lập chấm bổ sung cần script mới.

## TASK-20261007-01 — Thiết lập môi trường đánh giá RAG (completed)

- Cài Python 3.14.7 và Ollama 0.35.1 bằng winget; tạo `.venv`, cài
  `locks/rag-windows-py314.txt`, package editable và bổ sung SacreBLEU 2.6.0 do
  lockfile thiếu dependency đã khai báo trong extra evaluation.
- Tải `qwen2.5:7b` 4,7 GB; xác minh Ollama API. Cache BAAI/bge-m3 và tokenizer
  Qwen qua một smoke RAG thật. Giữ encoder trên CPU theo `configs/rag.yaml`; Qwen
  chạy qua Ollama trên máy có RTX 5060 Ti 16 GB.
- Dùng corpus có sẵn `Data/vector/unified` (117.871 vector/chunk), tạo SQLite cache
  và không chạy embedding lại. Dataset không bị sửa.
- Smoke single_0001 exit 0, có 5 chunk truy hồi và đáp án hợp lệ; wall 45,25 giây,
  retrieval 0,337 giây. Score lexical coverage 1/1. Artifact ở
  `outputs/environment_smoke_20261007/`.
- Kiểm chứng: ba view single/multi/coverage đều 1.500 ca; multi sequence hợp lệ;
  test dataset evaluation 3/3 và resume đạt; 40 unit test QA v4/RAG/config/Colab
  đạt. Chưa chạy benchmark đủ 4.500 lượt.
- Lỗi lock thiếu SacreBLEU và cách xử lý được ghi tại ERR-20261007-01.

## TASK-20261007-02 — Khảo sát tăng tốc benchmark (completed)

- Đối chiếu runner, adapter, retriever, cấu hình và phần cứng máy hiện tại. Xác
  nhận runner tuần tự và mutex retriever bao trùm encoder + FAISS + SQLite.
- Xác nhận index là `IndexFlatIP` 117.871 vector 1.024 chiều, tải vào RAM; không có
  bằng chứng I/O đĩa là nút thắt. Telemetry smoke cho retrieval 0,337 giây, thấp
  hơn đáng kể routing/generation của lượt cold-start.
- Kết luận kiến trúc: song song theo query cho single/coverage và theo conversation
  cho free-running multi; writer phải giữ một luồng và output deterministic/resume-safe.
  Với GPU 16 GB, bắt đầu Ollama parallel 2, đo rồi mới tăng 4; giữ một loaded model.
- CUDA BGE/BERTScore khả thi sau khi thay Torch CPU bằng wheel CUDA và kiểm tra
  Blackwell; batch scoring nên tự giảm khi OOM. Không cam kết mốc dưới một phút
  trước benchmark thực tế.
- vLLM hiện yêu cầu Linux (Windows qua WSL2) và Python 3.10–3.13 theo tài liệu;
  không thay trực tiếp Ollama trong môi trường Windows/Python 3.14 hiện tại.
- Không sửa code/cấu hình/runtime; đây là kết quả khảo sát để chốt phase triển khai.

## TASK-20261007-03 — Tăng tốc đánh giá trên RTX 5060 Ti (completed)

- `qa_v4/runner.py`: thêm thread pool và `--concurrency`; single/coverage lập lịch
  theo query, free-running multi theo conversation. Lượt trong conversation tuần
  tự, lỗi chặn các lượt sau như cũ; writer buffer để giữ đúng thứ tự view. Run report
  ghi concurrency hiệu lực và đơn vị lập lịch.
- `retrieval/retriever.py`: thay mutex toàn search bằng khóa encoder và SQLite
  riêng; FAISS IndexFlatIP read-only không còn bị khóa cùng generation worker.
- Tạo `configs/rag-fast-local.yaml`: BGE-M3 CUDA, BERTScore CUDA batch 16; giữ
  `configs/rag.yaml` CPU để tương thích máy khác. Cập nhật README QA v4 với lệnh
  chạy ba view, cài CUDA wheel và giới hạn VRAM.
- Môi trường máy: Torch 2.14.0+cu130 nhận RTX 5060 Ti; BGE dùng khoảng 2.198 MB
  VRAM, sau warm-up đo 0,044 giây/query trên mẫu 6. Ollama đặt parallel=2,
  max-loaded=1, Flash Attention và KV q8_0; log xác nhận CUDA compute 12.0.
- Benchmark cùng bốn single: c1 36,758 giây, c2 16,625 giây, 4/4 thành công,
  throughput tăng 2,21 lần; ID/action khớp. Multi hai conversation: 8/8 thành công,
  32,845 giây. Artifact: `outputs/environment_speed_20261007/`.
- BERTScore CUDA phát hiện contract `return_hash` khác; sửa scorer hỗ trợ dạng
  4-tuple và nested 2-tuple, thêm test. Smoke cache nóng 3 cặp mất 0,82 giây,
  score coverage 4/4. Không ngoại suy thành thời gian toàn tập khi chưa chạy đủ.
- Kiểm chứng: 44 unit test đạt; Ruff, pip check, config load và diff-check đạt.
  Không chạy đủ 4.500 lượt và không triển khai vLLM/WSL2.

## TASK-20261007-04 — Tiến trình chấm điểm (completed)

- `qa_v4/scoring.py` thêm progress tùy chọn cho CLI: phase chuẩn bị, tqdm lexical
  theo case, mô tả BERTScore (số cặp/model/device/batch), thời gian BERT và tổng hợp.
- `qa_v4/__main__.py` bật progress cho lệnh score và in đường dẫn artifact khi ghi
  xong. Lời gọi thư viện/test giữ mặc định im lặng; metric và JSON schema không đổi.
- Kiểm chứng smoke 4 case hiển thị 0→100%, tổng hợp và completion path; 24 test
  QA v4/review, Ruff và diff-check đạt.
# TASK-20261007-05

- Cài Python 3.14.7, môi trường `.venv` theo lock RAG/evaluation, Torch
  2.14.0+cu130 và Ollama 0.40.0; tải Qwen 2.5 7B. CUDA nhận RTX 3090 24 GB,
  `pip check` đạt.
- Thêm `configs/rag-rtx3090.yaml` và cho CLI QA v4 đọc trực tiếp layout unified-v2
  `data/rag/{split}.jsonl`/`{split}_queries.jsonl`; không sao chép hoặc đưa gold
  vào inference. Thêm test layout; 14 test QA runner và Ruff đạt.
- Đặt Ollama parallel=4, max-loaded=1, Flash Attention và KV q8_0. Smoke cache
  nóng concurrency 4 đạt 8/8, wall 24,52 giây, không OOM.
- Full run được người dùng yêu cầu dừng sau khi file ghi 36 prediction; không có
  run report/score cuối. Bàn giao lệnh output mới để người dùng tự quan sát.
- Dataset có lỗi layout giữa validator/checksum và artifact; hash nội dung test
  theo ánh xạ thực tế vẫn khớp. Chi tiết ở ERR-20261007-03 và ERR-20261007-04.

# TASK-20261007-06

- Sửa evaluator unified-v2 để chặn cảnh báo SacreBLEU lặp theo từng câu trong khi
  giữ nguyên `effective_order=False` và công thức điểm.
- Bổ sung thông báo phase corpus BLEU/BERTScore, progress BERTScore và CLI
  `--bert-batch-size`; cập nhật checksum của evaluator.
- Kiểm chứng trên 1.000 prediction: py_compile và synthetic test đạt; lexical
  hoàn tất 3,70 giây, coverage 995/1.000, corpus BLEU-4 23,9057. Không tự chạy
  BERTScore toàn tập; người dùng sẽ chạy lệnh CUDA và quan sát progress.

# TASK-20261007-07

- Baseline Qwen không retrieval nay dùng `answer_schema(False)` thay vì chỉ
  `format=json`, buộc `answer` không rỗng và `action` thuộc năm nhãn hợp lệ.
- Thêm một retry khi parse/validation thất bại; lần hai thất bại ném
  `StructuredAnswerError` và runner giữ `generation_diagnostics` gồm số attempt,
  lỗi validation và output rút gọn. Không retry lỗi HTTP/hạ tầng.
- Thêm test schema, recovery và failure diagnostics; cập nhật README.
- Kiểm chứng: 37 test QA/routing, Ruff check/format và pip check đạt. Smoke Qwen
  thật concurrency 4 đạt 20/20 trong 21,08 giây; 20 case tương ứng ở run cũ có
  5 failure schema. Không ghi đè artifact baseline 1.000 ca cũ.

# TASK-20261014-01 - QLoRA local-first và portable GPU

- Thêm package `training` cho config merge/override, validation JSONL/leakage,
  official chat-template token stats, assistant-only masking, early stop/checkpoint,
  preflight, QLoRA train/resume, baseline-vs-adapter evaluation, metrics, plot/report
  và artifact run. Import GPU/model là lazy; local validator không tải model 7B.
- Thêm `configs/{base,local,smoke,gpu}.yaml`, requirements pin, `.env.example`,
  ignore model/data/artifact và hướng dẫn Linux GPU/transfer SHA-256.
- Chatbot giữ API cũ, bổ sung provider `local_transformers` nạp baseline hoặc
  PEFT adapter; mặc định chỉ cache một model và không merge quantized weights.
- Kiểm chứng thật local: validator official tokenizer offline đạt 5.000
  record; report tại `outputs/qlora/dataset_report.json` (Git-ignore). Mẫu masking
  thật có 150 token, 62 target và 88 `-100`.
- Test: 15 test QLoRA/server/plot liên quan đạt; Ruff và `git diff --check`
  đạt. Full suite: 124 đạt, 1 skipped, 1 failure không thuộc diff task
  (test cũ mong JSON mode thay vì JSON schema).
- Chưa kiểm chứng: CUDA/bitsandbytes, GPU smoke/full training, resume thật,
  baseline/fine-tuned evaluation, checkpoint/best adapter và plot/metric từ log thật.
  Preflight local xác nhận CUDA unavailable và không cho fallback CPU.

# TASK-20261014-02 - Audit pre-GPU QLoRA

- Audit source/config/test thực tế cho masking, NF4/PEFT, Trainer, resume,
  evaluation, metrics, accounting, plots, portability và chatbot; không nạp weights.
- Sửa assistant-only boundary theo generation prompt, supervise EOS và từ chối
  truncation; thêm official Qwen cache-only test cho multi-turn/header/EOS.
- Sửa resume tiếp tục run cũ, validate optimizer/scheduler/RNG/callback/
  global-step/config/hash, restore callback state và từ chối checkpoint incomplete.
- Sửa target-token loss/perplexity, corpus BLEU/chrF, comparable train-validation
  gap, base/LoRA parameter accounting, measured footprint/VRAM/time và plot marker.
- Sửa PEFT inference base-model compatibility; giữ single-model cache và API cũ.
- Xác nhận JSON schema là contract runtime hiện hành; chỉ cập nhật test
  cũ, không bỏ hỗ trợ JSON mode của provider.
- Kiểm chứng: 136 test passed, 1 optional skipped; Ruff, compileall,
  diff-check và validator 5.000 record official-tokenizer offline đều đạt.
- Báo cáo `docs/qlora-pre-gpu-audit.md`; trạng thái partial vì CUDA,
  bitsandbytes kernel, GPU smoke và resume thật chưa được chạy.

## TASK-20261014-03 - GPU smoke RTX 5060 Ti 16 GB (completed)

- Cài Python 3.11.9 user-scope, tạo `.venv-qlora`, cài PyTorch 2.9.1+cu130 và
  stack QLoRA pin của repo. Driver 616.92/CUDA runtime 13.0 nhận SM 12.0; wheel
  có `sm_120`; CUDA matmul và BF16 đạt; không cài CUDA Toolkit/WSL/driver.
- Thêm config full/smoke RTX 5060 Ti với path dataset thực tế, requirements
  Windows Blackwell, GPU diagnostic, resume verifier và acceptance gate JSON/MD.
- Dataset official tokenizer đạt 3.000/1.000/1.000, hash được lưu, max length
  1.619/1.513/1.539 dưới 2.048; assistant-only masking/EOS và split isolation
  được test bằng pipeline hiện có.
- bitsandbytes 0.49.0 chạy NF4, double quant, BF16 backward và PagedAdamW8bit
  kernel thật; optimizer state uint8. `pip check` đạt.
- Smoke Qwen2.5-7B thật 4 optimizer step: loss 1,9367→1,3523; eval loss tốt nhất
  2,574343; 40.370.176 LoRA parameter trainable, 4.352.972.288 frozen; checkpoint-2
  đủ adapter/optimizer/scheduler/RNG/trainer/callback. Peak sau resume allocated/
  reserved 11.678.638.080/12.450.791.424 byte; khoảng 9,797 giây/optimizer step.
- Resume checkpoint-2→4 giữ log/LR liên tục, optimizer step 2→4, scheduler/RNG/
  callback/best metric và adapter cuối khớp run không gián đoạn. Buffer uint8
  optimizer không byte-identical dù scale/outcome khớp; ghi giới hạn tại
  ERR-20261014-12 và acceptance report.
- Sửa callback hậu kiểm không làm EarlyStopping báo thiếu metric; sửa timing
  resume dùng số step thực thi trong invocation. Sinh 7 plot và summary report.
- Kiểm chứng cuối: acceptance 7/7 PASS; 136 test đạt, 2 optional skip; pip check,
  Ruff, compileall và git diff-check đạt. Kết luận `READY WITH LIMITATIONS`; chưa
  chạy full 5 epoch hoặc đánh giá chất lượng cuối theo đúng phạm vi.

## TASK-20261014-04 - Điều khiển QLoRA độc lập PowerShell (completed)

- Thêm `start_qlora.ps1`, `status_qlora.ps1`, `stop_qlora.ps1`,
  `start_tensorboard.ps1` và worker ẩn. Worker độc lập khỏi Codex/ChatGPT, lưu
  stdout/stderr/PID/exit code theo run + attempt; không ghi đè log resume.
- Start dùng `.venv-qlora` và config RTX 5060 Ti cố định, chạy validator CUDA/
  dataset/config/resume, tính 1.875 full optimizer step, chặn active/rogue
  `training.train`, tạo run ID duy nhất và không truyền override hyperparameter.
- Thêm Trainer callback ghi `live_status.json` và TensorBoard train/eval loss,
  learning rate, gradient norm, step, epoch, GPU allocated/reserved/peak memory.
  Stop request được nhận cuối optimizer step, yêu cầu save + training stop;
  script chỉ báo checkpoint mới sau khi kiểm directory có timestamp phù hợp.
- `create_run_dir` từ chối directory đã tồn tại. Resume validate immutable config,
  dataset SHA-256 và đầy đủ adapter/optimizer/scheduler/RNG/callback state.
- README `docs/qlora-operations.md` ghi lệnh start/status/TensorBoard/stop/resume/
  plot/report, exit code và OOM không auto-restart. HF cache giữ hành vi chuẩn,
  không ép tải lại model.
- Kiểm chứng không full train: năm PowerShell script AST parse đạt trên Windows
  PowerShell; start dry-run đạt GPU + 3.000/1.000/1.000 record + 1.875 step;
  TensorBoard dry-run đạt; unit mock live metrics/graceful stop và overwrite guard
  đạt. Full suite 138 test đạt, 2 optional skip; pip check, Ruff, compileall và
  diff-check đạt.

# TASK-20261014-05 — audit cuối logging/reporting QLoRA

- Thêm `training_events.jsonl` append-only và fsync ở từng log callback, chứa UTC,
  invocation, step/epoch, loss, LR, gradient norm và mẫu CUDA memory; bổ sung epoch,
  checkpoint và resume history để giữ dữ liệu đã đo khi run gián đoạn.
- Làm rõ trạng thái lỗi/interrupted/graceful stop và early stopping; lưu timing,
  throughput, peak memory và checkpoint metadata từ dữ liệu thực.
- Tách artifact evaluation theo split, thêm question/generated answer/metric mỗi mẫu,
  token-weighted loss/perplexity và absolute improvement; test generation vẫn chỉ
  chạy qua CLI hậu kỳ, không được gọi trong validation loop.
- Plot ưu tiên event JSONL, tạo manifest generated/unavailable; report xuất cả JSON
  và Markdown với bảng availability, không thay thế metric thiếu bằng số giả.
- Thêm `training.readiness` và `docs/qlora-experiment-readiness.md`. Readiness trên
  config RTX đạt READY mà không load model/start train.
- Kiểm chứng: `pytest -q` đạt 137 passed, 2 skipped, 40 subtests; compileall, Ruff và
  diff-check đạt. Không chạy full training hoặc tải model weights.

# TASK-20261014-06 — đối chiếu test QLoRA với QA-v4

- Kiểm tra bằng script chỉ đọc ba JSONL: 1.000 query, 1.000 gold case và 1.000 SFT
  test; tập ID bằng nhau và không có message mismatch.
- Xác nhận config snapshot của run đã trỏ tới `fintuning/test_sft.jsonl`, là biểu diễn
  hội thoại loss/evaluation của cùng `rag/test_queries.jsonl` và `rag/test.jsonl`.
- Không sửa pipeline, không tải model và không khởi chạy evaluation dài.

# TASK-20261014-07 — đánh giá QLoRA bằng QA-v4

- Thêm context manager `qlora_adapter`: đọc config snapshot/best adapter, chạy local
  Transformers 4-bit và dùng cùng system prompt, action schema parser, một lần retry
  như Qwen baseline; không đưa reference/evidence/action gold vào prompt.
- CLI `qa-v4 run` nhận `--qlora-run-dir`, từ chối concurrency khác 1 trên GPU đơn,
  ghi mode/adapter/config hash và giới hạn structured decoding vào provenance.
- Dùng nguyên QA-v4 scorer để xuất action/coverage, EM/token PRF, BLEU/chrF++/TER,
  ROUGE, BERTScore, latency và các breakdown. Retrieval metric vẫn unavailable cho
  QLoRA/base; semantic metric chỉ có khi cung cấp judgments.
- Tài liệu hóa run, score và paired bootstrap base-vs-QLoRA/RAG-vs-QLoRA trong
  `docs/qlora-operations.md`.
- Kiểm chứng: 138 passed, 2 skipped, 40 subtests; compileall và Ruff đạt. Không tải
  model hoặc chạy 1.000 generation.
- Điều chỉnh sau quan sát run thật: adapter SFT sinh plain answer đúng contract train,
  nên bỏ ép JSON/retry. Prediction giữ nội dung, đánh dấu action unavailable; scorer
  loại action metric thay vì tính sai bằng 0. Full suite sau sửa đạt 139 passed,
  2 skipped, 40 subtests.
- Thêm true batched generation với left padding, giữ thứ tự và batch telemetry;
  CLI có equivalence gate single-vs-batch trước khi tạo artifact. Smoke RTX thật:
  batch 2 đạt 4/4 trong 25,67 giây; batch 4 đạt 4/4 trong 17,85 giây (nhanh hơn
  khoảng 1,44 lần), output gate khớp tuyệt đối và không OOM.

# TASK-20261014-08 - đánh giá full run và vẽ loss (completed)

- Kiểm kê `outputs/qlora`: hai smoke run đã hoàn tất và một full run thực dừng
  sớm ở step 1.300/1.875, epoch 3,4667, do validation-loss patience.
- Full run giảm validation loss từ 0,407741 ở step 100 xuống mức tốt nhất
  0,246493 ở step 1.100; step 1.200/1.300 tăng thành 0,258451/0,254082 trong khi
  training loss tiếp tục giảm, nên có dấu hiệu overfit nhẹ sau step 1.100.
- Xác minh `best_adapter/adapter_model.safetensors` có SHA-256 trùng đúng
  checkpoint-1100 và khác checkpoint-1200/1300; best restore là artifact thật.
- Chạy `env/Scripts/python.exe -m training.plot --run_dir <full-run>` thành công,
  sinh 9 PNG và manifest; biểu đồ so sánh evaluation được ghi unavailable đúng
  vì chưa có post-training test evaluation. Kiểm tra trực quan combined loss đạt.
- Kiểm chứng: `tests.test_qlora_plot` đạt 1/1; `git diff --check` đạt. Không chạy
  lại training hoặc thay đổi checkpoint/model.
- Giới hạn: loss/perplexity chỉ chứng minh tối ưu hóa SFT; chưa có prediction và
  metric test/QA-v4 nên chưa chứng minh độ đúng nội dung hay cải thiện so với baseline.

# TASK-20261015-01 - đánh giá khả năng hoàn tất QLoRA evaluation (completed)

- Đối chiếu artifact `environment.json` của full run: RTX 5060 Ti 16 GB, CUDA
  13.0, BF16, bitsandbytes/NF4 và full training đã chạy thành công; đủ năng lực
  cho BERTScore CUDA batch 16 và controlled 4-bit inference tuần tự.
- Đọc implementation thực tế: `training.evaluate` nạp base 4-bit, chạy đủ test,
  giải phóng rồi mới nạp adapter 4-bit; không giữ đồng thời hai model. Tuy nhiên
  nó vừa teacher-forced loss vừa generate cho 1.000 mẫu mỗi model, tổng 2.000
  generation, nên là bước dài nhất và không tái sử dụng prediction QA-v4 hiện có.
- Lexical chạy CPU; BERTScore dùng xlm-roberta-large/CUDA; paired bootstrap và
  plot/report nhẹ. Khuyến nghị chạy tuần tự và đóng process model cũ trước BERTScore.
- Phiên kiểm tra trực tiếp hiện tại khác host tạo run: RTX 4050 Laptop 6 GB, không
  có `.venv-qlora` và không có prediction batch4, nên không chạy tiếp thay người
  dùng và không tuyên bố artifact score đã hoàn tất.
- Hiệu chỉnh sau xác nhận của người dùng: RTX 4050 Laptop 6 GB là máy cần chạy
  evaluation. Khuyến nghị BERTScore batch 4 thay vì 16; lexical/compare/plot/report
  vẫn nhẹ. Controlled HF evaluation là rủi ro OOM/offload chậm với 6 GB VRAM và
  khoảng 4,87 GiB RAM trống, nên phải smoke tách biệt trước; chưa được thực thi.
- Kiểm tra live package index: Python 3.14 có `torch 2.14.0+cu130` và
  `2.14.1+cu130`; chọn 2.14.0+cu130 để thay bản 2.14.0+cpu với ít drift nhất.
  GPU compute 8.9 và driver 617.42 phù hợp; chưa thực hiện cài đặt.
- Sau khi người dùng xác minh CUDA hoạt động, sửa `dataset_file` để chấp nhận cả
  `data/rag/{split}.jsonl` và layout thực tế `data/{split}.jsonl`. Thêm regression
  test layout phẳng; hai test resolver đạt và đường dẫn test/query thực tế được
  phân giải đúng. Chưa chạy BERTScore dài.

# TASK-20261015-03 - xác minh QLoRA tốt hơn Base và RAG

- Đối chiếu provenance cho thấy cả ba run dùng cùng SHA-256 query
  `f4e180b70af50fc69fd39f236ecc2f3e77a028de6e30dbe8d4991cc24b01d4f4` và
  cùng chế độ `reference_history`; Base/QLoRA đủ 1.000 ca, RAG thành công 995 ca.
- QLoRA được SFT trên 3.000 chuỗi `history + question + gold assistant answer`, chỉ
  cập nhật adapter 40.370.176 tham số; checkpoint chọn bằng validation loss ở step
  1.100. Base không train theo bộ này; RAG không train generator nhưng thêm top-5
  context từ BGE-M3/FAISS ở inference.
- Điểm QLoRA trên 810 ca có reference nội dung: EM 0,2630, sentence BLEU 61,3774,
  ROUGE-L F1 0,7169, BERTScore F1 0,9514. Điểm tương ứng của RAG là BLEU 31,1504,
  ROUGE-L 0,5069, BERTScore 0,9041; Base là 15,4110, 0,3188 và 0,8816.
- Dataset split theo case/episode, không cô lập nguồn: 564/1.000 ca test (56,4%)
  có document xuất hiện trong train; 571/1.000 có procedure family xuất hiện trong
  train. Trên 810 ca similarity, QLoRA đạt BLEU 64,82 và EM 30% cho 493 ca document
  đã gặp, so với BLEU 56,02 và EM 20% cho 317 ca chưa gặp.
- QLoRA vẫn cải thiện ở nguồn chưa gặp, nhưng source overlap làm điểm tổng lạc quan
  hơn đánh giá document-disjoint. Metric hiện chỉ chứng minh bám reference: QLoRA
  không có action/retrieval và `generation_judged_cases=0`, nên chưa chứng minh
  thắng RAG về factuality, faithfulness, cập nhật tri thức hay hành vi từ chối.
- Kiểm chứng chỉ đọc artifact/dataset và phân tầng score; không chạy generation,
  không tải model và không thay đổi checkpoint.

# TASK-20261015-04 - tích hợp QLoRA vào web demo

- Mở rộng `WebModelConfig.mode` thành `base|rag|qlora`; `qlora` bắt buộc dùng
  provider `local_transformers` và có `adapter_path`, tránh cấu hình hợp lệ bề
  ngoài nhưng chạy sai backend.
- Thêm `qwen-qlora` vào `configs/inference.yaml`, dùng
  `Qwen/Qwen2.5-7B-Instruct`, NF4 4-bit và `best_adapter` của full run; đường dẫn
  tương đối được resolver chuẩn hóa thành artifact hiện có trong repository.
- `ChatApplication` xử lý `qlora` như direct generation, không gọi retrieval;
  response công khai có `mode=qlora`, `sources=[]`, lịch sử tách riêng theo ID.
- UI hiển thị ba lựa chọn và mô tả QLoRA là adapter không truy hồi; cập nhật tiêu
  đề và hướng dẫn README.
- Thêm `release_local_transformers_models()` và chuyển backend tuần tự. Khi đổi
  Ollama → QLoRA, server gửi `keep_alive: 0`; khi đổi QLoRA → Ollama, server xóa
  cache model local, chạy GC và `torch.cuda.empty_cache()`. Dùng `RLock` để helper
  an toàn khi được gọi từ nhánh cache hiện có.
- Kiểm chứng: `unittest` 22/22 cho server, web UI, RAG config/CLI và QLoRA local;
  Ruff, compileall, diff-check đạt. Parse config xác nhận ba model và adapter path
  tuyệt đối đúng. Chưa chạy model thật hoặc browser QA, nên không coi là bằng
  chứng runtime GPU/visual; không tải hay sửa checkpoint.

# TASK-20261015-05 - sửa runtime QLoRA trên web

- Xác nhận web dùng `env\Scripts\python.exe`; lỗi đầu do thiếu `accelerate`. Audit
  dependency cho thấy thiếu cả `peft` và `bitsandbytes`, nên cài các bản dự án đã
  ghim: Accelerate 1.12.0, PEFT 0.18.0 và bitsandbytes 0.49.0.
- `pip check`, import và phép NF4 CUDA forward nhỏ đạt. Lần smoke đầu tải đủ bốn
  shard Qwen vào Hugging Face cache nhưng `device_map=auto` báo một số module phải
  rơi xuống CPU vì RTX 4050 chỉ có 6 GB.
- CPU offload không được giữ làm giải pháp: Transformers 5.17.0 không tương thích
  bitsandbytes 0.49.0 ở hook `_is_hf_initialized`; sau khi hạ về bản dự án ghim
  4.57.3, auto CPU dispatch vẫn lỗi thao tác `Tensor.item()` trên meta tensor.
- Loader bổ sung tùy chọn `force_single_gpu`; cấu hình web QLoRA dùng NF4 toàn bộ
  trên GPU đơn, không CPU offload. Các tùy chọn offload/memory vẫn explicit và
  mặc định tắt, không được tuyên bố đã kiểm chứng trên stack này.
- Smoke thật cuối PASS: đúng base Qwen2.5-7B + `best_adapter`, 8 token, generation
  7,96 giây, CUDA allocated 5,35 GiB. Không sửa checkpoint; weights base được cache.
- Cần restart web process cũ để bỏ module Transformers đã import trước khi hạ bản.

# TASK-20261015-06 - chẩn đoán QLoRA liên tục hỏi làm rõ

- Kiểm tra client/server xác nhận `histories[model_id]` được gửi qua `/api/chat`,
  validate và ghép trước câu hỏi hiện tại cho nhánh QLoRA; không phát hiện lỗi mất
  history trong luồng nguồn.
- Đối chiếu dữ liệu cho thấy mã người dùng nhập `1.004696` không tồn tại. Corpus
  chứa đúng tên thủ tục dưới mã `1.009646` với 33 chunk, nhưng không có case mang
  document/mã này trong train, validation hoặc test SFT.
- Các lượt chỉ xác định chủ đề/thủ tục, chưa hỏi thuộc tính cụ thể. Adapter được
  SFT theo cặp câu hỏi cụ thể → gold answer và chạy không retrieval, nên câu hỏi
  làm rõ là phù hợp hơn việc tự chọn một nội dung để trả lời.
- Không sửa prompt/model. Khuyến nghị dùng nhánh RAG cho tài liệu corpus chưa có
  trong SFT; nếu cần chất lượng văn phong QLoRA cùng tri thức mới, triển khai nhánh
  QLoRA + RAG riêng và đánh giá lại faithfulness.
- Lượt thử bổ sung với câu hỏi “Thủ tục mã 1.009646 gồm những giấy tờ nào trong
  trường hợp điều chỉnh chung?” chứng minh rủi ro thực tế: QLoRA trả một mục tổng
  quát không có trong nguồn. Chunk `tthc_1_009646_sec_other_4_p1` quy định ba mục:
  văn bản đề nghị điều chỉnh (Mẫu I.1.8, 1 bản chính), quyết định của nhà đầu tư
  đối với nhà đầu tư là tổ chức (1 bản sao), và giải trình/tài liệu liên quan theo
  khoản 1 Điều 31 nếu có (1 bản sao). Đánh giá câu QLoRA: sai nguồn và thiếu 2/3 mục.

# TASK-20261015-07 - refactor sạch và CLI thống nhất (lát cắt 1)

- Kiểm kê Git/tree/import/entry point/config/script/artifact và ghi baseline trước
  sửa: 145 test, 143 pass, 1 skip, 1 readiness fail do profile dataset cũ trỏ
  đến thư mục `fintuning` không có trên checkout hiện tại.
- Thay module đơn `src/vigovbot/cli.py` bằng package `src/vigovbot/cli/`; thêm
  Typer console script `vigov` với doctor, data, gpu, train, dashboard, eval và
  report. `vigovbot` và bốn command cũ vẫn dispatch đến implementation cũ.
- CLI lazy-import workload; `--config`/`--run-id` explicit; start/resume truyền
  đúng active interpreter và config xuống worker. Thêm logs gần nhất/follow và
  cho TensorBoard chọn run/port.
- Tách cấu hình canonical thành `configs/environments/` và `configs/experiments/`;
  YAML cũ trở thành alias qua `extends`. Sửa precedence để CLI `--set` thắng biến
  môi trường. Không thay thuật toán QLoRA hoặc tự đổi hyperparameter.
- Hợp nhất metadata/dependency group trong `pyproject.toml`; editable install
  thành công mà không nâng Torch/CUDA. Không xóa file/script cũ và không động đến
  Data/outputs/checkpoint/adapter.
- Kiểm chứng cuối lát cắt: full suite 150 pass, 1 optional skip; Ruff, compileall,
  pip check, diff-check, PowerShell AST và console `vigov --help` đều đạt.
- Chưa kiểm chứng GPU trong task này. Lifecycle Linux và migration vật lý package
  `training/` còn lại nên trạng thái task là partial, không tuyên bố refactor xong.

## Lát cắt 2 - package training, lifecycle và run layout

- Di chuyển implementation `training/*.py` vào `src/vigovbot/training/`; package
  cũ trong checkout và package `src/training` đã cài đều alias cùng module object,
  nên patch/import cũ không tạo bản logic thứ hai.
- Thêm lifecycle Python đa nền tảng: worker tách process, PID + create-time +
  command identity, duplicate prevention, state/stdout/stderr/exit persistence,
  status classification, logs follow, graceful stop và TensorBoard độc lập.
- Chuẩn hóa run mới với config/environment/dataset/state ở root và các thư mục
  logs/checkpoints/best_adapter/metrics/predictions/plots/reports. Reader plot,
  report, status và GPU acceptance fallback layout phẳng để đọc run lịch sử.
- Thêm test lifecycle bằng mock cho dry-run, duplicate, identity mismatch, stop
  safety và dashboard; dry-run CLI thật xác nhận 4 step, RTX 4050/CUDA 13.0 và
  hash của ba split mà không tạo artifact.
- Thêm CI Windows/Ubuntu, tài liệu canonical development, GPU setup, training và
  evaluation. Editable install và compatibility import được kiểm tra từ cwd ngoài repo.
- Gate cuối: 156 test pass, 1 optional skip; Ruff, compileall, pip check,
  git diff --check, PowerShell AST và CLI help matrix pass. Không chạy model/GPU training.

# TASK-20261016-01 - Docker web và Ollama

- Thêm image Python 3.12 cho web, cài nhóm `rag,gpu` để giữ lựa chọn
  QLoRA, bind cổng 8000 và healthcheck HTTP có warm-up 10 phút.
- Thêm Compose ba service: Ollama GPU, job idempotent tải `qwen2.5:7b`, web
  GPU phụ thuộc health/model-init. Dùng volume riêng cho Ollama, RAG cache và
  Hugging Face; corpus/adapter được bind mount, không sao chép vào image.
- Giữ cấu hình Windows cũ; Docker dùng file riêng với endpoint service
  `http://ollama:11434`. Ollama giới hạn một model và parallel 1 cho GPU 6 GB.
- Build và runtime thật PASS: model-init exit 0, Ollama/web healthy, HTTP 200,
  CUDA nhận RTX 4050 trong web, web gọi Ollama nội bộ và request Base E2E
  trả lời đúng sau 77,93 giây warm-up.
- Lần tạo RAG cache trống vượt ba phút; seed cache hoàn chỉnh cùng
  corpus từ host vào named volume, không xóa artifact local. Ghi lỗi và
  nâng `start_period` lên 10 phút.
- Kiểm chứng: 11 test documentation/config/server, Ruff, compileall, Compose
  config và diff-check PASS. Chưa chạy QLoRA thật trong container hay browser QA.

# TASK-20261016-02 - dọn runtime local sau Docker hóa

- Preflight xác nhận ba target là thư mục thật với path tuyệt đối,
  không phải symlink; Docker web/Ollama healthy và ba volume tồn tại.
- Gỡ Ollama Desktop Windows 0.34.4 bằng winget. Xóa `.ollama`, `env` và
  `outputs/rag_cache` local, giải phóng ước tính 9,1 GiB. Thao tác xóa
  trực tiếp, không thể khôi phục qua Recycle Bin.
- Giữ nguyên `Data/vector/unified`, adapter QLoRA, cache Hugging Face dùng
  chung, image/container/network và toàn bộ Docker volume.
- Hậu kiểm: winget không còn package Ollama; ba path đã xóa không
  còn; Docker web/Ollama healthy, HTTP 200, model Ollama còn, CLI `vigov --help`
  trong container PASS. Test Python local không chạy lại vì `env` là target đã xóa.

# TASK-20261016-03 - chuẩn hóa hướng dẫn runtime Docker

- Chuyển quick start ở README từ cài package/chạy `vigov` local sang
  `docker compose up --build -d` và kiểm tra trạng thái service.
- Bổ sung hướng dẫn khởi động lần đầu, chạy hằng ngày, doctor, Ollama list,
  hỏi đáp, chuẩn bị RAG cache, log, restart, dừng stack và bảo toàn volume.
- Viết lại tham chiếu CLI theo container và chuyển hướng dẫn vận hành RAG sang
  `configs/rag/inference-docker.yaml` với endpoint nội bộ Ollama.
- Ghi rõ corpus/adapter vẫn cần trên host; `env`, `.ollama` và cache RAG local
  không cần. Ingestion, training và evaluation là workflow chuyên biệt, chưa
  thuộc Compose inference hiện tại.
- Kiểm chứng thực tế: `docker compose config --quiet`, web/Ollama healthy,
  `vigov doctor`, `vigov rag prepare` với 117871 vector, test documentation và
  `git diff --check` đều PASS.


## TASK-20261016-04 - Gỡ CI và hậu kiểm Docker sau builder prune

- Xóa workflow CI duy nhất `.github/workflows/ci.yml`; giữ nguyên các gate test,
  Ruff, compileall, pip check và diff-check dưới dạng lệnh chạy thủ công trong
  `docs/setup/development.md`.
- Khi bắt đầu, Docker Desktop engine chưa chạy. Sau khi khởi động lại, xác nhận
  Docker 29.8.2, Compose hợp lệ, build cache bằng 0 B, nhưng image web/Ollama và
  ba volume `ollama-models`, `rag-cache`, `huggingface-cache` vẫn tồn tại.
- Chạy `docker compose build web` từ cache rỗng thành công, recreate service web
  và chạy lại model init thành công. Runtime cuối: web/Ollama healthy, HTTP host
  200, web gọi Ollama 200, model `qwen2.5:7b` 4,7 GB còn nguyên, CUDA nhận
  NVIDIA GeForce RTX 4050 Laptop GPU (6141 MiB tổng theo `nvidia-smi`).
- Kiểm chứng: `docker compose config --quiet`, build web, `vigov --help`, health,
  HTTP và `git diff --check` đều PASS. Không chạy generation E2E hoặc browser QA.
## TASK-20261016-05 - Hợp nhất package training

- Giữ duy nhất implementation tại `src/vigovbot/training`; xóa 22 wrapper root
  `training/` và 22 wrapper `src/training/`, kể cả cache ignored còn sót.
- Chuyển test, mock target và lệnh tài liệu từ `training.*` sang
  `vigovbot.training.*`; package discovery trong `pyproject.toml` chỉ còn
  `vigovbot*`. Cập nhật tài liệu kiến trúc, development và skill cấu trúc để
  không tái tạo namespace song song.
- Kiểm chứng trong container tạm có `.[test,dev]`: 166 test pass, 3 optional skip;
  Ruff, compileall và pip check PASS. Wheel có 24 file dưới
  `vigovbot/training/` và 0 file dưới `training/`.
- Rebuild/recreate image web thành công. Runtime mới resolve
  `vigovbot.training` từ site-packages, `find_spec('training')` trả `None`; web
  và Ollama healthy. Không chạy training/model generation/benchmark.

## TASK-20261017-01 - Hợp nhất evaluation và CLI `eva`

- Chuyển toàn bộ QA benchmark vào `src/vigovbot/evaluation`; đổi hai file
  trùng tên thành `benchmark_runner.py` và `benchmark_report.py`, giữ nguyên
  primitive RAG `runner.py`/`report.py`.
- CLI duy nhất là `vigov eva`; lệnh `test --run-id` cũ của QLoRA được
  gộp vào cùng entrypoint. Xóa `qa-v4` không giữ compatibility alias.
- Cập nhật import, test, notebook generator/notebook, tài liệu và skill cấu
  trúc; giữ nguyên `outputs/qa_v4` là artifact lịch sử.
- Kiểm chứng: 42 targeted test và full suite 168 test pass, 3 optional skip;
  Ruff, compileall, documentation link test và diff-check PASS. Wheel sạch có
  18 file `vigovbot/evaluation`, 0 file `vigovbot/qa_v4`.
- Rebuild image không cache và recreate web thành công; runtime chỉ resolve
  `vigovbot.evaluation`, CLI `eva` exit 0, web/Ollama healthy và HTTP 200.

## TASK-20261017-02 - Đề xuất Evaluation Run v2 cho các model

- Audit xác nhận `examples/QA/golden_test_cases.jsonl` là JSON mô tả schema,
  không phải 3.850 case thật; example v2 chỉ có hai record
  `not_run`/`not_scored` và cùng gắn architecture `base`.
- Đối chiếu pipeline canonical cho thấy đã có Base, RAG Base và QLoRA
  không retrieval; chưa có profile QLoRA + RAG và chưa có writer/scorer
  xuất trực tiếp contract v2.
- Viết đề xuất bốn model profile, nội dung trace theo case, quy tắc
  `null` + status cho metric thiếu, bốn phase triển khai và ba PR đề xuất.
- Kiểm chứng chỉ gồm audit source/schema và documentation checks; không
  chạy model, generation, BERTScore, GPU hay benchmark 3.850 case.

## TASK-20261018-01 - Hoàn thiện luồng Evaluation Run v2 offline

- Xác nhận `Data/golden_dataset` có 3.850 case: 2.200 train, 550 val,
  1.100 test; 350 case unanswerable có evidence/citation rỗng theo chủ ý.
- Thêm `src/vigovbot/evaluation/v2.py` và lệnh `vigov eva export-v2` chỉ
  đọc Golden/prediction đã có. Lệnh không import adapter inference, từ chối
  ID ngoài split/trùng ID/thiếu coverage, trừ khi chọn `--allow-partial`.
- Hỗ trợ `base`, `finetuned`, `rag_base`, `rag_finetuned`; tính metric
  reference/retrieval/citation/telemetry có đủ input. Metric semantic,
  groundedness, BERTScore và constraint thiếu judgment giữ `null` kèm status.
- Output mỗi case theo schema v2 và summary riêng gồm hash provenance,
  coverage, answerable/unanswerable cohort, execution status và aggregate có `n`.
- Kiểm chứng: 8 test v2 pass; nhóm evaluation/QA/documentation 30/30 pass;
  compileall và `git diff --check` pass. Export skeleton thật trên 1.100 test
  case có 1.100/1.100 record pass JSON Schema, `inference_performed=false`.
- Không chạy model, retriever, BERTScore, judge, GPU hay benchmark generation.
  Ruff SKIPPED vì image inference không có package; full suite trong image này
  còn failure ROUGE-L cũ do thiếu optional `rouge-score`.

## TASK-20261018-03 - Audit phần dư thừa trong Evaluation v2

- Lần theo luồng `run-v2 -> predictions.jsonl -> export-v2 ->
  results.jsonl/summary.json` và đối chiếu schema v2 với response `/api/chat`.
- Xác định `predictions.jsonl` lưu đồng thời `retrieved`,
  `retrieved_chunk_ids` và `retrieved_scores`; `question`, `history_mode` và
  `web_model_id` cũng lặp theo từng dòng dù có thể suy ra hoặc đặt ở manifest.
- Các nhóm metric đầy đủ, Golden nhúng trong từng result và performance lặp ở
  hai nhánh làm output lớn, nhưng hiện thuộc contract schema v2 nên không thể
  bỏ nếu vẫn cam kết xuất đúng schema này.
- Phát hiện response web chỉ công khai `sources`, còn `run-v2` đặt
  `citations=[]`; scorer sau đó coi citation kỳ vọng nhưng rỗng là điểm 0.
  Vì vậy citation hiện không phản ánh citation do model sinh và cần sửa contract
  trước khi dùng ba metric citation để so sánh RAG.
- Không chạy model, không tạo benchmark và không thay đổi source/runtime.

## TASK-20261018-04 - Tối ưu Docker development và dọn build cache

- Xác nhận cổng 8000 do PHP/Laravel PID 9224 sử dụng; không dừng tiến trình đó,
  chuyển mapping web sang `${VIGOVBOT_WEB_PORT:-8001}:8000`.
- Mount `src` và `configs` read-only, đặt `PYTHONPATH=/app/src`; bỏ mount Golden
  và output evaluation khỏi web, chuyển hướng dẫn Evaluation v2 sang chạy host
  và gọi API web tại cổng 8001.
- Tách cài dependency `rag,gpu` thành layer chỉ phụ thuộc `pyproject.toml`, sau
  đó mới copy/cài source bằng `--no-deps`; thay đổi source không còn làm mất
  cache dependency trong các build theo Dockerfile mới.
- Recreate bằng `docker compose up -d --no-build`; web/Ollama healthy và HTTP
  200. Dockerfile check, Compose config, 11 test v2, documentation test,
  compileall và diff-check đạt sau khi sửa newline nhật ký.
- `docker builder prune -a -f` xóa 12,76 GB build cache. Hậu kiểm còn 0 B build
  cache; không xóa image, named volume, Golden, adapter hoặc output.
- Không chạy model generation, benchmark hay Evaluation v2 thật.

## TASK-20261018-05 - Thêm tiến trình nhẹ cho Evaluation v2

- Thêm progress text dùng thư viện chuẩn, ghi ra stderr để giữ JSON summary trên
  stdout sạch và không thêm `tqdm` hoặc dependency runtime.
- `run-v2` cập nhật tối đa mỗi 10 giây và luôn in dòng cuối, gồm current/total,
  phần trăm, success/error, elapsed và ETA.
- `export-v2` cập nhật mỗi 100 Golden record và luôn in dòng cuối, gồm
  current/total, phần trăm, elapsed và ETA.
- Thêm regression assertion cho dòng hoàn tất của cả hai bước; 11 test v2 và
  1 test documentation pass, compileall và diff-check pass.
- Không gọi model, không chạy benchmark và không thay đổi schema/metric/artifact.

## TASK-20261018-06 - Đồng bộ lệnh cài đặt và khởi chạy

- Cập nhật README/CLI/Docker/RAG guide theo ba trường hợp: first build hoặc đổi
  dependency/Dockerfile dùng `up --build`; chạy hằng ngày dùng `up -d`; chỉ sửa
  `src`/`configs` dùng `restart web` nhờ bind mount.
- Đồng bộ URL web/API active sang cổng host 8001 và thêm
  `VIGOVBOT_WEB_PORT=8001` vào `.env.example`; cổng container vẫn là 8000.
- Làm rõ Evaluation v2 chạy từ môi trường Python host đã cài editable, trong
  khi Ollama/inference web vẫn chạy trong Docker.
- Quét tài liệu active không còn `localhost:8000`; documentation test, Compose
  config và diff-check pass. Không sửa/restart runtime, model, data hoặc artifact.

## TASK-20261018-02 - Tách Evaluation v2 thành hai lệnh

- Thêm `vigov eva run-v2` đọc Golden split, chọn `--limit`, gọi
  `/api/chat` và ghi prediction theo `TC_*`; Base/QLoRA/RAG mặc định lần lượt
  dùng `qwen-base`, `qwen-qlora`, `qwen-rag`, có thể ghi đè bằng `--model-id`.
- Payload HTTP chỉ có question, model ID và history. Ground truth, taxonomy,
  context/citation label và key fact không được gửi tới model.
- Prediction thành công giữ answer/action/retrieval source/latency; request lỗi
  vẫn tạo record `execution_status=error`, không bịa answer. Output và run
  manifest không ghi đè.
- Compose mount `Data/golden_dataset` read-only và `outputs/evaluation_v2` read-write,
  nên sau một lần rebuild workflow chạy bằng hai lệnh `docker compose exec`.
- Kiểm chứng: 11 test v2 pass; 39 test evaluation/QA/docs/server pass;
  Compose config, compileall, public CLI routing và `git diff --check` pass.
  Không gửi request model thật trong quá trình kiểm chứng.

## TASK-20261018-07 — Đồng bộ training, adapter, Docker secrets, lock và EOL

- Bổ sung training QLoRA 4-bit vào Mermaid/bảng module và bỏ phủ nhận fine-tuning.
  Code hiện hardcode load_in_4bit=True; chưa xác nhận training 8-bit/production.
- Config dùng path chung; loader hỗ trợ QLORA_ADAPTER_PATH, Compose bind read-only
  vào /app/models/qlora với create_host_path:false và lỗi rõ khi thiếu biến.
  .env local được bổ sung lựa chọn adapter hiện có, không đọc/in token; artifact giữ nguyên.
- .dockerignore loại .env/.env.*, PEM/KEY ở mọi cấp. Không có bằng chứng token đã lộ.
- Pin Transformers 4.57.3 tại extras rag/embedding; uv pip compile resolve lại 4 lock
  Windows và thêm Linux x86_64/Python 3.12 (rag,gpu). Dockerfile cài lock Linux.
  Đây là resolver lock, không phải xác nhận cài đặt hoặc GPU runtime.
- .gitattributes quy định LF cho text và CRLF cho PowerShell/batch; chuẩn hóa 7 file
  mixed được báo cáo. Không stage/renormalize toàn repo hoặc sửa checkpoint.
- PASS: 18 test chọn lọc từ tests.test_rag_config_cli (4 test cấu hình/CLI),
  tests.test_documentation và tests.test_artifact_safety trong image vigovbot-web:latest
  với network none, repository read-only; Ruff 0.15.6 cho config/test mới;
  compileall cho hai file; docker compose config --quiet; thiếu biến adapter bị từ chối;
  git diff --check; scan tracked text không còn mixed EOL.
- Lượt chạy cả tests.test_rag_config_cli + docs: 6 test, 1 lỗi do thiếu matplotlib.
  Python host thiếu pydantic/Ruff nên dùng image có sẵn và uvx Ruff trong cache tạm.
- Chưa clean install lock, rebuild Docker hoặc chạy inference/training. Không restart service.

## TASK-20261018-08 — Helper canonical và hợp đồng lexical

- Hash helper/training/audit chuyển sang alias artifacts.file_hash, bỏ read_bytes
  toàn file; indexing dùng configure_console.
- utils/text.py gom NFC/casefold/Unicode tokens cho training data/metrics, QA và
  V2. Audit overlap ghi normalization version; V2 giữ coercion input cũ.
- evaluation/lexical.py định nghĩa vi-lexical-v1: SacreBLEU none/exp/effective-order,
  scale 0–100, corpus aggregate; ROUGE tokenizer Unicode dùng chung.
  Training summary và QA report gắn contract, legacy report gắn version riêng.
- Không đổi baseline notebook legacy; tài liệu qa-rag-evaluation.md ghi rõ phải
  rescore prediction cũ trước khi so sánh và đồng nhất cohort/denominator.
- utils/jsonl.py đọc UTF-8 BOM với chính sách blank skip/error; training giữ
  validation/duplicate ID. experiments recovery không bị hợp nhất vào dataset reader.
- PASS: Ruff các module bị tác động và test mới; 61 unittest trong container tạm:
  tests.test_shared_contracts, test_qlora_local, test_qa_v4, test_evaluation_v2,
  test_artifact_safety, test_documentation. Repo mount read-only; dependency test
  cài trong container bị xóa khi hoàn tất, không thay image runtime hay host.
- Test mới xác nhận hash đa chunk không read_bytes, NFC/NFD/casefold parity,
  BLEU/ROUGE tiếng Việt, blank-line policy và recovery không cắt lỗi giữa file.
- Không chạy GPU/model/benchmark hoặc sửa artifact cũ. Không commit.

## TASK-20261018-09 — Tách trách nhiệm orchestration

- chunking/tables.py chứa repair, flatten, header helpers thuần; markdown giữ
  method alias tương thích. Table repair vốn độc lập, nhận định cần instantiate
  toàn chunker không đúng với repair_table_continuations hiện tại.
- rag/response.py chứa resolve_route và generate_answer; pipeline giữ retrieval,
  prompt budget và assembly. Retry schema/citation, fallback và thời gian giữ nguyên.
- train.py tách _prepare_training_data, _prepare_model, _training_arguments,
  _finalize_training; giữ resume gate/hash, callback/optimizer state và best-restored
  validation. Đã sửa hướng dẫn dependency cũ trỏ requirements không còn tồn tại.
- scoring_legacy.py format và đổi tên biến; đọc/ghi file bằng Path và JSONL reader
  có context manager. Đối chiếu scorer trước refactor từ HEAD: bằng nhau trên 3
  biến thể view (all, selected, empty), gồm missing prediction và judgment.
- Namespace cùng basename không collision Python; bổ sung bảng trách nhiệm trong
  architecture.md thay vì đổi tên public hàng loạt. Runner schema/history khác nhau
  giữ riêng; benchmark thêm lỗi rõ ràng khi output tồn tại, vẫn exclusive-create.
  Không tuyên bố đã thêm resume cho threaded runner.
- PASS: 103 tests trong container tạm với repo mount read-only: refactor boundaries,
  ingestion chunking, RAG pipeline, conversation routing, routing providers,
  training lifecycle, QLoRA local, QA v4/review, documentation. Các test model là mock.
- PASS: Ruff phạm vi thay đổi, compileall src/test mới, diff-check. Không training,
  GPU resume, model inference hoặc benchmark thật. Artifact cũ giữ nguyên.

## TASK-20261018-10 — Runtime/API correctness

- server/app.py: khóa theo model call chỉ cho Ollama/local Transformers; API
  ngoài không chờ khóa và không thay _active_provider, tránh mất dấu owner GPU.
  Health/models vốn không dùng lock. GPU switching vẫn tuần tự hóa có chủ đích.
- Tất cả model lỗi trả 502 + status failed + results + error cho UI; mixed result
  trả 200/status partial; validation giữ 400. Đây là API comparison, không phải
  server OpenAI chat-completions. Không thay schema success từng model.
- evaluation/adapter.py: hai except nằm ở unload cleanup; warning exception type
  thay pass, giữ exception generation và kết quả đã hoàn thành, không in URL/token.
- Retriever dùng SELECT IN theo tối đa 900 ID/batch trong một vùng khóa, lookup
  map rồi trả theo FAISS rank; thiếu metadata vẫn raise. K thông thường một query.
- Batch local inference giữ RLock đến hết decode và dùng deepcopy tokenizer,
  padding state cache không đổi kể cả generate lỗi; release cache không xen ngang.
- Provider vốn copy message ở nhánh schema; thêm validation list không rỗng,
  role/content hợp lệ và copy ngay đầu cho mọi nhánh trước gửi request.
- PASS: 62 unittest trong container tạm, source mount read-only: runtime safety,
  server, routing providers, RAG pipeline, QA v4, evaluation v2. HTTP test thật
  localhost status 400/502/200 và content-type; model/API ngoài đều giả lập.
- Test concurrency dùng barrier 2 request, xác nhận remote không chờ GPU lock;
  SQL trace xác nhận một SELECT và rank; batch lỗi giữ tokenizer và nhả lock;
  provider không gọi HTTP khi messages rỗng và không sửa caller khi network lỗi.
- PASS Ruff, compileall, documentation, diff-check. Không chạy GPU/model/load test,
  không đo throughput thực tế, không recreate dịch vụ hay sửa artifact.

## TASK-20261018-11 — Coverage có bằng chứng và PEFT CPU integration

- Review 0% không đúng với nhiều module đã có test; đo full suite với coverage
  branch/line thay vì suy ra từ tên file. Chi tiết bảng tại setup/development.md.
- pyproject.toml cấu hình coverage; scripts/verify_tests.py chạy unittest verbose,
  offline, giữ test exit status và xuất tests.log/coverage.json/coverage.txt.
- Gom fixture ký tự từ 4 file, giữ overhead=10 và serialize_messages tại caller
  cần semantics đó; QLoRA FakeTokenizer có role/EOS riêng không gộp cơ học.
- Test real PEFT CPU không mock torch/Transformers/PEFT/tokenizers: tiny GPT2,
  masking, finite loss, gradient adapter, optimizer step, save/reload và logits parity.
- Lượt cuối: exit 0; 194 test, 3 skip; 3887/5624 statement (69,1%),
  1062/1794 branch (59,2%), combined 66,7%. Report trong
  outputs/verification/task-20261018-11; không commit artifacts.
- Skip có lý do: dataset v4 thiếu, Qwen tokenizer thiếu cache, Node.js thiếu.
  Integration HTTP/FAISS/SQLite đã có; chưa E2E OCR/model thật hay GPU QLoRA.
- Không khôi phục CI đã xóa chủ động; unittest không cần conftest/pytest.ini.
  Assertion chuẩn đã có expected/actual/traceback; test mới thêm context nghiệp vụ,
  không thêm message máy móc cho toàn bộ suite.
- PASS Ruff các test/script thay đổi, compileall, documentation và diff-check.
  Container tạm, repo read-only, chỉ thư mục verification được mount writable.

## TASK-20261018-12 — Typed training config và docs canonical

- training/schema.py dùng Pydantic strict/extra forbid theo từng section; validate
  type/range/cadence/LoRA/NF4/early stopping. config.py gọi schema, vẫn trả dict
  nguyên giá trị, không chèn default làm đổi snapshot/hash checkpoint cũ.
- Model khác default được chọn qua name và experimental=true; target modules
  tùy kiến trúc phải không rỗng/unique. Default Qwen 7B giữ bộ projection audited.
  trust_remote_code vẫn false. Schema không chứng minh PhoGPT/Llama/Qwen size
  khác chạy đúng; cần smoke riêng, chat template đúng và GPU phù hợp.
- refactor-summary đổi nhóm eval thành eva; QA guide đổi env/Scripts sang .venv.
- Di chuyển EMBEDDING.md đến docs/architecture/embedding.md và sửa mọi caller/link
  active trong docs/README và README subsystem. Không để cây tài liệu song song.
- configs/ingestion/settings.yaml đổi thành ingestion.yaml; pipeline và docs cập
  nhật, đồng bộ basename với package default. Không đổi giá trị ingestion.
- Stage cũ lưu nguyên bytes tại docs/project/stage-history-20261018.md (1.022 dòng,
  SHA256 462db71290983efb6530692c46010c38bf063fd3707a584a1dd15104933d414c).
  current-stage chỉ giữ snapshot ngắn, link archive/history; docs index đã cập nhật.
- PASS: 47 unittest chạy, 46 pass/1 skip tokenizer Qwen không có cache; nhóm
  training schema, QLoRA local/audit/readiness, unified CLI, ingestion, documentation.
  Test schema cover toàn profile repo, experimental opt-in, typo/type/cadence và
  không mutation snapshot. Ruff, compileall, documentation link, diff-check pass.
- Không chạy model mới, training/GPU, không đổi checkpoint/dataset; chưa commit.

## TASK-20261018-13 — Dependency/packaging/cleanup

- Khai báo huggingface-hub>=0.34,<1 ở core để artifact/preflight không lệ thuộc
  transitive install. Resolve lại 5 lock Windows/Linux; không sửa version bằng tay.
- torch==2.9.1 thuộc gpu, tương thích >=2.2,<3; không có xung đột chỉ vì range/pin.
  Giữ requires-python core, docs phân biệt GPU baseline 3.12 và wheel availability
  chưa xác nhận theo host. Không tuyên bố mọi Python 3.14 GPU wheel tồn tại/không tồn tại.
- helpers.__all__ liệt kê export; bỏ Ruff per-file F401 suppression.
- check_clean_env bỏ gate Windows 3.14, tự chọn Scripts/python.exe hay bin/python;
  mặc định install test/dev extras, --lock cho lock đúng nền tảng. Help/syntax pass,
  chưa chạy cài sạch full dependency ở từng OS/Python.
- check_wheel --wheel-dir hỗ trợ artifact tạm, kiểm tra installed entrypoint
  vigov/vigovbot qua importlib.metadata ngoài checkout: help/train/eva/data/doctor;
  legacy ingest/embed/rag vẫn được kiểm tra.
- main.py dùng unified dispatcher, không argument hiện help; ingestion phải tường minh.
- Xóa đúng __pycache__/colab_worker_embed.cpython-314.pyc và
  merge_vector_packs.cpython-314.pyc sau xác nhận source không còn; rmdir ba cây
  context-management/repository-navigation/token-budget-optimization chỉ khi rỗng.
  Đường dẫn resolve nằm trong workspace; không recursive delete artifact.
- .gitignore thêm wheel/egg/.eggs, sqlite/db/index, wandb, desktop.ini, swp.
- PASS Docker container tạm: copy source build sang /tmp/package, wheel build,
  install target ngoài checkout, defaults và entrypoints, root help, 14 tests
  unified CLI/shared contracts/docs. Repo mount read-only; log/wheel trong
  outputs/verification/task-20261018-13. Không thay service/image runtime.
- PASS Ruff, compileall, docs, diff-check. Không clean-env matrix hoặc GPU/model.

## TASK-20261018-14 — Chốt release blockers sau review

- Kiểm tra Git trước khi sửa: worktree sạch, HEAD/main/origin-main cùng ở commit
  `8a65476`; các module `tables.py`, `response.py`, `schema.py`, `text.py`,
  `jsonl.py`, `lexical.py` và các test/helper mới đều đã được commit, không còn
  18 file untracked. Không tạo commit mới hoặc sửa lại lịch sử.
- `test_metric_formulas_and_corpus_aggregation` dùng `skipUnless(find_spec())`
  cho dependency `rouge-score`. Test pass khi cài ROUGE/SacreBLEU và được báo
  `skipped: rouge-score is unavailable` trong môi trường không có ROUGE.
- Ba `configs/rag/evaluation*.yaml` đặt `dataset_path: null`. Dataset hiện có
  `Data/tthc_test_case_v1/data/test.jsonl` là schema v2, không tương thích loader
  legacy `question`/`ground_truth`, nên không thay bằng một path tồn tại nhưng sai
  schema. `vigov eva` tiếp tục nhận dataset v2 qua `--dataset`; tài liệu legacy
  yêu cầu config riêng với dataset đúng schema.
- Thêm regression test nạp cả ba profile và xác nhận không còn dataset path/zip
  giả. PASS: profile load, documentation links, Ruff, compileall, diff-check.
- Docker Desktop tắt (`dockerDesktopLinuxEngine` không tồn tại), nên không dùng
  container; chạy test trong môi trường `uv --no-project` tạm. Không chạy model,
  benchmark, GPU hoặc runtime Docker.


## TASK-20261018-18 — Discovery độc lập, chunker decomposition, execution chung và typed config

- Test: thêm package bootstrap checkout và guard dependency có allowlist chính xác;
  chỉ thiếu package bên ngoài mới skip, không che lỗi module nội bộ/submodule sai.
  Import metric/tensor trong method có guard riêng. Mock encoder/GPU đúng phạm vi
  test logic; không giả lập FAISS để tuyên bố integration pass.
- Chunker: `headings.py` quản lý metadata/sanitize/heading; `splitter.py` quản lý
  ngân sách ký tự, overlap và bảng. Class điều phối còn 178 dòng thay vì 372.
  Giữ public TTHCChunkingError/sanitize_text/extract_metadata và output contract.
- Evaluation: `execution.py` là engine scheduling/retry/log tiến độ chung cho
  cả ba adapter. Giữ persistence/resume/history/output schema riêng; không tuyên bố
  đã xóa ba public entry point. Retry mặc định 1 attempt, opt-in có delay giới hạn;
  policy explicit ghi vào manifest/report, UI ETA benchmark vẫn ở adapter.
- Training: load_config trả TrainingConfig; train và caller dùng thuộc tính có kiểu.
  Dict chỉ còn ở parsing YAML/override và serialization. Private path metadata không
  vào snapshot; exclude_unset giữ tương thích snapshot/resume cũ. Không chạy Mypy.
- Kiểm chứng: Python hệ thống 3.14 và `python -S -m unittest discover -s tests`:
  38 tests, 10 pass, 28 skip do thiếu dependency; không có lỗi discovery.
- Venv tạm `%TEMP%/vigov-task18-env`, Python 3.12, cài `.[test,dev]` và sacrebleu;
  HF_HUB_OFFLINE=1, TRANSFORMERS_OFFLINE=1. Full suite: 213 tests, 208 pass, 5 skip
  (3 cần torch, 1 tokenizer không có cache, 1 dataset v4 không có).
  Có kiểm chứng FAISS/SQLite thật và HTTP localhost bằng fixture/mock model.
- Parity đối chiếu source HEAD trước refactor: 48 trường hợp chunking (output,
  warnings và lỗi), 7 profile snapshot training đều bằng nhau.
- Metric dependency bị chặn qua import hook: 6 shared-contract tests, 3 pass,
  3 skip đúng; không che lỗi nội bộ. Ruff toàn repo, compileall, pip check,
  documentation/link checks trong full suite và git diff --check pass.
- Log kiểm chứng tạm: `%TEMP%/vigov-task18-{bare,nosite,focused,full}.log`.
  Lượt full suite ban đầu và cách sửa ghi ERR-20261018-18.
- Không chạy model/GPU/training/benchmark mạng/Docker; không sửa dataset/checkpoint,
  không commit. Hướng dẫn cập nhật tại docs/setup/development.md.
## TASK-20261018-19 — Evaluation trace qua Web Chat

- API `/api/chat` nhận boolean `evaluation_trace`; mặc định response như cũ. Opt-in trả schema trace 1.0 với route thực thi, router object, retrieval_query, context_used, evidence, citation status và telemetry thực có. Không trả raw provider response/raw router trong trace.
- Pipeline ghi actual_route theo nhánh đã chạy (rag_search, clarify, out_of_scope, routing_error); timing rewrite chỉ đo khi có lượt rewrite riêng. Routing time không bị gán giả thành rewrite time.
- run-v2 tự yêu cầu trace, giữ trace gốc và ánh xạ cho scorer; report có số mẫu available/unavailable/unsupported_version. Không gửi nhãn Golden hoặc cờ trace tới model.
- Citation đã validate được ánh xạ chunk_id → source_id. Không tự bật citations_enabled để giữ cùng hành vi Web Chat; disabled/thiếu trace giữ null, quan sát danh sách rỗng có status hợp lệ mới chấm 0. Prediction Web cũ có danh sách rỗng nhưng thiếu status được đánh dấu thiếu trace khi export lại. Artifact lịch sử không bị sửa.
- Scorer offline version 2 ghi trong provenance và metric_details. Token ước tính giữ riêng; token usage/throughput, TTFT, rerank time, VRAM, GPU utilization, cost chưa đo vẫn null.
- Kiểm chứng: nhóm API/v2/routing/multiturn 48 tests, 47 pass/1 skip. Full suite Python 3.12 venv tạm với HF offline: 217 tests, 212 pass/5 skip (torch, tokenizer cache, dataset v4). Regression HTTP localhost chạy make_handler + ChatApplication + run-v2 + export-v2 với model fixture; route/rewrite/citation/latency tới scorer đúng, không rò nhãn Golden.
- Ruff toàn repo, compileall, documentation checks và diff-check pass. Log: `%TEMP%/vigov-task19-full.log`. Không gọi model/GPU/benchmark mạng, không kiểm chứng Docker/deployment và không commit.
- Chốt triển khai: diff-check và Ruff lần cuối pass. `docker compose ps --format json` không kết nối được pipe dockerDesktopLinuxEngine; chưa thể xác nhận dịch vụ Docker nạp code mới. Cần khởi động Docker rồi khởi động lại service web trước khi chạy Golden thật.
## TASK-20261018-21 - Xác minh artifact Evaluation v2

- Base run `base-qwen2.5-7b-20261018-173953` và RAG run `rag-base-qwen2.5-7b-20261018-192403` đều phủ đúng 1.100 Golden test ID, không trùng/thiếu/thừa và có 1.100 execution success.
- Đối chiếu SHA-256 xác nhận `results.jsonl.summary.json`, `offline_scores_v2.json` và `offline_scores_v2_bertscore.json` cùng trỏ đúng Golden/prediction hiện có.
- Base: chrF 21,4384; SacreBLEU 2,0640; BERTScore F1 0,854424. RAG: chrF 41,3178; SacreBLEU 23,6626; BERTScore F1 0,904564; MAP@5 0,365917 trên 1.000 ca relevance.
- RAG có routing/retrieval/generation timing nhưng citation bị tắt ở 1.098 ca; token usage, TTFT, throughput, VRAM/GPU và cost đều thiếu. Không có judgment semantic/groundedness.
- Kiểm tra chỉ đọc artifact; không inference lại. `compileall` và Git checks đạt; unit test/Ruff và JSON Schema validator không có đủ dependency trong Python hiện tại.

## TASK-20261022-01 — Golden train/validation → SFT (2026-10-22)

- Thêm `src/vigovbot/training/golden_sft.py`, dùng reader JSONL chung và validator `training/data.py`; thêm CLI `vigov data golden-to-sft` tại `cli/main.py`. Tài liệu: `docs/guides/training.md`.
- Chỉ ánh xạ ID/history/question/expected_answer, không chuẩn hóa chuỗi; giữ mọi unanswerable. Kiểm tra hai split trước ghi, báo file/dòng/ID khi lỗi, chặn ID trùng và bảo vệ artifact có nội dung khác. UTF-8, ensure_ascii=False, newline LF cuối file, tái tạo byte giống nhau.
- Tạo train_sft.jsonl: 2.200 mẫu, 2.167 single-turn / 33 follow-up / 200 unanswerable; validation_sft.jsonl: 550 mẫu, 546 single-turn / 4 follow-up / 50 unanswerable. Không loại/cân bằng mẫu.
- Mapping tuyệt đối và thứ tự ID trên 2.750 mẫu PASS; đọc toàn bộ bằng `training.data.read_jsonl` PASS. Không trùng ID hoặc toàn conversation trong mỗi split.
- Exact overlap (không normalize): ID=0, toàn messages=0, prompt history+question=0, question cuối=2 chuỗi. Hai câu “Nếu nộp trực tiếp thì thời hạn và phí thế nào?” (14 train/2 val) và “Nếu nộp trực tuyến thì thời hạn và phí thế nào?” (15 train/2 val) có history khác; không loại dữ liệu. Question duplicate nội bộ: train 3 nhóm/30 bản dư, validation 2 nhóm/2 bản dư.
- Chạy helper `.agents/skills/dataset-validation/scripts/validate_dataset.py` qua hàm validate trên projection question/split tạm vì helper không đọc schema messages: 2.750 record, 0 lỗi, 34 bản dư trên tập gộp, 2 câu giao split sau casefold/chuẩn hóa whitespace. Phân biệt kiểm tra chuẩn hóa này với exact nguyên văn bên trên. Không chạy near-duplicate.
- Kiểm chứng bằng Python 3.12 trong `%TEMP%/vigov-sft-check`, PYTHONPATH=src, PYTHONUTF8=1. Không cài model stack.
- PASS: `python -m unittest tests.test_golden_sft tests.test_training_schema tests.test_documentation -v` (14/14 PASS: 8 converter, 5 training schema, 1 documentation).
- PASS: `python %TEMP%/vigov-sft-verify.py`: gọi CLI thật bằng Typer CliRunner, assert count/ID/mapping/schema, hash trước/sau, không test_sft và tái tạo vào thư mục tạm để so byte. Report tạm `%TEMP%/vigov-sft-verify.json`.
- PASS: `python -m ruff check src/vigovbot/training/golden_sft.py src/vigovbot/cli/main.py tests/test_golden_sft.py`; `python -m compileall -q` trên ba file này.
- Lượt test đầu trên Python hệ thống FAIL vì thiếu filelock; đã xử lý môi trường (ERR-20261022-01). Lượt diff-check đầu FAIL vì dòng trống EOF tài liệu, đã xóa.
- SKIPPED theo phạm vi: near-duplicate, tokenizer, training/inference/GPU/model download/benchmark, full suite không liên quan. Không tuyên bố chất lượng mô hình từ kiểm chứng dữ liệu.
- Golden source/config training không sửa; test chỉ được đọc bytes để hash, không dùng chuyển đổi/training/validation. Không tạo test_sft. Data bị Git ignore theo quy tắc hiện có; artifact có trên đĩa, không force-add, không commit/push.
- Giữ thay đổi chưa commit ban đầu của người dùng tại current-stage (dấu gạch tiêu đề TASK-20261018-22).

SHA-256 nguồn trước = sau:

- `test_golden.jsonl`: `5bf3606d87690e3b1625f7dc31c593d4226d4b19c79aa9cd75e31aaca102a127`
- `train_golden.jsonl`: `e68a3fa29cbad31a0d83ba5b4b7fe79e561a3dd88157ae51968dbbbb2c1a70fa`
- `val_golden.jsonl`: `ef0602251f67b4336b52690e8322d11127973b161c54e7f8f0efacf0ffa17589`

SHA-256 artifact:

- `train`: `c38649aa644be6dd97c26757cbe8acc3f91fdba86f37cd6eb584cb5dfcad7e0d`
- `validation`: `fdf7cfb5d22ee944055adaaf1aa54ed3eb48f2ada6f8165cdb2c12d32f60a05a`

Đề xuất commit: `feat(data): convert Golden train and validation to lossless SFT`

- Chốt: `git diff --check` PASS; `git status --short` gồm 6 file sửa và 2 file code/test mới, không có Golden/config trong diff. Hai artifact SFT tồn tại nhưng bị ignore; thay đổi ban đầu của người dùng vẫn được giữ.
# TASK-20261022-03 — Judge local, giai đoạn đầu

- Thêm ollama_judge.py và CLI judge-v2: chỉ endpoint loopback, model explicit, schema score, hash input/rubric và digest model; output tạo mới, flush từng ca.
- Giới hạn: judgment AI nhị phân có null; chưa nối scorer v2, chưa claim extraction/human/pairwise, chưa triển khai trace mới.
- Compileall đã chạy; test ban đầu lỗi filelock khi import v2, đã chuyển import vào hàm runtime. Ollama preflight timeout, chưa inference.
- Bổ sung: TTFT streaming Ollama, token usage final-call, citation source/claim ID, decomposition/RRF và mapping, MAP@10 có depth gate, scorer sub-query exact-normalized, judge claim extraction và merge hash-bound, pairwise human packet/score, schema mở rộng và hướng dẫn evaluation-extended.md.
- Config mới opt-in; action giữ enum năm nhãn hiện tại. GPU/VRAM/cost không có telemetry vẫn null. Không chạy model hoặc judge; người dùng chạy ở máy cấu hình cao.
- Kiểm chứng cuối: 57 tests PASS (evaluation v2, judge, extended/schema, documentation, server, routing providers, conversation routing); Ruff PASS; compileall PASS; diff-check PASS. Chưa test rag_config_cli do thiếu faiss; không chạy GPU/model.
- Bổ sung complete-v2, run-v2 --resume/--complete-trace, judge --resume, chrF++, provider call ledger, context judge guard, rubric error polarity và capability preflight. Test resume xác nhận không gọi lại model cho prediction đã lưu. Kết quả cuối cập nhật stage; không chạy inference.
- Bổ sung lần cuối: exact METEOR (identity stem/no synonyms), cosine SentenceTransformer, GPU nvidia-smi collector, PyTorch allocator peaks/token/TTFT, runtime identity source/config/Ollama digest/adapter/base snapshot/index/corpus, noise replay fixed prompt + labeled distractors và paired correctness. Retry ca lỗi với backup, không inference lại ca thành công.
- Regression mới: units GPU và scope, noise giữ prompt/bỏ gold answer/resume, retry chỉ ca lỗi. 61 tests offline PASS; Ruff PASS. Không chạy model/GPU/judge thực; mọi đo GPU ở test là fixture.
- Chốt bổ sung: 63 tests PASS sau thêm scorer extended fixture và preflight không gọi inference khi GPU không đo được. Đây là kiểm chứng code/fixture, không xác nhận chất lượng model hay benchmark hardware.
# TASK-20261023-01 — Chuẩn bị triển khai V100 thuê

- Thêm profile `v100_32gb_golden_sft.yaml` dùng FP16 cho SM70 và smoke profile 4 step riêng.
- Thêm script Linux setup/verify, không tự chạy train/evaluation; thêm hướng dẫn lệnh người dùng chủ động chạy và lưu ý vector RAG 6,8 GB.
- Đóng gói source + Golden data thành archive 2,3 MB; kiểm tra không có `.env`, outputs hoặc Data/vector. Không chép secret/checkpoint/cache.
- SSH TCP pass nhưng BatchMode/key fail `Permission denied`; SCP non-interactive không có credential channel. Chưa thay đổi container.
- Kiểm chứng local: 14 test PASS; Ruff PASS; config resolve ra float16/train Golden/test null; diff-check PASS. Linux/CUDA/container NOT VERIFIED.
- Đã triển khai thật vào `/workspace/ViGovBot`: Conda Python 3.11.17, PyTorch 2.9.1+cu128, CUDA/V100 SM70 nhận đủ 32 GB; dataset report xác nhận 2.200 train và 550 validation, readiness `READY`.
- Sửa setup tương thích image chỉ có Python 3.10: tự tạo môi trường Conda Python 3.11 và dùng PATH trực tiếp thay vì giả định có `bin/activate`. Thêm `jsonschema` vào test extra theo import thực tế.
- Kiểm chứng remote cuối: 41 test PASS, Ruff PASS, compileall PASS. Không tải model weights và không chạy smoke/train/evaluation/judge. RAG vector và Ollama judge vẫn là dependency vận hành riêng.
# TASK-20261023-02 — Khóa complete-v2 tự đủ trace

- Health endpoint công bố capability contract version 2 cho complete trace: top-10, sub-query retrieval, citation, token/TTFT/latency, GPU samples, runtime identity và noise replay.
- `complete-v2` kiểm tra toàn bộ capability trước GPU/judge/identity và trước prediction đầu tiên; server cũ hoặc thiếu trường bị từ chối, không cần người dùng chỉnh YAML.
- Đã đồng bộ ba file source/test lên container V100. Kiểm chứng local và remote: 26 test PASS, Ruff PASS, compileall PASS; không chạy model/evaluation.
# TASK-20261023-03 — Tối ưu throughput V100 32 GB

- Profile V100 đổi train batch 1→2, eval batch 1→4, accumulation 8→4, giữ effective batch 8; tắt gradient checkpointing và dùng 4 dataloader worker với pinned/persistent memory.
- RAG query encoder chuyển CPU→CUDA. BERTScore mặc định batch 16. Web thêm endpoint release model; complete-v2 tự unload generation/judge sau mọi inference và trước BERTScore/cosine để tái sử dụng VRAM.
- Đồng bộ source/config lên container. Remote 48 test PASS, Ruff PASS, compileall PASS; config resolve đúng batch 2/eval 4/accum 4/effective 8/checkpoint false/workers 4. Local focused 15 test PASS; full local có 1 lỗi môi trường thiếu FAISS đã ghi journal.
- Không chạy model nên chưa tuyên bố tốc độ/peak VRAM thực đo; smoke profile kế thừa đúng cấu hình full và là gate trước full training.
# TASK-20261023-04 - Tách capture bốn cấu hình trước khi chấm

- Thêm web profile `qwen-qlora-rag`: cùng base/adapter local Transformers với
  QLoRA thuần nhưng chạy qua retrieval/prompt/context RAG.
- `QLORA_ADAPTER_PATH` giờ khóa đồng thời hai profile QLoRA, tránh đánh giá nhầm
  adapter. `rag_finetuned` có default model ID `qwen-qlora-rag`.
- Thêm `noise-v2` resume độc lập để toàn bộ inference sạch/nhiễu được thu trong
  pha prediction; thêm `score-noise-v2` chỉ đọc judgment sạch/nhiễu và ghi report
  kèm SHA-256. Human/pairwise vẫn tách riêng.
- Kiểm chứng local: Ruff PASS; compileall PASS; `git diff --check` PASS. Pytest
  chưa chạy local vì các venv hiện có thiếu pytest/filelock; cần chạy bộ test
  tập trung bằng `.venv-v100` trên container sau khi đồng bộ source. Không chạy
  model, train hoặc evaluation.
# TASK-20261023-05 - Giữ answer khi chỉ citation sai sau retry

- Tách lỗi citation khỏi lỗi structured answer cốt lõi: vẫn retry như cũ; chỉ
  khi answer/action/evidence của retry hợp lệ mới giữ prediction và đánh dấu
  `citations_status=invalid_model_output`. JSON/action/evidence sai vẫn thất bại.
- Trace công khai citation rỗng có trạng thái lỗi; scorer tính citation recall 0
  và invalid-citation rate 1, không biến lỗi quan sát được thành missing input.
- Không đổi prompt/retrieval/generation cho các ca đã thành công, nên resume giữ
  chúng và chỉ chạy lại 21 ca 502. Thêm regression test cho fallback và metric.
- Kiểm chứng local: Ruff PASS, compileall PASS, `git diff --check` PASS. Pytest và
  HTTP/model runtime chờ chạy trên `.venv-v100` sau khi đồng bộ.

- Bổ sung theo log runtime: bốn ca cố định không phải timeout mà là JSON bị cắt
  sau retry. Thêm final repair thứ ba chỉ cho `JSONDecodeError`, cùng budget 512
  token và prompt giới hạn answer 600 ký tự/tối đa 3 citation. Không thay đổi
  cấu hình hay chạy lại 1.096 prediction thành công.
- Sau lượt thật còn một ca model bỏ qua giới hạn prompt; final repair giờ dùng
  deep-copy response schema và đặt `maxLength`/`maxItems` thật. Hai lần sinh đầu
  và mọi prediction đã thành công không thay đổi.
- Sửa QLoRA + RAG: lỗi JSON của optional sub-query decomposition không còn trả
  502; fallback retrieval query gốc và trace trạng thái fallback. Thêm regression
  test; không thay đổi generator/retrieval khi decomposition hợp lệ.

# TASK-20261023-06 - Vẽ biểu đồ training QLoRA từ backup

- Run nguồn:
  `backups/vigovbot-stage-offline-pass-20261023-005223/outputs/qlora/qlora-v100-optimized`;
  không có `backups/qlora` trực tiếp. Dùng pipeline canonical
  `vigovbot.training.plot` và log `logs/training_events.jsonl`.
- Đã tạo 9 biểu đồ trong `plots/`: `training_loss.png`, `validation_loss.png`,
  `combined_loss.png`, `learning_rate.png`, `gradient_norm.png`, `gpu_memory.png`,
  `time_per_epoch.png`, `throughput.png`, `parameter_proportions.png`; đồng thời
  tạo `plot_manifest.json` ghi field/source từng biểu đồ.
- Dữ liệu quan sát: training `early_stopped` ở step 700; best validation loss
  `0.3928232789039612` tại checkpoint/step 500. Biểu đồ kết hợp đánh dấu cả hai mốc.
- Không tạo `evaluation_comparison.png` vì không có artifact post-training test;
  giữ trạng thái `unavailable` trong manifest, không suy diễn metric.
- Kiểm chứng PASS: 9 PNG mở được bằng Pillow, 8 file 1280x720 và biểu đồ tham số
  960x720, mọi file khác 0 byte; xem trực quan `combined_loss.png`; unit test
  `tests.test_qlora_plot` 2/2 PASS. `git diff --check` exit 0 nhưng báo warning
  quyền đọc `outputs/.gitkeep` đã tồn tại từ worktree.
- Dependency plotting được cài riêng vào `%TEMP%/vigov-plot-deps-v2`, không sửa
  môi trường dự án. Không chạy training, model, evaluation hoặc sửa artifact gốc.

Đề xuất commit: `docs(qlora): add training plots from V100 backup`
# TASK-20261023-08 - Điều tra Web QLoRA treo và thông báo 404

- Kiểm tra trực tiếp `docker compose ps`, log `web`, `/api/models`, cache Hugging Face, adapter mount, tài nguyên container và GPU.
- Hai request 404 là `/favicon.ico` và `/.well-known/appspecific/com.chrome.devtools.json`, không phải `/api/chat`.
- QLoRA lần đầu tải bốn shard model nền trong 7 phút 48 giây; cache tăng trong lúc chờ và các file `.incomplete` biến mất sau khi hoàn tất.
- Model nạp 4/4 checkpoint shard trong khoảng 27 giây; adapter `/app/models/qlora` có đủ cấu hình và weights, dung lượng khoảng 170 MB.
- Trong pha generation, RTX 4050 dùng 5.884/6.141 MiB; không ghi nhận OOM/restart. Request thực tế kết thúc HTTP 200.
- Không thay đổi source, cấu hình, checkpoint hoặc cache. Không thêm lỗi vào failure journal vì đây là độ trễ cold start, không phải runtime failure.
