# QLoRA Qwen2.5-7B: local-first và GPU portable

Pipeline này tách hai ranh giới: máy local kiểm tra dữ liệu/cấu hình/logic
bằng CPU; máy Linux GPU mới nạp model 7B, smoke train và train thật. Không có
fallback ngầm từ QLoRA sang full fine-tuning.

## Cài đặt local

```powershell
python -m venv .venv-qlora
.venv-qlora\Scripts\python -m pip install -r requirements\qlora-base.txt
.venv-qlora\Scripts\python -m unittest tests.test_qlora_local tests.test_qlora_plot -v
.venv-qlora\Scripts\python -m training.validate_data --config configs/training/environments/local.yaml
```

Mặc định validator không nạp tokenizer. `--with-tokenizer` nạp official Qwen
tokenizer/chat template và có thể tải các file tokenizer nhỏ; nó không tải model 7B.
Dùng thêm `--local-files-only` để chỉ dùng tokenizer đã có trong cache.

## Chuyển sang máy GPU

Clone Git hoặc giải nén source archive. Không chép `.env`, `outputs`, checkpoint hay
token vào Git. Chuyển ba JSONL qua kênh riêng, rồi so hash:

```bash
sha256sum Data/tthc_test_case_v1/data/*_sft.jsonl
python -m training.validate_data --config configs/training/environments/gpu.yaml --with-tokenizer
```

Trên Linux, tạo venv, cài PyTorch wheel theo CUDA/driver từ trang PyTorch,
sau đó `pip install -r requirements/qlora-gpu.txt`. File pin là chiến lược
tái lập; nên xuất thêm `pip freeze` của máy train và lưu cùng run.

```bash
python -m training.preflight --config configs/training/environments/gpu.yaml
python -m training.train --config configs/training/experiments/smoke.yaml --approve --run-id smoke-HOST-DATE
python -m training.train --config configs/training/environments/gpu.yaml --approve --run-id experiment-001
python -m training.train --config configs/training/environments/gpu.yaml --approve --resume outputs/qlora/experiment-001/checkpoints/checkpoint-100
python -m training.evaluate --run_dir outputs/qlora/experiment-001 --split validation
python -m training.evaluate --run_dir outputs/qlora/experiment-001 --split test
python -m training.plot --run_dir outputs/qlora/experiment-001
python -m training.report --run_dir outputs/qlora/experiment-001
```

Preflight in GPU name, CUDA/version, VRAM, BF16, package compatibility, disk trống
và khoảng VRAM ước tính. Gợi ý không tự sửa hyperparameter; dùng
`--set training.per_device_train_batch_size=1` hoặc biến
`VIGOVBOT_QLORA__TRAINING__...` sau khi duyệt. OOM: giảm batch, sequence length
hoặc tăng accumulation minh bạch, chạy lại smoke, không đổi learning rate ngầm.

## Dữ liệu, loss và chọn model

Chat template Qwen được áp cho toàn bộ multi-turn. Label của user/template là
`-100`; chỉ token thuộc message assistant sinh loss. Mẫu bị cắt mất toàn bộ
target bị từ chối. Validation loss chọn checkpoint/early stop; test chỉ đánh giá
sau cùng. Perplexity = `exp(cross_entropy)`. Generalization gap = validation
token-loss trừ training token-loss tại các quan sát cuối.

Trainable % = LoRA trainable / tổng parameter PEFT. Reduction = 1 - tỉ lệ đó;
đây là giảm parameter huấn luyện, không phải nén toàn model. Baseline
memory FP16/BF16 = 2 byte/parameter; số QLoRA chỉ là estimate và loại trừ
activation/kernel/fragmentation. Adapter được lưu riêng trong `best_adapter/`.

## Tích hợp chatbot

`web.models[]` hỗ trợ provider `local_transformers`, `adapter_path` và
`load_in_4bit`. Để baseline, bỏ trống adapter; để fine-tuned, trỏ adapter
tương đối. Mặc định cache chỉ giữ một bản 7B, không merge adapter vào
quantized weights. API `/api/chat` và schema kết quả không thay đổi.

## Artifact và giới hạn metric

Run lưu config/environment/hash, log CSV, metrics, prediction JSONL, plots,
checkpoint và adapter. Plot chỉ vẽ điểm đã quan sát, không nội suy. Kiểm tra
procedure code/tiền/văn bản/cơ quan là rule-based; fabricated claim và refusal
cá nhân được ghi `unavailable` nếu không có evidence/nhãn tin cậy.

## Windows RTX 5060 Ti 16 GB đã kiểm chứng

Trên Windows 10 với driver NVIDIA 616.92, dùng Python 3.11 và wheel PyTorch
2.9.1 CUDA 13.0. Không cần cài CUDA Toolkit hệ thống vì wheel mang runtime cần
thiết. Driver phải đủ mới cho CUDA 13.0 và wheel phải có `sm_120`.

```powershell
py -3.11 -m venv .venv-qlora
.venv-qlora\Scripts\python -m pip install --upgrade pip setuptools wheel
.venv-qlora\Scripts\python -m pip install torch==2.9.1 `
  --index-url https://download.pytorch.org/whl/cu130
.venv-qlora\Scripts\python -m pip install -r requirements\qlora-windows-blackwell.txt -e .
.venv-qlora\Scripts\python -m pip check
.venv-qlora\Scripts\python -m training.gpu_diagnostics `
  --output outputs\qlora\gpu_environment_diagnostic.json
.venv-qlora\Scripts\python -m training.validate_data `
  --config configs\training\environments\rtx5060ti_16gb.yaml --with-tokenizer
.venv-qlora\Scripts\python -m training.preflight `
  --config configs\training\environments\rtx5060ti_16gb.yaml `
  --output outputs\qlora\preflight_rtx5060ti.json
```

Smoke và resume dùng config riêng, không đổi hyperparameter full-training:

```powershell
.venv-qlora\Scripts\python -m training.train `
  --config configs\training\experiments\smoke_rtx5060ti_16gb.yaml --approve --run-id smoke-HOST-DATE
.venv-qlora\Scripts\python -m training.train `
  --config configs\training\experiments\smoke_rtx5060ti_16gb.yaml --approve `
  --resume outputs\qlora\smoke-HOST-DATE\checkpoints\checkpoint-2
.venv-qlora\Scripts\python -m training.gpu_acceptance `
  --run_dir outputs\qlora\smoke-HOST-DATE
```

Kết quả smoke trên máy đã kiểm chứng không phải metric chất lượng model. Buffer
optimizer uint8 của bitsandbytes có thể không byte-identical sau resume; gate kiểm
step state, scheduler/RNG/callback, loss/gradient và adapter cuối so với run không
gián đoạn. Không đánh dấu sẵn sàng nếu adapter hoặc continuity khác.

Để vận hành full training độc lập với Codex/ChatGPT bằng PowerShell, xem
[Vận hành full QLoRA độc lập trên Windows](qlora-operations.md).
