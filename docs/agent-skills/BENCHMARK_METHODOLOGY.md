# Phương pháp benchmark usage

So sánh `baseline` và `skills` trên cùng task set, revision, model, reasoning
effort, quyền tool và môi trường. Counterbalance thứ tự. Mỗi JSONL run cần
`task_id`, `condition`, `completed`; thêm token usage, elapsed, turns, rework và
test khi đo được. Không dùng độ dài chữ làm token.

Chấm completion bằng rubric cố định, review mù nếu có người đánh giá. Báo matched
pairs, invalid runs, sample size và uncertainty; không kết luận causal từ ít mẫu.

```powershell
python .agents\skills\usage-benchmark\scripts\summarize_benchmark.py runs.jsonl
```

Script giữ `null` cho metric thiếu; không tự gọi dịch vụ hoặc tạo số liệu.
