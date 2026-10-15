# Xác minh nguồn Agent Skills

Kiểm tra trực tiếp ngày 2026-10-15. Không sao chép hoặc chạy script bên thứ ba.

| Nguồn chính thức | Nội dung đã áp dụng |
|---|---|
| [OpenAI skill-creator](https://github.com/openai/codex/blob/main/codex-rs/skills/src/assets/samples/skill-creator/SKILL.md) | `name`/`description` phân biệt, entrypoint ngắn, progressive disclosure, resource có mục đích, giữ invocation policy |
| [OpenAI Skills guide](https://developers.openai.com/api/docs/guides/tools-skills) | Skill là thư mục có `SKILL.md`; discovery dùng name/description; resource hỗ trợ workflow |
| [Rethinking skills and prompts for GPT-6 Astra](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra) | Giảm description rộng/trùng, tránh itinerary dư thừa, giữ `AGENTS.md` ngắn và conditional |
| [Using skills to accelerate OSS maintenance](https://developers.openai.com/blog/skills-agents-sdk) | Repo-local `.agents/skills`, trigger rõ, deterministic scripts và verification/handoff tách trách nhiệm |

## Môi trường và discovery

- `codex --version` trả `codex-cli 0.160.0`.
- Repository dùng `.agents/skills/<name>/SKILL.md`; không có `.codex/skills`.
- Global hiện có `C:\Users\quangTam\.codex\skills` (`.system` và
  `sales-project-progress`); không có `C:\Users\quangTam\.agents\skills`.
- Phiên Codex hiện tại đã liệt kê các repo-local skill ở `.agents/skills`, nên
  layout này là **VERIFIED trong phiên hiện tại**.
- Discovery/implicit routing của tên skill mới sau khi mở một phiên Codex hoàn
  toàn mới là **NOT VERIFIED** trong task này; validator/source test không thay
  thế được kiểm tra lifecycle đó.

Tài liệu OpenAI về API skill còn mô tả upload/versioning cho Responses/Agents
API; repository này không upload hosted skill nên không áp dụng các bước đó.
