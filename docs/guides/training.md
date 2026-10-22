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
## Tạo SFT từ Golden train/validation

Từ gốc repository, chạy `vigov data golden-to-sft`. Có thể chỉ định
`--source-dir Data/golden_dataset --output-dir Data/golden_dataset_sft`.
Lệnh tạo `train_sft.jsonl` và `validation_sft.jsonl`, giữ nguyên ID, thứ tự và
Unicode: `messages = chat_history + user(question) + assistant(expected_answer)`.
Không thêm context, system prompt hoặc nhãn; giữ cả ca unanswerable.

Cả hai split được kiểm tra bằng validator training trước khi ghi. Lỗi dữ liệu
báo file/dòng/test_id; ID trùng trong hoặc giữa split đều bị chặn. Lệnh có thể
chạy lại với cùng input để kiểm chứng byte; từ chối ghi đè artifact khác nội dung.
Không đọc test để chuyển đổi, không tạo `test_sft.jsonl` và không sửa cấu hình
training. Dùng profile `configs/training/experiments/golden_sft.yaml` cho hai artifact này.

## Training với Golden SFT

Profile Golden kế thừa thông số QLoRA từ base và đặt `data.splits.test: null`
để bỏ test cũ. Train/validation bắt buộc; test có thể bỏ hoặc đặt null. Nếu
khai báo đường dẫn test thì file vẫn phải hợp lệ. Profile ba split cũ giữ nguyên.

```powershell
vigov data check --config configs/training/experiments/golden_sft.yaml
vigov train start --config configs/training/experiments/golden_sft.yaml --run-id golden-sft-HOST-DATE
```

Lệnh start cần môi trường GPU phù hợp; kiểm tra tokenizer/max_seq_length và GPU
smoke trước full run. Profile không tự cấp quyền train qua execution.approved.
Chọn run mới khi đổi dataset; không resume checkpoint bộ cũ. Hash/snapshot chỉ
ghi các split đã cấu hình, và resume vẫn yêu cầu khớp chính xác config/hash.
Đánh giá cuối trên `test_golden.jsonl` qua `vigov eva run-v2`/`export-v2` theo
[hướng dẫn evaluation](qa-rag-evaluation.md). Evaluator SFT `--split test` báo lỗi
rõ ràng nếu run không khai báo test; không dùng validation thay test.
