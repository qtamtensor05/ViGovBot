# ViGovBot

ViGovBot là hệ thống nghiên cứu hỏi đáp thủ tục hành chính tiếng Việt, kết hợp
Qwen2.5, RAG và pipeline QLoRA. Dự án cung cấp CLI thống nhất `vigov`, web UI/API
cục bộ, xử lý tài liệu, huấn luyện nền, đánh giá và báo cáo thực nghiệm.

> **Trạng thái:** Mốc nghiên cứu/demo đã được chốt ngày 2026-11-09
> tại tag `vigovbot-research-v1`. Dự án không tuyên bố sẵn sàng production.
> Xem [báo cáo kết thúc](docs/reports/bao-cao-ket-thuc-nghien-cuu-demo.md).

## Kết quả sơ bộ

- Router v2 trên 1.246 mẫu đạt Scope Accuracy 96,95%, Action Accuracy 91,33%
  và Strict E2E Accuracy 74,08%.
- Benchmark PA1 bao gồm 638 case và sáu cấu hình. QLoRA v2 + RAG dẫn đầu
  EM 20,41%, key-fact coverage 38,78% và citation recall 53,43% trong snapshot.
- Kết quả còn giới hạn về invalid citation, abstention, unsupported answer và
  chưa được xác minh cho tải lớn hay production.

## Khả năng chính

- Nhập PDF, chuẩn hóa/chia đoạn và tạo corpus BGE-M3 với FAISS/SQLite.
- Hỏi đáp Base, RAG hoặc QLoRA qua CLI, web UI và `/api/chat`.
- Huấn luyện QLoRA có preflight, smoke, checkpoint/resume và Early Stopping.
- Quản lý training nền, log, trạng thái, TensorBoard và graceful stop.
- Đánh giá, sinh prediction, metric, biểu đồ và báo cáo từ artifact đã lưu.

## Bắt đầu nhanh

Phần này là công thức tái lập. Runtime Docker không được duy trì sẵn trên
máy đóng mốc; lần chạy mới sẽ tải/build lại image, model và cache cần thiết.
Web Base/RAG và Ollama có thể chạy bằng Docker Desktop mà không cần cài
Python, virtual environment hoặc Ollama trực tiếp trên Windows.

Lần đầu hoặc sau khi đổi `pyproject.toml`/Dockerfile:

```powershell
docker compose up --build -d
docker compose ps
```

Những lần chạy hằng ngày chỉ cần `docker compose up -d`; sau khi sửa `src` hoặc
`configs`, dùng `docker compose restart web` mà không build lại.
Lệnh web tự kiểm tra dependency, vector corpus, PhoBERT, cache, CUDA và cổng
trước khi mở server; model Ollama/QLoRA còn thiếu chỉ được cảnh báo, không chặn web.
Trong Docker, Qwen nền tải song song; QLoRA chỉ import qua profile `qlora` khi cần.
Ảnh mặc định dùng Torch CPU và không chứa CUDA; QLoRA cục bộ chạy
bằng profile `gpu` riêng theo hướng dẫn Docker.

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
