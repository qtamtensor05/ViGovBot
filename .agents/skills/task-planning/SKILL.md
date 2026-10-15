---
name: task-planning
description: Plan complex repository work as verifiable phases with dependencies and acceptance criteria. Use for multi-step, risky or long-running tasks; skip simple one-step edits.
---

# Task Planning

Lập kế hoạch vừa đủ và cập nhật theo bằng chứng.

## Hợp đồng

- Input: Mục tiêu, constraint, known state, acceptance criteria và quyền hành động.
- Output: Các phase có dependency, gate kiểm chứng, trạng thái và stopping condition.

## Quy trình

+1. Audit trước khi quyết định kiến trúc.\n2. Chia bước theo artifact có thể kiểm chứng, không theo mô tả mơ hồ.\n3. Gắn acceptance test và rủi ro cho mỗi phase; nhận diện lệnh dài.\n4. Cập nhật khi evidence thay đổi, không giữ kế hoạch đã lỗi thời.

## Ví dụ

Yêu cầu phù hợp: "plan this complex repository task." Thực hiện quy trình trên và báo rõ bằng chứng.

## Giới hạn và kiểm chứng

Không tạo kế hoạch dài cho typo hoặc thay đổi đơn lẻ. Kế hoạch không phải bằng chứng hoàn thành. Kiểm chứng bằng scenario tương ứng trong
`docs/agent-skills/TEST_REPORT.md`; nếu có script, chạy cả fixture hợp lệ và input lỗi.
