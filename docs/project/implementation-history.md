# Lịch sử triển khai

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

