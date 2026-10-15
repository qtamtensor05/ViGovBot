---
name: repository-navigation
description: Find repository entry points, implementations, references and module dependencies efficiently. Use when the relevant code location is unknown or the repository is large.
---

# Repository Navigation

Điều hướng từ mục tiêu đến implementation.

## Hợp đồng

- Input: Tên behavior/symbol/command/path hoặc lỗi cần lần theo.
- Output: Bản đồ entry point → implementation → config/data → tests/docs với đường dẫn và khoảng trống.

## Quy trình

+1. Dùng `rg --files` và `rg` trước; đọc manifest/AGENTS gần phạm vi.\n2. Theo import, command registration, config loader và call sites.\n3. Với monorepo, xác định package boundary trước khi mở rộng.\n4. Dừng khi đủ evidence cho task và ghi phần chưa theo.

## Ví dụ

Yêu cầu phù hợp: "locate the implementation and callers." Thực hiện quy trình trên và báo rõ bằng chứng.

## Giới hạn và kiểm chứng

Không scan toàn bộ binary/artifact/generated directories. Không nhầm compatibility wrapper với implementation canonical. Kiểm chứng bằng scenario tương ứng trong
`docs/agent-skills/TEST_REPORT.md`; nếu có script, chạy cả fixture hợp lệ và input lỗi.
