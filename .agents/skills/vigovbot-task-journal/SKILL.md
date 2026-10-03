---
name: vigovbot-task-journal
description: Maintain Vietnamese requirements, implementation history, current stage and failure journal for substantial tasks in the ViGovBot repository. Use for multi-step changes, investigations and pipeline work; skip trivial edits unless requested.
---

# Nhật ký task ViGovBot

Áp dụng trong repository ViGovBot, không ghi hồ sơ của dự án khác vào đây.
Đọc `docs/project/current-stage.md` và các mục liên quan trước khi làm.
Đường dẫn dưới đây tính từ gốc repository.

## Hồ sơ

- `docs/project/requests.md`: thêm ID `TASK-YYYYMMDD-NN`, ngày theo Asia/Saigon,
  yêu cầu người dùng, phạm vi, tiêu chí hoàn thành, giả định và trạng thái.
  Giữ yêu cầu gốc; ghi bổ sung nếu người dùng đổi phạm vi.
- `docs/project/implementation-history.md`: thêm mục theo ID task, nêu hành vi
  thay đổi, file liên quan, quyết định có ảnh hưởng, lệnh kiểm chứng, kết quả
  thực tế và phần chưa kiểm chứng. Không chép toàn bộ diff hoặc log.
- `docs/project/current-stage.md`: cập nhật ảnh chụp hiện tại gồm task đang làm,
  giai đoạn, việc đã xong, việc còn lại, trở ngại, bước tiếp theo và bằng chứng.
  Khi tiếp tục phiên cũ, kiểm tra hồ sơ và artifact trước khi chạy lại.
- `docs/project/failure-journal.md`: thêm `ERR-YYYYMMDD-NN`, ID task, triệu chứng,
  lệnh/bối cảnh tái hiện, nguyên nhân đã xác nhận hoặc giả thuyết, cách thử sửa,
  kết quả kiểm chứng và cách tránh lặp lại. Ghi cả lỗi công cụ/môi trường ảnh
  hưởng công việc. Không tạo lỗi giả khi không có lỗi.

## Mốc cập nhật

Tạo yêu cầu và đánh dấu `in_progress` trước khi triển khai. Cập nhật stage khi
đổi giai đoạn, có trở ngại hoặc chuẩn bị chạy công việc dài. Lưu lỗi sau khi có
đủ dữ kiện; ghi rõ thử sửa chưa thành công. Trước trả lời cuối, ghi triển khai,
kiểm chứng, stage và trạng thái `completed`, `partial` hoặc `blocked` đúng thực tế.
Không đánh dấu completed nếu tiêu chí còn thiếu; nêu việc còn lại và lý do.

Giữ lịch sử cũ, chỉ bổ sung kết quả mới hoặc chỉnh sai sót có giải thích.
Không lưu API key, dữ liệu cá nhân, nội dung .env hay log thô lớn. Dùng đường dẫn
artifact và trích đoạn lỗi đã loại bí mật. Cập nhật roadmap/README nếu task làm
thay đổi nội dung ở đó; current-stage theo dõi task, không thay thế roadmap.
Trả lời cuối nêu kết quả, kiểm chứng và liên kết hồ sơ; chỉ đề xuất commit nếu phù hợp.
