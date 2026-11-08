# Kiểm tra sẵn sàng trước khi chạy web

Mọi lần chạy web bằng CLI đều thực hiện preflight nhẹ trước khi nạp corpus và
model. Preflight phân biệt thành phần bắt buộc với model tùy chọn: thiếu model
Ollama, QLoRA hoặc backend web riêng chỉ tạo `WARN`, không chặn giao diện web.

## Chạy kiểm tra độc lập

Trên môi trường native đã cài ViGovBot:

```powershell
python -m pip install -e ".[rag,phobert]"
vigov web-check --config configs/rag/inference.yaml --host 127.0.0.1 --port 8000
```

Nếu chỉ muốn kiểm tra file và môi trường, không gọi Ollama/API model:

```powershell
vigov web-check --config configs/rag/inference.yaml --no-service-probe
```

Với Docker sau khi đã build image:

```powershell
docker compose run --rm --no-deps web `
  vigov web-check `
  --config configs/rag/inference-docker-ollama.yaml `
  --host 0.0.0.0 `
  --port 8000
```

## Quy tắc PASS, WARN và FAIL

Preflight trả exit code `2` khi có `FAIL` bắt buộc. Các kiểm tra bắt buộc gồm:

- cấu hình RAG hợp lệ;
- dependency Python cần cho web/RAG;
- index, metadata và manifest của corpus vector;
- quyền ghi vào vị trí cache RAG;
- sáu file PhoBERT khi cấu hình bật router PhoBERT;
- cổng web chưa bị chiếm.

Các mục sau là tùy chọn và chỉ tạo `WARN`:

- `embedding.device = cuda` nhưng CUDA không khả dụng — embedding fallback về CPU, web vẫn chạy được;
- Ollama chưa chạy;
- một hoặc nhiều model Ollama chưa được cài;
- adapter `local_transformers` chưa có;
- API key của backend tương thích OpenAI chưa được đặt.

Vì vậy web vẫn được phép khởi động khi thiếu model tùy chọn. Model đó sẽ không
trả lời thành công cho đến khi backend tương ứng sẵn sàng.

Preflight chỉ kiểm tra nhanh cấu trúc manifest và sự hiện diện của file corpus.
Khi web thực sự khởi động, pipeline tiếp tục kiểm tra toàn bộ checksum index và
metadata, nạp PhoBERT, BGE-M3 cùng tokenizer. Bước đầy đủ này vẫn có thể dừng
startup nếu artifact bị hỏng dù preflight nhanh đã `PASS`.

## Khởi động web

Không cần gọi hai lệnh trong vận hành thông thường vì `vigov web` tự chạy
preflight trước:

```powershell
vigov web --config configs/rag/inference.yaml --host 127.0.0.1 --port 8000
```

Nếu báo thiếu vector hoặc PhoBERT, tạo/phục hồi trước:

```powershell
vigov data embed outputs/metadata --output-dir Data/vector/unified
python recovery/phobert/restore.py
```
