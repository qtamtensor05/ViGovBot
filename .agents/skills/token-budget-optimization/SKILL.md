---
name: token-budget-optimization
description: Choose a context and output strategy proportional to task complexity while preserving correctness. Use when token cost or context size is a stated concern or a large task needs deliberate budgeting.
---

# Token Budget Optimization

Tối ưu có đo lường, không tuyên bố tiết kiệm giả.

## Hợp đồng

- Input: Loại task, giới hạn context/token nếu có, nguồn cần thiết và telemetry khả dụng.
- Output: Chiến lược simple/medium/complex, dữ liệu giữ/bỏ, log summary và số đo chỉ khi provider cung cấp.

## Quy trình

+1. Phân loại task theo số module, rủi ro và nhu cầu xác minh.\n2. Batch search/read độc lập; giới hạn log tại nguồn; ưu tiên diff và structured summary.\n3. Chỉ tải skill reference liên quan.\n4. Nếu không có token telemetry, chỉ mô tả biện pháp chứ không báo phần trăm tiết kiệm.

## Ví dụ

Yêu cầu phù hợp: "optimize the context budget." Thực hiện quy trình trên và báo rõ bằng chứng.

## Giới hạn và kiểm chứng

Không cắt evidence, error context hoặc tests cần thiết. Không dùng character count thay actual tokenizer. Kiểm chứng bằng scenario tương ứng trong
`docs/agent-skills/TEST_REPORT.md`; nếu có script, chạy cả fixture hợp lệ và input lỗi.
