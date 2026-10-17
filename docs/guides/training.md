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

## Schema và model thử nghiệm

Training config được kiểm tra bởi Pydantic trong `training/schema.py`:
field sai tên/type bị từ chối; kiểm tra NF4, double quantization, target modules,
cadence và early stopping vẫn giữ. `load_config()` trả dict tương thích và
không chèn default vào snapshot cũ để tránh thay hợp đồng resume.

Model mặc định vẫn là Qwen/Qwen2.5-7B-Instruct. Với model khác, đặt đồng thời:

```yaml
model:
  name: Qwen/Qwen2.5-1.5B-Instruct
  experimental: true
```

Dùng trong YAML kế thừa base hoặc truyền `--set model.name=...` cùng
`--set model.experimental=true` ở lệnh hỗ trợ overrides. Chọn target_modules
phù hợp kiến trúc, tokenizer phải có chat template tương thích assistant masking,
model phải hỗ trợ causal LM/PEFT/NF4. `trust_remote_code` vẫn false. Model cần
remote code không được bật ngầm. Schema pass chỉ xác nhận cấu hình; cần smoke
riêng trên phần cứng mục tiêu trước khi kết luận model hoạt động. Không resume
checkpoint của model cũ sang model mới; chọn run mới.
