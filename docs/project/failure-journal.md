# Nhật ký vấp ngã

Chỉ ghi lỗi quan sát được; phân biệt nguyên nhân đã xác nhận với giả thuyết.

## ERR-20261003-10

- Task: TASK-20261003-09.
- Triệu chứng: lệnh kiểm thử đầu tiên không import được `vigovbot`.
- Bối cảnh tái hiện: `python -m unittest tests.test_qa_v4` dùng Python hệ thống.
- Nguyên nhân đã xác nhận: package dùng layout `src/` và Python hệ thống không
  cài editable package; đây là lỗi môi trường đã từng được ghi nhận.
- Xử lý: chuyển sang `env\Scripts\python.exe`, là môi trường dự án hiện có.
- Kết quả kiểm chứng: chạy lại đạt 8 test QA v4; Ruff cũng đạt.
- Phòng tránh: dùng Python trong `env/` cho kiểm thử repository.

## ERR-20261003-09

- Task: TASK-20261003-07.
- Triệu chứng: lượt đầu `scripts/smoke_routing_live.py oil` nhận HTTP 500 từ
  Ollama ở lần gọi router; chưa có response JSON model để validate.
- Nguyên nhân: chưa xác định; không có body lỗi/log runner trong traceback nên
  không khẳng định do schema, bộ nhớ hay tải model.
- Kiểm tra: gọi riêng /api/chat cùng schema với prompt ngắn, nhận HTTP 200 và
  JSON hợp lệ. Chạy lại nhóm oil thành công 2/2, nhóm basic thành công 4/4.
- Kết quả: lỗi API không còn tái hiện trong các lượt sau; không thêm retry HTTP
  tự động và không coi lỗi API là JSON sai dẫn đến fallback.
- Phòng tránh: khi lỗi tái hiện cần lấy body lỗi và log Ollama đúng thời điểm,
  phân biệt lỗi dịch vụ với lỗi schema/validator.

## ERR-20261003-08

- Task: TASK-20261003-06.
- Bối cảnh: probe Qwen thật với câu hỏi tràn dầu và history giả về hộ chiếu.
- Triệu chứng: cả initial/retry trả follow_up, query và clarification không rỗng;
  validator báo Retrieval route requires query and no clarification; fallback.
- Tái hiện: `env\Scripts\python scripts\probe_oil_spill_routing.py --with-history`.
- Thử giải pháp: cùng prompt/history dùng schema anyOf ép các trường theo nhánh.
- Kết quả: JSON hợp lệ ngay lần đầu, clarification rỗng; nhãn follow_up vẫn
  chưa đúng ý nghĩa câu hỏi chuyển chủ đề. Chưa sửa production, chưa chứng minh
  schema giải quyết mọi trường hợp. Artifact oil_spill_routing_probe_history.json.
- Phòng tránh đề xuất: schema + ví dụ phân loại + retry cụ thể + telemetry web.

## ERR-20261003-07

- Task: TASK-20261003-05.
- Triệu chứng: script xác thực lỗi UnicodeEncodeError khi in tiếng Việt.
- Lệnh: `env\Scripts\python scripts\verify_routing_artifact.py outputs\qa_v4\local_smoke.jsonl`.
- Nguyên nhân: stdout Windows dùng cp1252 không biểu diễn được tiếng Việt.
- Sửa: cấu hình stdout UTF-8; chạy lại thành công, kiểm tra đủ 10 dòng.
- Phòng tránh: script chẩn đoán in Unicode cần cấu hình encoding rõ ràng.

## ERR-20261003-06

- Task: TASK-20261003-05.
- Triệu chứng: 3 lượt trong artifact Qwen thật trả câu fallback mặc định.
- Bằng chứng: `outputs/qa_v4/local_smoke.jsonl`, dòng 8–10; raw response model
  `qwen2.5:7b`, initial_error/retry_error cùng marker fallback được lưu đầy đủ.
- Nguyên nhân xác nhận: JSON đúng cú pháp nhưng follow_up chứa clarification
  không rỗng; `parse_route` báo `Retrieval route requires query and no clarification`.
