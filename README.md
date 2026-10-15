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

```powershell
python -m pip install -e .
vigov doctor
vigov web
```

Xem toàn bộ lệnh tại [tham chiếu CLI](docs/guides/cli.md). Thiết lập môi trường,
GPU và dependency nằm trong [tài liệu setup](docs/README.md#bắt-đầu-và-môi-trường).

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
