# Thay đổi hệ thống

## Rút gọn evidence có cấu trúc vượt ngân sách - 2026-10-25

### Mục tiêu

Không loại toàn bộ bảng hoặc giá trị JSON chỉ vì vượt `max_chunk_tokens`; giữ
phần bằng chứng hợp lệ trong prompt mà không cắt hỏng cấu trúc.

### Thực hiện

- Rút gọn bảng Markdown/HTML theo hàng hoàn chỉnh và JSON theo field/phần tử.
- Không thay đổi scalar hoặc giá trị trong ô; giữ giới hạn từng chunk, tổng
  context và trace phần nội dung thực tế đã dùng.

### Kết quả

Đã kiểm chứng bằng 11 test evidence chuyên biệt, full suite 238 test, Ruff,
compileall và `git diff --check`; 21 test dependency tùy chọn bị skip. Chưa chạy
tokenizer Qwen thật hoặc API generation vì môi trường Python hiện thiếu
Transformers/FAISS.

## Tách ngân sách context cho routing - 2026-10-25

### Mục tiêu

Giảm chi phí context và giới hạn đầu ra của lần gọi routing mà không thay đổi
ngân sách sinh câu trả lời.

### Thực hiện

- Thêm `llm.routing_num_ctx` và `llm.routing_num_predict`.
- Dùng ngân sách riêng cho payload và kiểm tra context của routing.
- Kiểm chứng cấu hình, hành vi routing và regression.

### Kết quả

Đã triển khai và kiểm chứng bằng 36 test routing, full suite 234 test và Ruff.
Chưa đo latency thực tế vì máy hiện không có Ollama hoặc Docker runtime hoạt động.

## Chuẩn hóa hồ sơ vận hành - 2026-10-25

### Mục tiêu

Giữ tài liệu triển khai ngắn gọn và chỉ cập nhật khi chỉnh sửa quan trọng ảnh
hưởng hệ thống hoặc vận hành.

### Thực hiện

- Đổi điều kiện kích hoạt `vigovbot-task-journal`.
- Chuẩn hóa hồ sơ theo `Mục tiêu - Thực hiện - Kết quả`.
- Hợp nhất lịch sử cũ, loại yêu cầu báo cáo, dọn dẹp và chỉnh sửa nhỏ.

### Kết quả

Hoàn tất ngày 2026-10-25.
