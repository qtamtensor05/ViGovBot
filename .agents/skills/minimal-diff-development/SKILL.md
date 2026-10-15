---
name: minimal-diff-development
description: Implement the smallest coherent code change that satisfies a request while preserving contracts and unrelated work. Use for scoped fixes and features; not for an explicitly requested broad refactor.
---

# Minimal Diff Development

Giới hạn diff nhưng vẫn sửa đúng root cause.

## Hợp đồng

- Input: Yêu cầu, acceptance criteria, current diff/status và public contracts liên quan.
- Output: Patch nhỏ nhất, danh sách file, contract preserved/changed, verification và scope expansion warning.

## Quy trình

+1. Chụp `git status` và khoanh vùng callers/tests.\n2. Giữ API/config/path tương thích trừ khi yêu cầu đổi.\n3. Không format/refactor file ngoài phạm vi.\n4. Review `git diff --stat`, diff nội dung và untracked files trước bàn giao.

## Ví dụ

Yêu cầu phù hợp: "implement this change with a minimal diff." Thực hiện quy trình trên và báo rõ bằng chứng.

## Giới hạn và kiểm chứng

Không dùng minimality để né test hay giữ workaround sai. Cảnh báo trước nếu root cause buộc chạm nhiều module. Kiểm chứng bằng scenario tương ứng trong
`docs/agent-skills/TEST_REPORT.md`; nếu có script, chạy cả fixture hợp lệ và input lỗi.
