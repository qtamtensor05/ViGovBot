---
name: context-handoff
description: Create a concise, secret-safe handoff for continuing repository work in another Codex session. Use at pauses, context boundaries or explicit handoff requests.
---

# Context Handoff

Tóm tắt đủ để tiếp tục mà không lặp audit.

## Hợp đồng

- Input: Mục tiêu, status, decisions, changed files, tests, errors, artifacts và next step.
- Output: Handoff ngắn gồm verified facts, unverified boundaries, blockers, exact next actions và no secrets.

## Quy trình

+1. Nêu objective và latest user scope.\n2. Tách completed/in-progress/not-run; liệt kê file và command quan trọng.\n3. Ghi quyết định cùng lý do, lỗi còn mở và cách tái hiện tối thiểu.\n4. Loại API key, env value, PII và log thô.

## Ví dụ

Yêu cầu phù hợp: "prepare a handoff for the next session." Thực hiện quy trình trên và báo rõ bằng chứng.

## Giới hạn và kiểm chứng

Không dùng handoff thay project documentation khi task yêu cầu nhật ký bền vững. Không suy đoán trạng thái. Kiểm chứng bằng scenario tương ứng trong
`docs/agent-skills/TEST_REPORT.md`; nếu có script, chạy cả fixture hợp lệ và input lỗi.
