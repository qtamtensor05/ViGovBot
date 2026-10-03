# Current stage — giai đoạn hiện tại

- Cập nhật: 2026-10-03 (Asia/Saigon).
- Task: TASK-20261003-07.
- Giai đoạn: hoàn tất TASK-20261003-07, bản sửa có trong mã nguồn.
- Lệnh smoke đã chạy: `env\Scripts\python scripts\smoke_routing_live.py oil`
  và cùng lệnh với `basic`; lần cuối cả hai nhóm exit 0.
- Artifact smoke: `outputs/qa_v4/routing_implemented_oil.json` và
  `outputs/qa_v4/routing_implemented_basic.json`.
- Đã làm: schema theo nhánh, prompt ví dụ, retry cụ thể, adapter provider,
  chẩn đoán web/debug và history fallback trung tính; pipeline version 4.
- Còn lại: không còn hạng mục thuộc yêu cầu hiện tại.
- Trở ngại: chưa ghi nhận trở ngại ngăn hoàn tất task.
- Bước tiếp theo: restart web để nạp mã mới, thử câu hỏi với corpus thật;
  benchmark rộng hơn hoặc kiểm chứng provider ngoài khi cần.
- Bằng chứng: 42 test offline đạt; Ruff/security/pip check đạt; smoke Qwen thật
  6/6 đúng nhãn và hợp lệ ở lần đầu, không fallback; artifact có model digest.
- Trạng thái ứng dụng: đã triển khai và kiểm chứng routing; chưa restart web,
  chưa kiểm chứng đáp án corpus thật hoặc API OpenAI-compatible thật.
- Lỗi thực tế: một HTTP 500 Ollama chưa xác định nguyên nhân; các lượt sau đạt,
  không có trở ngại hiện tại, xem ERR-20261003-09.
