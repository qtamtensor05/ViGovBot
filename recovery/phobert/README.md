# PhoBERT recovery bundle

Giữ `restore.py`, `manifest.json` và thư mục `checkpoint/` cùng nhau. Trên máy
mới, đặt toàn bộ thư mục `recovery/` tại nơi muốn tạo cây `model/`, rồi chạy:

```powershell
python recovery/phobert/restore.py
```

Đầu ra được tạo tại
`model/phobert_v3_finetuned_20261028/runtime/checkpoint/`. Script kiểm tra SHA-256
trước và sau khi sao chép, đồng thời từ chối ghi đè runtime đã tồn tại.

`checkpoint/` chứa trọng số lớn và không được commit bằng Git thường.
