# Phương pháp paired benchmark baseline-vs-skills

Mục tiêu là đo hiệu quả workflow, không chứng minh trước rằng skill tiết kiệm
token. Benchmark chỉ được chạy khi có quyền, telemetry thật và chi phí chấp nhận.

## Thiết kế

1. Khóa task set, acceptance rubric, repository revision, model, reasoning effort,
   context ban đầu, quyền tool, sandbox, môi trường và timeout.
2. Với mỗi task, chạy một baseline không có custom skill và một run có skill;
   counterbalance thứ tự giữa các cặp để giảm hiệu ứng cache/thứ tự.
3. Dùng workspace/worktree cô lập cho mỗi run. Không để artifact của run trước
   trở thành context ẩn cho run sau.
4. Chấm completion/test bằng cùng rubric; nếu có human review, ẩn condition.

Mỗi JSONL row cần `task_id`, `condition`, `completed`, `repo_revision`, `model`,
`reasoning_effort`; nên có provider `input_tokens`, `output_tokens`,
`cached_tokens`, `elapsed_seconds`, `turns`, `rework_count`, `tests_passed`,
`rerun_reason` và `invalid_reason`. Metric không có giữ `null`.

```powershell
python .agents\skills\usage-benchmark\scripts\summarize_benchmark.py runs.jsonl
```

Báo số cặp hợp lệ, paired differences, completion/test success, dispersion,
missing telemetry, reruns và uncertainty. Không dùng character/word count thay
token, không trộn model/environment khác nhau và không tuyên bố causal/savings từ
methodology hoặc dữ liệu synthetic. Task migration này chỉ kiểm thử script bằng
fixture; **benchmark usage thật: NOT VERIFIED / NOT RUN**.
