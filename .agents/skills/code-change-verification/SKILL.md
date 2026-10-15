---
name: code-change-verification
description: Select and run proportionate lint, type, unit, integration and regression checks for code changes. Use after implementation or when assessing readiness.
---

# Code Change Verification

Báo đúng phạm vi kiểm chứng.

## Hợp đồng

- Input: Diff hiện tại, test commands dự án, risk areas và môi trường khả dụng.
- Output: Lệnh đã chạy + exit/result, lệnh chưa chạy + lý do, regression risks và verdict có giới hạn.

## Quy trình

+1. Map file đổi sang test gần nhất; chạy targeted checks trước.\n2. Mở rộng full suite khi shared contract hoặc regression risk cao.\n3. Chạy static checks và `git diff --check`; kiểm tra artifact nếu behavior phụ thuộc artifact.\n4. Tách PASS, FAIL, SKIPPED, NOT VERIFIED.

## Ví dụ

Yêu cầu phù hợp: "verify these code changes." Thực hiện quy trình trên và báo rõ bằng chứng.

## Giới hạn và kiểm chứng

Không coi compile/help/mock là runtime end-to-end. Không nhận pass nếu command bị timeout hoặc output không đủ. Kiểm chứng bằng scenario tương ứng trong
`docs/agent-skills/TEST_REPORT.md`; nếu có script, chạy cả fixture hợp lệ và input lỗi.
