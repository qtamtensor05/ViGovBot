# Vận hành full QLoRA độc lập trên Windows

Bộ script này chạy QLoRA trong worker PowerShell độc lập. Sau khi lệnh start trả
về, có thể đóng Codex/ChatGPT; không đóng máy, đăng xuất Windows hoặc kết thúc PID
worker/training. Script không đổi hyperparameter và không tự restart khi CUDA OOM.

## Start

Mở PowerShell tại gốc repository:

```powershell
.\scripts\start_qlora.ps1
```

Trước khi chạy, script dùng `.venv-qlora`, validate
`configs/training/environments/rtx5060ti_16gb.yaml`, CUDA, ba split dữ liệu và config. Nó từ chối
nếu phát hiện QLoRA run khác, tạo run ID duy nhất và lưu:

- artifact Trainer: `outputs/qlora/<run-id>/`;
- stdout/stderr/exit code/PID: `outputs/qlora/control/runs/<run-id>/<attempt-id>/`;
- active pointer: `outputs/qlora/control/active_run.json`.

Model dùng cache chuẩn của Hugging Face. `from_pretrained` chỉ tải file thiếu hoặc
revision chưa có; script không xóa cache và không ép tải lại.

Kiểm tra trước mà không khởi chạy process:

```powershell
.\scripts\start_qlora.ps1 -DryRun
```

## Status

```powershell
.\scripts\status_qlora.ps1
```

Run cũ cụ thể:

```powershell
.\scripts\status_qlora.ps1 -RunId "<run-id>"
```

Status hiển thị PID worker/training, exit code, step hiện tại/tổng dự kiến, epoch,
loss train/validation/best, elapsed, ETA, GPU utilization và VRAM. Trước log event
đầu tiên, loss/epoch/ETA có thể là `unavailable`; đó không phải dữ liệu giả.

## TensorBoard

```powershell
.\scripts\start_tensorboard.ps1
```

Mở `http://localhost:6006`. Dùng `-NoBrowser` nếu không muốn tự mở trình duyệt.
Trainer và callback ghi train loss, validation loss, learning rate, gradient norm,
global step, epoch, GPU allocated/reserved và peak memory trong lúc chạy.

## Stop an toàn

```powershell
.\scripts\stop_qlora.ps1
```

Script xác minh đúng PID/command line rồi tạo stop request. Trainer nhận request ở
cuối optimizer step kế tiếp, yêu cầu save checkpoint và dừng. Mặc định script chờ
tối đa 300 giây và không kill nếu hết timeout. Nó chỉ tuyên bố có checkpoint mới
khi xác minh directory `checkpoint-*` được tạo/cập nhật sau stop request.

Force stop chỉ dùng khi chấp nhận mất tiến độ sau checkpoint gần nhất:

```powershell
.\scripts\stop_qlora.ps1 -TimeoutSeconds 300 -ForceAfterTimeout
```

Checkpoint không bị xóa trong cả hai chế độ.

## Resume

Chỉ định checkpoint đã có đủ adapter/optimizer/scheduler/RNG/trainer/callback state:

```powershell
.\scripts\start_qlora.ps1 -Resume ".\outputs\qlora\<run-id>\checkpoints\checkpoint-<step>"
```

Script validate config snapshot và SHA-256 của dataset trước khi tạo worker.
Resume tiếp tục đúng run directory; không tạo hoặc ghi đè run khác.

## Plot và report sau khi kết thúc

Trước tiên kiểm tra `ProcessState=EXITED` và `ExitCode=0`:

```powershell
.\scripts\status_qlora.ps1 -RunId "<run-id>"
.\.venv-qlora\Scripts\python.exe -m training.evaluate --run_dir ".\outputs\qlora\<run-id>" --split test
.\.venv-qlora\Scripts\python.exe -m training.plot --run_dir ".\outputs\qlora\<run-id>"
.\.venv-qlora\Scripts\python.exe -m training.report --run_dir ".\outputs\qlora\<run-id>"
```

CUDA OOM hoặc lỗi khác được giữ trong `stderr.log` và `exit_code.txt`. Worker không
tự đổi batch/sequence/accumulation, không tự restart và không đánh dấu thành công
khi exit code khác 0.

## Đánh giá cùng benchmark Qwen base và RAG

Backend `--qlora-run-dir` dùng đúng query/history và scorer QA-v4 của hai run cũ.
Model không nhận reference answer, evidence hoặc nhãn hành vi trong prompt. QLoRA
chạy tuần tự trên một GPU (`--concurrency 1`); output mới không ghi đè artifact cũ.

```powershell
$runDir = ".\outputs\qlora\qlora-full-20261014-153839-desktop-7pkpjrj-ea78be2d"
$dataset = ".\Data\tthc_test_case_v1"
$pred = ".\outputs\tthc_test_case_v1\predictions_qwen_qlora.jsonl"
$score = ".\outputs\tthc_test_case_v1\scores_qwen_qlora.json"

.\.venv-qlora\Scripts\python.exe -m vigovbot qa-v4 run `
  --dataset $dataset --split test --mode reference_history --concurrency 1 `
  --batch-size 4 --verify-batch-equivalence 4 `
  --qlora-run-dir $runDir --out $pred

.\.venv-qlora\Scripts\python.exe -m vigovbot qa-v4 score `
  --dataset $dataset --split test --predictions $pred --lexical --bertscore `
  --bert-device cuda --bert-batch-size 16 --out $score
```

So sánh paired trên đúng benchmark:

```powershell
.\.venv-qlora\Scripts\python.exe -m vigovbot.qa_v4.compare `
  --left .\outputs\tthc_test_case_v1\scores_qwen_baseline_schema_c4.json `
  --right $score --out .\outputs\tthc_test_case_v1\base_vs_qlora.json

.\.venv-qlora\Scripts\python.exe -m vigovbot.qa_v4.compare `
  --left .\outputs\tthc_test_case_v1\scores_c4_full.json `
  --right $score --out .\outputs\tthc_test_case_v1\rag_vs_qlora.json
```

QLoRA được train để sinh câu trả lời assistant dạng văn bản, không sinh nhãn `action`.
Evaluator giữ nguyên output này và ghi action metric là unavailable, không ép JSON,
không retry và không suy đoán nhãn từ câu chữ. Các metric nội dung dùng chung vẫn so
sánh trực tiếp được. Recall/MRR chỉ có ý nghĩa cho RAG và cũng được ghi unavailable
cho QLoRA.

`--batch-size 4` là batching GPU thật, không phải nhiều thread cùng gọi model. Trước
khi tạo artifact, runner sinh đơn và sinh batch trên bốn mẫu rồi yêu cầu kết quả
khớp tuyệt đối; nếu khác, lệnh dừng và yêu cầu quay về batch 1. Smoke thật trên RTX
5060 Ti đạt 4/4, không OOM và phần chạy chính nhanh hơn batch 2 khoảng 1,44 lần.
