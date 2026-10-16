# Tham chiếu CLI `vigov`

## Runtime Docker hiện hành

Web, Base/RAG/QLoRA và Ollama chạy bằng Docker Compose. Không cần cài package
Python, tạo virtual environment hoặc cài Ollama trên Windows. Khởi động stack:

```powershell
docker compose up -d
docker compose ps
```

Lần đầu hoặc sau khi đổi dependency/source dùng `docker compose up --build -d`.
Container `web` đã chạy web server ở <http://localhost:8000>; không gọi thêm
`vigov web` trong container.

## Kiểm tra và hỏi đáp

```powershell
docker compose exec -T web vigov doctor
docker compose exec -T web vigov --help
docker compose exec -T ollama ollama list
docker compose exec -T web vigov ask "Hồ sơ gồm những gì?" --config configs/rag/inference-docker.yaml
docker compose exec -T web vigov rag prepare --config configs/rag/inference-docker.yaml
```

Cấu hình Docker phải là `configs/rag/inference-docker.yaml`; file này gọi Ollama
qua `http://ollama:11434`. Không dùng cấu hình local trỏ tới `localhost:11434`
từ container.

## Quản lý stack

```powershell
docker compose logs --tail 100 web ollama ollama-model-init
docker compose restart web ollama
docker compose down
```

`docker compose down` giữ các named volume. `docker compose down --volumes` xóa
model Ollama và các cache Docker, vì vậy chỉ dùng khi thực sự muốn tải/tạo lại.

## Các nhóm lệnh chưa thuộc runtime Compose

Compose hiện tại được đóng gói cho inference và web, không phải môi trường đầy
đủ để ingest PDF, tạo corpus mới, training hoặc evaluation. Các nhóm sau cần
môi trường chuyên biệt, dependency tương ứng và bind mount input/output rõ ràng:

- `vigov data ingest|embed|check|stats`
- `vigov rag smoke|evaluate|report|run`
- `vigov gpu`, `vigov train`, `vigov dashboard`
- `vigov eva`, `vigov report`

Không chạy các lệnh này bằng `docker compose exec web` với Compose hiện tại vì
artifact ghi trong filesystem container có thể mất và nhiều dataset/output chưa
được mount. Khi cần phát triển hoặc chạy pipeline, tạo lại môi trường theo
[Thiết lập phát triển](../setup/development.md), [Môi trường và tái lập](../setup/environments.md),
[Huấn luyện](training.md) hoặc [Đánh giá](evaluation.md).

Các entry point module `python -m vigovbot ingest|embed|rag|eva` dùng chung
dispatcher với CLI; workflow chuyên biệt không phải lệnh runtime Docker
thường ngày.
