# QLoRA v2 recovery bundle

Giữ `restore.py`, `manifest.yaml` và thư mục `adapter/` cùng nhau. Kiểm tra bundle
mà không tải hoặc merge model:

```powershell
python recovery/qlora_v2/restore.py --dry-run --allow-unpinned-revision
```

Phục hồi đầy đủ cần Qwen nền, đủ RAM/ổ đĩa và `llama.cpp`:

```powershell
python recovery/qlora_v2/restore.py `
  --llama-cpp-dir C:\tools\llama.cpp `
  --allow-unpinned-revision
```

GGUF Q8_0 và Modelfile cuối được tạo tại `model/qlora_v2/runtime/`. Thư mục
`adapter/` chứa trọng số lớn và không được commit bằng Git thường.
