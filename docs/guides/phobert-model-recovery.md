# Phục hồi PhoBERT router trên máy mới

PhoBERT v3 trong ViGovBot là checkpoint hoàn chỉnh, không phải adapter như QLoRA.
Gói cần chuyển máy gồm sáu tệp trong
`recovery/phobert/checkpoint/` và có kích thước khoảng
542 MB. Gói đã chứa encoder, bốn head, tokenizer và metadata, nên không tải model nền,
không merge và không tạo GGUF.

## Chuẩn bị

1. Clone repository và cài dependency của ViGovBot.
2. Chép nguyên bundle vào `recovery/phobert/`, gồm `restore.py`, `manifest.json`
   và thư mục `checkpoint/`.
3. Không commit checkpoint vào Git thường vì toàn bộ `model/` đã được ignore. Dùng ổ lưu
   trữ model, Git LFS hoặc artifact registry nếu cần chia sẻ nội bộ.

## Khôi phục

```bash
vigov train restore-phobert
```

Hoặc gọi trực tiếp script recovery từ repository:

```bash
python recovery/phobert/restore.py
```

Có thể chỉ xác minh bundle mà chưa sao chép:

```bash
vigov train restore-phobert --dry-run
```

Để dùng bundle hoặc đích khác:

```bash
vigov train restore-phobert \
  --bundle-dir D:/model-store/phobert-v3/checkpoint \
  --output-dir model/phobert_v3_finetuned_20261028/runtime/checkpoint
```

Toàn bộ logic, manifest và checkpoint nằm trong `recovery/phobert/`; CLI gọi
trực tiếp script của bundle. Lệnh phục hồi
không ghi đè runtime hiện có; muốn phục hồi lại phải chủ động di chuyển hoặc xóa đúng
thư mục runtime trước khi chạy.

Sau khi hoàn tất, cấu hình RAG nạp checkpoint từ
`model/phobert_v3_finetuned_20261028/runtime/checkpoint/`. Lệnh không tự chạy khi khởi
động hệ thống: cần chạy một lần trên máy mới trước khi khởi động ViGovBot.
