# Xác minh nguồn Agent Skills

Kiểm tra ngày 2026-10-15. Không chạy hoặc sao chép script bên thứ ba. Metadata
repository được đối chiếu qua GitHub API; thời điểm cập nhật không tự chứng minh chất lượng.

| Nguồn | Phân loại | License/bảo trì | Kết luận |
|---|---|---|---|
| [OpenAI Skills](https://github.com/openai/skills), [Codex Skills](https://developers.openai.com/codex/skills) | OFFICIAL | Catalog chính thức; license xét từng skill | Dùng chuẩn cấu trúc/discovery, không copy |
| [Agent Skills specification](https://agentskills.io) | OFFICIAL | Chuẩn manifest `SKILL.md` | Dùng frontmatter/progressive disclosure |
| [Anthropic Skills](https://github.com/anthropics/skills) | OFFICIAL với Claude | Repo hoạt động; license theo thư mục/notice | Tham khảo pattern, không coi Codex-native |
| [Vercel agent-skills](https://github.com/vercel-labs/agent-skills) | OFFICIAL với Vercel | Repo hoạt động; license xét từng phần | Không có bộ khớp toàn phạm vi |
| [Vercel skills CLI](https://github.com/vercel-labs/skills) | COMMUNITY_VERIFIED | MIT; hỗ trợ Codex | Công cụ phân phối tùy chọn |
| [NVIDIA rag-eval](https://github.com/NVIDIA/skills/blob/main/skills/rag-eval/SKILL.md) | COMMUNITY_VERIFIED | Apache-2.0; active | Tốt nhưng phụ thuộc NVIDIA Blueprint |
| [Claude Forge rag-retrieval](https://github.com/ArieGoldkin/claude-forge/blob/main/plugins/ai-toolkit/skills/rag-retrieval/SKILL.md) | REJECTED | MIT; Claude-specific | Không có artifact contract ViGovBot |
| [Vectara hallucination/eval](https://github.com/vectara/agent-skills/blob/main/skills/hallucination-and-eval/SKILL.md) | REJECTED | Chưa xác nhận license repo | Không đủ cơ sở tái sử dụng |

Toàn bộ 15 skill trong repository là `CUSTOM_REQUIRED`: dùng chuẩn chính thức
nhưng hợp đồng, ranh giới artifact và verification được viết riêng cho ViGovBot.
Không thêm dependency hoặc quyền thực thi từ nguồn bên thứ ba.
