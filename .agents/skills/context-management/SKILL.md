---
name: context-management
description: Select task-relevant repository context with progressive disclosure. Use for non-trivial repository work where broad reading would add noise; not for a single known-file edit.
---

# Context Management

Giữ context đủ để quyết định, không đọc tràn lan.

## Hợp đồng

- Input: Mục tiêu, workspace, file/entry point đã biết và acceptance criteria.
- Output: Context map gồm entry points, files cần đọc, references hoãn tải và giả định cần xác minh.

## Quy trình

+1. Bắt đầu từ AGENTS, task request, entry point và `rg` references.\n2. Mở file theo dependency gần nhất; chỉ tải reference khi nhánh quyết định cần.\n3. Tái dùng nội dung còn hiệu lực; refresh phần dễ drift.\n4. Mở rộng phạm vi khi evidence cho thấy cross-module impact.

## Ví dụ

Yêu cầu phù hợp: "scope context for this repository task." Thực hiện quy trình trên và báo rõ bằng chứng.

## Giới hạn và kiểm chứng

Không bỏ qua file cần thiết chỉ để giảm token. Không dùng cho câu hỏi tự chứa hoặc edit một file đã xác định. Kiểm chứng bằng scenario tương ứng trong
`docs/agent-skills/TEST_REPORT.md`; nếu có script, chạy cả fixture hợp lệ và input lỗi.
