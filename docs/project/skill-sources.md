# Nguồn skill agent

Đã kiểm tra ngày 2026-10-03.

| Nguồn | Mục đích |
|---|---|
| [OpenAI skills](https://github.com/openai/skills) | Catalog skill cho Codex; đã lấy danh sách curated bằng skill-installer |
| [Anthropic skills](https://github.com/anthropics/skills) | Tham khảo các skill và cách đóng gói từ nhà phát hành |
| [Agent Skills specification](https://agentskills.io/specification) | Chuẩn SKILL.md, frontmatter và cấu trúc resources |

Hai skill riêng được viết cho yêu cầu ViGovBot, không sao chép hoặc cài hàng
loạt skill không liên quan. Nguồn bổ sung để cân nhắc theo task: `jupyter-notebook`
cho notebook, `pdf` cho tài liệu PDF và `playwright` cho kiểm chứng web UI trong
catalog OpenAI. Chưa cài các skill này vì task hiện tại chỉ cần quy trình ghi hồ
sơ và chờ lệnh. Skill tải ngoài cần đọc nội dung và script trước khi sử dụng.
