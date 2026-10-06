# Lịch sử triển khai

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
