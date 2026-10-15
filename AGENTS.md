# Hướng dẫn agent cho ViGovBot

## Chọn skill theo nhiệm vụ

Các skill nằm trực tiếp trong `.agents/skills/` để Codex discovery. Chọn một
skill chính theo outcome; chỉ thêm skill hỗ trợ khi trách nhiệm khác biệt rõ,
không tự tải toàn bộ catalog. Nhóm và điều kiện kích hoạt nằm tại
[`docs/agent-skills/SKILL_CATALOG.md`](docs/agent-skills/SKILL_CATALOG.md).

- RAG/chatbot: architecture, ingestion, retrieval, evaluation, dataset, API và security.
- Repository: dùng `context-navigation` khi chưa rõ vị trí hoặc task nhiều module;
  planning cho task phức tạp; minimal diff khi triển khai; verification trước
  bàn giao; handoff khi chuyển phiên.

Không gửi dữ liệu nhạy cảm ra dịch vụ ngoài, không chạy production/load test,
benchmark tốn phí hoặc script bên thứ ba khi chưa có phạm vi và quyền rõ ràng.

## Cấu trúc dự án

Khi thêm, di chuyển, đổi tên hoặc hợp nhất source, cấu hình, tài liệu, CLI hay
package, đọc và áp dụng
[vigovbot-project-structure](.agents/skills/vigovbot-project-structure/SKILL.md).
Không tạo cây song song ngoài cấu trúc canonical. README gốc chỉ giữ tổng quan
và quick start tối thiểu; hướng dẫn môi trường, câu lệnh đầy đủ, vận hành,
training/evaluation và troubleshooting phải nằm trong `docs/`.

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