- Cách kiểm tra: script verify_routing_artifact chạy lại validator trên cả
  initial_text và retry_text, tái hiện đủ 6 lỗi hợp đồng của ba lượt fallback.
- Kết quả: xác nhận lỗi; task điều tra chưa sửa prompt/schema của ứng dụng.
- Phòng tránh đề xuất: schema có ràng buộc theo nhánh hoặc prompt retry chứa
  lỗi cụ thể và ví dụ JSON sửa; cần kiểm chứng model thật trước khi áp dụng.

## ERR-20261003-05

- Task: TASK-20261003-04.
- Triệu chứng: nhánh web `Qwen 2.5 7B + RAG` trả lỗi `SQLite objects created in
  a thread can only be used in that same thread`.
- Bối cảnh tái hiện: `Retriever` được tạo trong thread khởi động server, sau đó
  `ThreadingHTTPServer` xử lý `/api/chat` bằng thread worker và gọi `search()`.
- Nguyên nhân đã xác nhận: `sqlite3.connect` dùng mặc định
  `check_same_thread=True`, không phù hợp với vòng đời tài nguyên web hiện tại.
- Xử lý: mở database read-only với `check_same_thread=False`; bổ sung khóa nội bộ
  quanh toàn bộ `search()` và `close()` để tuần tự hóa encoder, FAISS và SQLite.
- Kết quả: test hồi quy tạo Retriever ở thread chính rồi truy hồi trong thread
  worker thành công; tổng cộng 20 test server/cấu hình/RAG đều đạt.
- Phòng tránh: mọi tài nguyên được tạo trước `ThreadingHTTPServer.serve_forever()`
  phải có hợp đồng thread rõ ràng và test gọi từ worker thread.

## ERR-20261003-04

- Task: TASK-20261003-03.
- Triệu chứng: lần chạy test đầu báo không tìm thấy package `vigovbot`; khi thêm
  `PYTHONPATH=src`, Python mặc định tiếp tục thiếu `filelock` và `yaml`.
- Bối cảnh tái hiện: chạy test bằng `python` hệ thống thay vì môi trường dự án.
- Nguyên nhân đã xác nhận: Python 3.14 mặc định chưa cài package/dependency dự án;
  workspace dùng virtual environment tại `env/`, không phải `.venv/`.
- Xử lý: chạy lại bằng `env\Scripts\python`.
- Kết quả: 19 test liên quan server, cấu hình và pipeline đều thành công.
- Phòng tránh: kiểm tra virtual environment có sẵn và dùng Python của môi trường
  dự án trước khi kết luận thiếu dependency.

## ERR-20261003-03

- Task: TASK-20261003-02.
- Triệu chứng: hai module test RAG không import được, `ModuleNotFoundError: No
  module named 'faiss'`.
- Bối cảnh tái hiện: chạy `python -m unittest tests.test_rag_config_cli
  tests.test_rag_pipeline -v`; workspace không có `.venv`, lệnh dùng Python 3.14
  mặc định.
- Nguyên nhân đã xác nhận: môi trường Python hiện tại chưa cài dependency
  `faiss-cpu` thuộc nhóm `rag`/`test`.
- Xử lý: không cài dependency vì task chỉ sửa tài liệu; chuyển sang kiểm tra tĩnh
  liên kết và `git diff --check`.
- Kết quả: kiểm thử ứng dụng chưa chạy được; lỗi không phát sinh từ thay đổi mã
  nguồn vì task không sửa code.
- Phòng tránh: dùng môi trường đã cài `.[test,dev]` hoặc `.[rag]` khi cần chạy bộ
  test RAG; không coi lỗi thiếu dependency là regression của ứng dụng.

## ERR-20261003-01

- Task: TASK-20261003-01.
- Triệu chứng: PowerShell in lỗi Set-PSReadLineOption về virtual terminal và
  invalid handle trước output của lệnh đọc file.
