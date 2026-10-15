# Vận hành huấn luyện QLoRA

## Smoke và full run

```powershell
vigov train smoke --config configs/training/experiments/smoke.yaml --run-id smoke-HOST-DATE --approve
vigov train start --config configs/training/environments/rtx5060ti_16gb.yaml --run-id qlora-HOST-DATE
```

`start` tạo worker độc lập với terminal/Codex, lưu PID, create-time, stdout,
stderr, config và run ID. Duplicate active worker bị từ chối.

```powershell
vigov train status --run-id <run-id>
vigov train logs --run-id <run-id> --lines 100
vigov train logs --run-id <run-id> --follow
vigov dashboard --run-id <run-id>
vigov train stop
vigov train resume <run-dir>/checkpoints/checkpoint-N --config <same-config>
```

Resume tiếp tục đúng run cũ và kiểm tra config/dataset hash cùng đầy đủ state
optimizer, scheduler, RNG, callback. Stop ghi yêu cầu graceful; chỉ dùng
`--force-after-timeout` khi chấp nhận rằng checkpoint mới có thể không tồn tại.

Run mới dùng `config.yaml`, `environment.json`, `dataset_report.json`, `state.json`
và các thư mục `logs/`, `checkpoints/`, `best_adapter/`, `metrics/`,
`predictions/`, `plots/`, `reports/`. Reader vẫn hỗ trợ layout phẳng lịch sử.
