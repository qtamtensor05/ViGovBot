# Thiết lập GPU cho QLoRA

Không tự nâng Torch, CUDA, Transformers hoặc bitsandbytes trên môi trường đang
hoạt động. Chọn wheel Torch phù hợp driver trước, sau đó cài các phiên bản đã ghim:

```powershell
python -m venv .venv-qlora
.venv-qlora\Scripts\python -m pip install --upgrade pip setuptools wheel
# Cài wheel Torch phù hợp host theo tài liệu PyTorch chính thức.
.venv-qlora\Scripts\python -m pip install -e ".[training,gpu]"
.venv-qlora\Scripts\vigov doctor
.venv-qlora\Scripts\vigov gpu check
```

`vigov gpu check` kiểm tra CUDA, BF16, NF4 forward/backward và paged AdamW mà
không tải Qwen. Tiếp theo kiểm tra dữ liệu và command đã resolve:

```powershell
vigov data check --config configs/training/experiments/smoke.yaml
vigov train start --config configs/training/experiments/smoke.yaml --run-id smoke-HOST-DATE --dry-run
```

Chỉ bỏ `--dry-run` hoặc dùng `vigov train smoke ... --approve` sau khi hai gate
trên đạt. Xem [tài liệu QLoRA chi tiết](qlora-training.md) cho pin Windows/Linux.
