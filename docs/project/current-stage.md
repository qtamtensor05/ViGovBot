# Current stage — giai đoạn hiện tại

- Cập nhật: 2026-10-03 (Asia/Saigon).
- Task: TASK-20261003-02.
- Giai đoạn: hoàn tất TASK-20261003-02.
- Đã làm: cập nhật hướng dẫn triển khai theo router nhiều lượt, xét bằng chứng,
  CLI history, web API/UI nhiều model và giới hạn hiện tại; bỏ liên kết hỏng.
- Còn lại: không còn hạng mục thuộc yêu cầu hiện tại.
- Trở ngại: chưa ghi nhận trở ngại ngăn hoàn tất task.
- Bước tiếp theo: task lớn tiếp theo tạo ID mới và cập nhật các hồ sơ này.
- Bằng chứng: 16 liên kết tương đối đều có đích; `git diff --check` thành công.
  Unit test RAG chưa chạy do Python hiện tại thiếu `faiss` (ERR-20261003-03).
  Không chạy model, corpus hoặc web server thật vì chỉ thay đổi tài liệu.
- Trạng thái ứng dụng: tài liệu triển khai đã đối chiếu trực tiếp với mã nguồn;
  README/roadmap ngoài phạm vi task có thể còn mô tả trạng thái không đồng nhất.
