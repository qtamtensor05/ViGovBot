# Nhật ký vấp ngã

Chỉ ghi lỗi quan sát được; phân biệt nguyên nhân đã xác nhận với giả thuyết.

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
