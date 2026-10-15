---
name: usage-benchmark
description: Design and analyze controlled A/B benchmarks comparing Codex workflows with and without custom skills using provider telemetry. Use only when real comparable runs can be collected.
---

# Usage Benchmark

So sánh công bằng, không tạo số đo giả.

## Hợp đồng

- Input: Cùng task set, environment/model/settings, telemetry thực và scoring rubric.
- Output: Protocol, raw-run schema, matched-pair summary, uncertainty, invalid runs và conclusions bounded by data.

## Quy trình

+1. Khóa task set, model, effort, repo revision và tool permissions.\n2. Randomize/counterbalance condition order; giữ raw telemetry.\n3. Đo input/output/cached token khi provider cung cấp, elapsed time, turns, rework, tests và completion rubric.\n4. Dùng `scripts/summarize_benchmark.py`; không suy causal từ ít mẫu.

## Ví dụ

Yêu cầu phù hợp: "design a controlled skill benchmark." Thực hiện quy trình trên và báo rõ bằng chứng.

## Giới hạn và kiểm chứng

Không benchmark bằng text length, run giả hoặc điều kiện khác nhau. Không chạy workload tốn phí nếu chưa được phép. Kiểm chứng bằng scenario tương ứng trong
`docs/agent-skills/TEST_REPORT.md`; nếu có script, chạy cả fixture hợp lệ và input lỗi.
