# Chạy ViGovBot bằng Docker Desktop

Luồng Docker gồm web ViGovBot và Ollama trong hai container. Ollama lưu model
trong volume `ollama-models`; web lưu cache RAG trong volume `rag-cache`. Cấu
hình local `configs/rag/inference.yaml` không thay đổi; container dùng
`configs/rag/inference-docker.yaml` với endpoint `http://ollama:11434`.

Đây là runtime mặc định và bắt buộc cho web, Base/RAG/QLoRA và các lệnh kiểm tra
cơ bản. Sau khi đã gỡ runtime local, không chạy `vigov`, `python` hoặc `ollama`
trực tiếp trên Windows; dùng các lệnh `docker compose` bên dưới.

## Yêu cầu

- Docker Desktop chạy WSL2 backend.
- Driver NVIDIA cho WSL2 và `docker run --rm --gpus all ... nvidia-smi` hoạt động.
- Corpus có tại `Data/vector/unified`.
- Adapter QLoRA có tại đường dẫn khai báo trong `compose.yaml` nếu dùng
  lựa chọn QLoRA.

Không cần cài hoặc chạy Ollama Desktop trên Windows.

## Khởi động lần đầu hoặc sau khi đổi dependency

Từ PowerShell tại gốc repository:

```powershell
docker compose up --build -d
docker compose ps
docker compose exec -T ollama ollama list
```

Lần đầu, service `ollama-model-init` tải `qwen2.5:7b` vào volume trước
khi web khởi động. Web còn tạo RAG cache từ corpus trong lần đầu,
nên healthcheck cho phép tối đa 10 phút khởi tạo. Sau khi `web` healthy,
mở <http://localhost:8000>.

## Chạy hằng ngày và lệnh cơ bản

```powershell
docker compose up -d
docker compose ps
docker compose exec -T web vigov doctor
docker compose exec -T web vigov --help
docker compose exec -T ollama ollama list
```

Hỏi trực tiếp qua CLI hoặc chuẩn bị lại RAG cache:

```powershell
docker compose exec -T web vigov ask "Cần những giấy tờ gì để cấp bản sao hộ tịch?" --config configs/rag/inference-docker.yaml
docker compose exec -T web vigov rag prepare --config configs/rag/inference-docker.yaml
```

Container `web` đã tự chạy web server; không chạy thêm `vigov web` bên trong
container. Khi cần khởi động lại hoặc xem log:

```powershell
docker compose restart web ollama
docker compose logs --tail 100 web ollama ollama-model-init
```

## Dừng và quản lý dữ liệu

```powershell
docker compose down
```

Lệnh trên giữ model và cache. Chỉ dùng `docker compose down --volumes` khi
thực sự muốn xóa model Ollama, cache RAG và cache Hugging Face đã tải.

Các dữ liệu vẫn cần trên host vì đang được bind mount vào container:

- `Data/vector/unified`: corpus vector cho RAG.
- `Data/golden_dataset`: Golden train/val/test, bind mount read-only cho Evaluation v2.
- `outputs/evaluation_v2`: prediction và kết quả v2 ghi trở lại host.
- Adapter được khai báo trong `compose.yaml`: cần khi chọn QLoRA.
- Source và cấu hình repository: dùng để build image và mount artifact.

Không cần giữ `env`, `%USERPROFILE%\.ollama` hoặc `outputs/rag_cache` trên host.
Model Ollama, cache RAG và cache Hugging Face hoạt động nằm trong Docker named
volume. Không chạy `docker compose down --volumes` nếu muốn giữ chúng.

Compose phục vụ inference/web và smoke Evaluation v2 qua `run-v2`/
`export-v2`. Ingestion PDF, training và metric evaluation cần dependency tùy
chọn như BERTScore vẫn cần môi trường chuyên biệt; xem hướng dẫn
tương ứng trước khi chạy.

## GPU 6 GB và chuyển model

Cả `web` và `ollama` được quyền truy cập GPU. Web giữ cơ chế chuyển backend
tuần tự: dỡ model Ollama trước khi nạp QLoRA và giải phóng QLoRA trước
khi quay lại Base/RAG. `OLLAMA_NUM_PARALLEL=1` và
`OLLAMA_MAX_LOADED_MODELS=1` giảm nguy cơ hết VRAM trên RTX 4050 6 GB.

Không gửi đồng thời nhiều request GPU trong cấu hình này. Lần đầu chọn
QLoRA có thể tải base model vào volume `huggingface-cache`, nên sẽ lâu hơn.
