# Chạy ViGovBot bằng Docker Desktop

Luồng Docker mặc định gồm web Base/RAG và Ollama trong hai container. Ollama lưu model
trong volume `ollama-models`; web lưu cache RAG trong volume `rag-cache`. Cấu
hình local `configs/rag/inference.yaml` không thay đổi; container dùng
`configs/rag/inference-docker-ollama.yaml` với endpoint `http://ollama:11434`.

Đây là runtime mặc định nhẹ cho web Base/RAG, dùng Torch CPU và không
mang CUDA. QLoRA cục bộ nằm trong target/service GPU tùy chọn. Workflow evaluation
hiện hành có thể chạy bằng môi trường Python dự án trên Windows để đọc Golden v3
và ghi output trực tiếp; Ollama và inference web vẫn chạy trong Docker.

## Yêu cầu

- Docker Desktop chạy WSL2 backend.
- Driver NVIDIA cho WSL2 và `docker run --rm --gpus all ... nvidia-smi` hoạt động.
- Corpus có tại `Data/vector/unified`.
- Adapter QLoRA chỉ bắt buộc khi khởi động profile `gpu`.

Không cần cài hoặc chạy Ollama Desktop trên Windows.

## Khởi động lần đầu hoặc sau khi đổi dependency

Từ PowerShell tại gốc repository:

```powershell
docker compose up --build -d
docker compose ps
docker compose exec -T ollama ollama list
```

Chỉ build lại khi đổi `pyproject.toml`, Dockerfile hoặc dependency. `src` và
`configs` được bind mount; sau khi chỉ sửa code/cấu hình, chạy
`docker compose restart web`.

Lần đầu, service `ollama-model-init` tải `qwen2.5:7b` vào volume trước
khi web khởi động. Web còn tạo RAG cache từ corpus trong lần đầu,
nên healthcheck cho phép tối đa 10 phút khởi tạo. Sau khi `web` healthy,
mở <http://localhost:8001>. Cổng trong container vẫn là 8000; có thể đổi cổng
host bằng biến `VIGOVBOT_WEB_PORT` nếu 8001 cũng đang được sử dụng.

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
docker compose exec -T web vigov ask "Cần những giấy tờ gì để cấp bản sao hộ tịch?" --config configs/rag/inference-docker-ollama.yaml
docker compose exec -T web vigov rag prepare --config configs/rag/inference-docker-ollama.yaml
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
- Bản merge GGUF `outputs/qlora_v2/qwen2.5-7b-qlora-rag-sft-q8_0.gguf`: Compose tự động
  nhập thành `qwen-qlora-rag-sft:latest` vào volume Ollama (và tự động gỡ bỏ model v1 `qwen-qlora:latest`).
- `src` và `configs`: mount read-only cho development; sửa code/cấu hình chỉ
  cần recreate/restart container, không build lại dependency.

Không cần giữ `env`, `%USERPROFILE%\.ollama` hoặc `outputs/rag_cache` trên host.
Model Ollama, cache RAG và cache Hugging Face hoạt động nằm trong Docker named
volume. Không chạy `docker compose down --volumes` nếu muốn giữ chúng.

Compose chỉ phục vụ inference/web và model. Workflow evaluation v3.2 đọc Golden
v3, ghi output và gọi API `http://localhost:8001` từ môi trường Python trên host; Golden/output
không được đưa hoặc mount vào container web. Ingestion PDF, training và metric
evaluation cần dependency tùy chọn như BERTScore vẫn cần môi trường chuyên biệt.

Profile Docker mặc định dùng `configs/rag/inference-docker-ollama.yaml` với
`retrieval.top_k: 15`. Profile `web-gpu` dùng
`configs/rag/inference-docker.yaml` với `retrieval.top_k: 5`. Đây là lựa chọn
cấu hình theo profile, không phải hai giai đoạn candidate/rerank; runtime online
không bật reranker.

Dockerfile cài dependency nặng trước khi copy source. Vì vậy thay đổi source
không làm mất cache PyTorch ở lần build kế tiếp; chỉ thay đổi `pyproject.toml`
mới buộc cài lại dependency.

## QLoRA merge trên Web

Web mặc định tại cổng 8001 có bốn lựa chọn Base, Base + RAG, QLoRA v2 và
QLoRA v2 + RAG. Hai lựa chọn QLoRA v2 dùng chung `qwen-qlora-rag-sft:latest` qua Ollama,
không nạp adapter PEFT trong tiến trình Web. Model v1 cũ (`qwen-qlora:latest`) đã được gỡ bỏ khỏi cấu hình phục vụ.

Target `web-gpu` vẫn giữ CUDA, PEFT và bitsandbytes tách khỏi image web mặc
định. Có thể khởi động service tùy chọn tại cổng 8002:

```powershell
docker compose --profile gpu build web-gpu
docker compose --profile gpu up -d web-gpu
```

Chỉ build target GPU khi thực sự cần dependency CUDA cục bộ khác.

## GPU 6 GB và chuyển model

`web-gpu` và `ollama` được quyền truy cập GPU. Web GPU giữ cơ chế chuyển backend
tuần tự: dỡ model Ollama trước khi nạp QLoRA và giải phóng QLoRA trước
khi quay lại Base/RAG. `OLLAMA_NUM_PARALLEL=1` và
`OLLAMA_MAX_LOADED_MODELS=1` giảm nguy cơ hết VRAM trên RTX 4050 6 GB.

Không gửi đồng thời nhiều request GPU trong cấu hình này. Lần đầu chọn
QLoRA có thể tải base model vào volume `huggingface-cache`, nên sẽ lâu hơn.

## Chọn adapter trên từng máy

Đặt `QLORA_ADAPTER_PATH` trong `.env` thành thư mục adapter thực tế trên host
(chứa `adapter_config.json` và trọng số), theo mẫu `.env.example`. Không chép
đường dẫn run cá nhân vào YAML. Profile GPU dùng giá trị này hoặc mặc
định `outputs/qlora/best_adapter`. Thư mục không tồn tại sẽ bị từ chối thay vì
tự tạo thư mục rỗng. Container GPU luôn đọc adapter tại `/app/models/qlora`.
Sau khi đổi mount, dùng `docker compose --profile gpu up -d --force-recreate web-gpu`.

Khi chạy Python trực tiếp, đặt `$env:QLORA_ADAPTER_PATH` trước khi chạy CLI;
đường dẫn tương đối của biến được tính từ thư mục làm việc. Python không tự
nạp `.env`. Khi không có biến, config local dùng `outputs/qlora/best_adapter`;
cần chuẩn bị adapter tại đó trước khi chọn QLoRA. Không di chuyển run lịch sử.