- Bối cảnh: exec_command dùng login mặc định, nạp PowerShell profile.
- Nguyên nhân: profile bật prediction của PSReadLine trong phiên không có
  terminal tương tác phù hợp; thông báo chỉ tới profile dòng 12–13.
- Xử lý: các lệnh tiếp theo dùng `login: false`.
- Kiểm chứng: lệnh đọc tài liệu và liệt kê skill sau đó không còn lỗi profile.
- Phòng tránh: dùng PowerShell không nạp profile cho lệnh agent không tương tác;
  không chỉnh profile cá nhân ngoài phạm vi task.

## ERR-20261003-02

- Task: TASK-20261003-01.
- Triệu chứng: quick_validate.py thất bại với `ModuleNotFoundError: No module named 'yaml'`.
- Tái hiện: chạy validator bằng Python mặc định cho một trong hai skill mới.
- Nguyên nhân: Python mặc định không có PyYAML mà validator import.
- Xử lý: cài PyYAML bằng pip --target vào thư mục tạm riêng; đặt PYTHONPATH và
  PYTHONUTF8 trong process kiểm chứng rồi chạy lại validator.
- Kết quả: cả hai skill đều trả `Skill is valid!`, exit code 0.
- Phòng tránh: kiểm tra dependency của công cụ validator; dùng môi trường riêng,
  không thêm dependency tooling vào ứng dụng chỉ để kiểm tra Markdown.

## ERR-20261004-01 — TASK-20261004-01: generation sai hợp đồng

- Bằng chứng: ZIP thứ hai có 4 lỗi `Evidence status and action do not match`
  (000033, 000084, 000211, 000271), gây 7 lượt free-running bị chặn.
- Nguyên nhân xác nhận ở code: generation chỉ dùng JSON mode, không ràng buộc
  cặp evidence/action, không retry; runner không lưu raw generation lỗi.
  Artifact không đủ để biết chính xác trường thiếu/sai của từng lượt.
- Sửa: schema theo cặp, giữ validator, retry một lần có budget; lưu diagnostics
  và blocked_by_id. Kiểm thử tái hiện JSON thiếu/sai/cắt dở, sửa thành công hoặc
  vẫn lỗi đều đạt. Giữ việc chặn chuỗi đã lỗi để không làm sai free_running.

## ERR-20261004-02 — TASK-20261004-01: lỗi ngữ nghĩa trong mẫu mới

- 000142 suy diễn trạng thái cá nhân từ quy trình; 000141 bỏ một phần câu hỏi;
  các ca 000059/000263 out_of_scope sai, 000072/000180 chọn thủ tục khi mơ hồ.
- Biện pháp: điều chỉnh prompt và giữ câu hỏi gốc cùng query đã viết lại.
- Chưa xác nhận hiệu quả bằng model thật: localhost:11434 từ chối kết nối;
  không có log Colab để xác định nguyên nhân artifact chỉ chứa 23 lượt.
- Báo cáo chi tiết: colab-rag-2-assessment.md; cần smoke lại, không tuyên bố
  các lỗi nội dung đã hết từ kiểm thử mock hoặc action accuracy.

## ERR-20261004-03 — TASK-20261004-03

- Bối cảnh: kiểm tra artifact theo đường dẫn người dùng gọi output/result_qa và in dữ liệu tiếng Việt bằng Python.
- Triệu chứng: đường dẫn không tồn tại; PowerShell profile báo PSReadLine khi redirect; Python stdout cp1252 gây UnicodeEncodeError; một truy vấn rg dùng glob đường dẫn Windows không hợp lệ.
- Xác nhận/sửa: thư mục thực là outputs/result_qa; dùng login=false, PYTHONIOENCODING=utf-8 và tìm trên đường dẫn thư mục với glob file. Các lần đọc tiếp theo thành công, dữ liệu gốc không bị sửa.
- Tránh lặp: xác nhận tên thư mục và encoding trước khi đọc artifact Unicode.
- Lỗi artifact quan sát riêng: single_0445 StructuredAnswerError sau 2 lần sinh JSON; chưa sửa runtime, chi tiết và giả thuyết cắt token nằm trong báo cáo.
