# Cài đặt trên Windows 11

## Repository

Giữ nguyên cây `.agents/skills/`, mở Codex tại gốc dự án và bắt đầu phiên mới để
refresh discovery. Trước cập nhật kiểm tra `Get-ChildItem .agents\skills -Directory`
và `git status --short`; không ghi đè thư mục cùng tên.

## Global Codex

Chỉ copy skill thực sự dùng sang `$env:CODEX_HOME\skills` hoặc
`$HOME\.codex\skills` khi chưa đặt biến. So sánh `SKILL.md` trước khi copy.
Skill ViGovBot mặc định nên repo-local vì phụ thuộc cấu trúc dự án.

## Cập nhật và gỡ

Cập nhật qua Git để review diff. Gỡ đúng thư mục đã xác nhận không phải
symlink/shared copy, rồi mở phiên mới. Ba script chỉ dùng Python standard library.
