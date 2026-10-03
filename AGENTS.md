# Hướng dẫn agent cho ViGovBot

## Task lớn và bộ nhớ dự án

Với task nhiều bước, thay đổi hành vi/kiến trúc/cấu hình/dữ liệu, điều tra lỗi hoặc
chạy pipeline lâu, đọc và áp dụng
[vigovbot-task-journal](.agents/skills/vigovbot-task-journal/SKILL.md).
Task sửa typo hoặc chỉnh nhỏ một chỗ không cần lập hồ sơ riêng, trừ khi người dùng yêu cầu.

Ghi yêu cầu trước khi triển khai; cập nhật giai đoạn ở các mốc có ý nghĩa; lưu
thay đổi, kiểm chứng và lỗi thực tế trước khi kết thúc. Viết bằng tiếng Việt.
Không suy diễn trạng thái hoàn tất từ kế hoạch hoặc tài liệu cũ.

## Lệnh chạy lâu

Áp dụng [vigovbot-long-running-commands](.agents/skills/vigovbot-long-running-commands/SKILL.md)
khi cài dependency, tải model, tạo embedding, benchmark hoặc chạy lệnh lâu.
Ưu tiên thông báo hoàn tất và chờ theo session; không liên tục đọc/tail log.
Chỉ đọc phần log cần thiết sau khi lệnh kết thúc hoặc có lỗi/timeout cụ thể.
Giữ khả năng tiếp nhận yêu cầu mới; các cập nhật ngắn cho người dùng không cần đọc log.
