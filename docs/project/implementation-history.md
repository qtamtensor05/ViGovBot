# Lịch sử triển khai

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
