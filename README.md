# ViGovBot

ViGovBot là hệ thống nghiên cứu hỏi đáp thủ tục hành chính tiếng Việt, kết hợp
Qwen2.5, RAG và pipeline QLoRA. Dự án cung cấp CLI thống nhất `vigov`, web UI/API
cục bộ, xử lý tài liệu, huấn luyện nền, đánh giá và báo cáo thực nghiệm.

## Khả năng chính

- Nhập PDF, chuẩn hóa/chia đoạn và tạo corpus BGE-M3 với FAISS/SQLite.
- Hỏi đáp Base, RAG hoặc QLoRA qua CLI, web UI và `/api/chat`.
- Huấn luyện QLoRA có preflight, smoke, checkpoint/resume và Early Stopping.
- Quản lý training nền, log, trạng thái, TensorBoard và graceful stop.
- Đánh giá, sinh prediction, metric, biểu đồ và báo cáo từ artifact đã lưu.

## Bắt đầu nhanh

Runtime web, RAG và Ollama hiện chạy bằng Docker Desktop; không cần cài Python,
virtual environment hoặc Ollama trên Windows.

Lần đầu hoặc sau khi đổi `pyproject.toml`/Dockerfile:

```powershell
docker compose up --build -d
docker compose ps
```

Những lần chạy hằng ngày chỉ cần `docker compose up -d`; sau khi sửa `src` hoặc
`configs`, dùng `docker compose restart web` mà không build lại.

Khi service `web` báo `healthy`, mở <http://localhost:8001>. Xem
[hướng dẫn Docker](docs/setup/docker.md) để vận hành và
[tham chiếu CLI](docs/guides/cli.md) để chạy lệnh bên trong container. Các môi
trường phát triển, training và evaluation chuyên biệt nằm trong
[tài liệu setup](docs/README.md#bắt-đầu-và-môi-trường).

## Cấu trúc chính

| Đường dẫn | Trách nhiệm |
|---|---|
| `src/vigovbot/` | Ứng dụng, CLI, RAG, API, training và evaluation |
| `configs/ingestion/` | Pipeline nhập liệu, OCR và chunking |
| `configs/rag/` | Inference và đánh giá RAG |
| `configs/training/` | Base, môi trường và experiment QLoRA |
| `tests/` | Unit, integration và regression tests |
| `docs/` | Hướng dẫn, kiến trúc, báo cáo và hồ sơ dự án |
| `Data/`, `outputs/` | Dataset và artifact runtime không thuộc tài liệu nguồn |

## Tài liệu

- [Mục lục tài liệu](docs/README.md)
- [Kiến trúc hệ thống](docs/architecture/architecture.md)
- [Vận hành RAG](docs/guides/trien-khai-rag-co-ban.md)
- [Huấn luyện QLoRA](docs/guides/training.md)
- [Đánh giá và báo cáo](docs/guides/evaluation.md)
- [Thiết lập phát triển](docs/setup/development.md)
- [Trạng thái dự án](docs/project/current-stage.md)

Các entry point cũ vẫn được giữ cho script lịch sử; luồng vận hành mới nên dùng
`vigov`. Dataset, checkpoint và kết quả thực nghiệm hiện có không được tự động
di chuyển hoặc ghi đè.

## Đóng góp và giấy phép

Xem [CONTRIBUTING.md](CONTRIBUTING.md). Điều khoản sử dụng nằm trong
[LICENSE](LICENSE).
