# Lịch sử triển khai

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
