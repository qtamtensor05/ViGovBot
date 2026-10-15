# ViGovBot

ViGovBot là hệ thống nghiên cứu Retrieval-Augmented Generation (RAG) cho dữ liệu
thủ tục hành chính tiếng Việt. Pipeline hiện tại xử lý tài liệu PDF, tạo chỉ mục
vector và sinh câu trả lời kèm thông tin nguồn bằng Qwen qua Ollama.

```text
PDF/OCR → chuẩn hóa và chia đoạn → BGE-M3 → FAISS/SQLite
                                              ↓
Câu hỏi + lịch sử → Qwen định tuyến → BGE-M3/FAISS truy hồi
                                      ↓
                         xét bằng chứng → câu trả lời và nguồn
```

## Trạng thái dự án

Phạm vi đã triển khai gồm CLI, notebook Colab, web UI/API cục bộ, xử lý dữ liệu,
truy hồi dense, hỏi đáp nhiều lượt và đánh giá. Web giữ lịch sử riêng cho từng
lựa chọn trong trình duyệt; chưa có lưu phiên phía server, quản lý người dùng,
xác thực/TLS hoặc fine-tuning QLoRA.

Mã nguồn nằm trong package duy nhất `src/vigovbot`. Notebook cài package từ
checkout và sử dụng namespace `vigovbot.*`.

## Yêu cầu hệ thống

- Python 3.10–3.14.
- Ollama và model `qwen2.5:7b` cho chức năng hỏi đáp.
- Tesseract cùng tessdata tiếng Việt khi xử lý PDF scan bằng OCR.
- Dung lượng lưu trữ và bộ nhớ phù hợp với corpus; BGE-M3 được tải ở lần sử dụng đầu tiên.

Các lệnh trong tài liệu được thực thi từ thư mục gốc của repository.

## Cài đặt

### Môi trường kiểm thử

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[test,dev]"
.venv\Scripts\python -m unittest discover -s tests -v
.venv\Scripts\python scripts/demo_offline.py
```

Demo offline không tải model và không yêu cầu GPU. Trường `status` trong kết quả
phải có giá trị `ok`.

### Môi trường RAG

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[rag]"
ollama pull qwen2.5:7b
```

Trên Linux và macOS, sử dụng `.venv/bin/python` thay cho
`.venv\Scripts\python`. Các nhóm dependency khác và quy trình cài đặt tái lập
được mô tả trong [tài liệu môi trường](docs/environments.md).

## Vận hành RAG với corpus hiện có

Cấu hình `configs/rag/inference.yaml` sử dụng corpus tại `Data/vector/unified`.
Corpus hợp lệ phải có đủ ba artifact:

- `tthc_unified.index`;
- `tthc_unified_metadata.json`;
- `corpus_manifest.json`.

Khởi tạo cache truy vấn:

```powershell
.venv\Scripts\python -m vigovbot rag --config configs/rag/inference.yaml prepare
```

Thực hiện truy vấn:

```powershell
.venv\Scripts\python -m vigovbot rag --config configs/rag/inference.yaml ask `
  --question "Hồ sơ cấp bản sao hộ tịch gồm những gì?"
```

Corpus cũ không có manifest không được chấp nhận theo cấu hình mặc định. Quy trình
chuyển đổi được quy định tại [tài liệu migration](docs/migration.md).

### Giao diện web hỏi đáp

Sau khi embedding hoàn tất, khởi động server bằng cấu hình inference:

```powershell
.venv\Scripts\python -m vigovbot rag --config configs/rag/inference.yaml web
```

Mở `http://127.0.0.1:8000` trong trình duyệt và nhấn `Ctrl+C` tại terminal để dừng.
Encoder, tokenizer và kho truy hồi chỉ được nạp một lần lúc khởi động. Có thể đổi địa
chỉ hoặc cổng bằng `--host` và `--port`. Chỉ nên dùng `--host 0.0.0.0` trong mạng tin
cậy vì server cơ bản này chưa có xác thực người dùng.

Các lựa chọn hiển thị trong UI được khai báo tại `web.models` trong file YAML.
Cấu hình mặc định có `Qwen base` (`mode: base`, gọi model trực tiếp),
`Qwen + RAG` (`mode: rag`, truy hồi tài liệu trước khi sinh) và `Qwen + QLoRA`
(`mode: qlora`, nạp `best_adapter` bằng Transformers 4-bit) để hiển thị ba câu
trả lời cạnh nhau. Ba provider được hỗ trợ là `ollama`, `openai_compatible` và
`local_transformers`. Với API bên ngoài, đặt tên biến chứa khóa tại
`api_key_env` và đặt giá trị biến đó trong môi trường chạy server; không ghi API key
trực tiếp vào YAML hoặc trình duyệt. Xem ví dụ trong `configs/rag/inference.yaml`.

QLoRA cần môi trường đã cài dependency GPU trong `requirements/qlora-gpu.txt` và
CUDA khả dụng. Cấu hình mặc định không giữ đồng thời model Ollama và local
Transformers trên GPU: khi chuyển backend, server dỡ model trước rồi mới nạp model
tiếp theo. Cách này phù hợp GPU 6 GB nhưng lần hỏi đầu sau mỗi lần chuyển sẽ chậm
do phải nạp lại weights. Cấu hình RTX 4050 ép model NF4 lên một GPU để tránh
Accelerate tự tách module 4-bit sang CPU; cần đóng ứng dụng dùng GPU trước khi
khởi động. Ba chế độ giữ lịch sử hội thoại riêng trên trình duyệt.

Router RAG dùng JSON Schema theo nhánh và thử lại một lần nếu JSON sai; hai lần
sai vẫn trả câu mặc định. UI hiển thị riêng fallback kỹ thuật và hỏi làm rõ thật.
Đặt `web.debug_routing: true` rồi khởi động lại server để xem raw JSON router.
Provider OpenAI-compatible ở nhánh RAG cần hỗ trợ strict `json_schema`;
chi tiết trong [tài liệu RAG nhiều lượt](docs/rag-multi-turn.md).

## Giao diện dòng lệnh

CLI thống nhất được cài bằng `pip install -e .` và có tên `vigov`. Các entry
point `vigovbot ingest|embed|rag|qa-v4` vẫn được giữ để tương thích trong giai
đoạn di chuyển.

```powershell
vigov --help
vigov doctor
vigov data check --config configs/training/base.yaml
vigov data stats --config configs/training/base.yaml
vigov gpu check
vigov train smoke --config configs/training/experiments/smoke.yaml --approve
vigov train start --config configs/training/environments/rtx5060ti_16gb.yaml --dry-run
vigov train status
vigov train logs --lines 100
vigov train stop
vigov train resume <checkpoint> --config configs/training/environments/rtx5060ti_16gb.yaml
vigov dashboard --run-id <run-id>
vigov eval test --run-id <run-id>
vigov report plots --run-id <run-id>
vigov report build --run-id <run-id>
```

`--dry-run` không khởi động training. `smoke` chỉ chạy thật khi có `--approve`;
không dùng test split để chọn model. Chi tiết migration và giới hạn hiện tại nằm
tại [tóm tắt refactor](docs/refactor-summary.md).

`train start/status/logs/stop/resume` dùng worker Python độc lập trên Windows và
Linux. Metadata process lưu PID, thời điểm tạo process và command marker để tránh
nhầm PID tái sử dụng; stop ưu tiên file yêu cầu graceful để callback lưu checkpoint.

| Nhóm lệnh | Chức năng | Đầu vào chính | Đầu ra chính |
|---|---|---|---|
| `vigovbot ingest` | Trích xuất và chia đoạn tài liệu | PDF, cấu hình ingestion/chunking | Metadata và báo cáo xử lý |
| `vigovbot embed` | Tạo corpus BGE-M3/FAISS | Thư mục hoặc ZIP chứa chunk JSON | Index, metadata và corpus manifest |
| `vigovbot rag` | Chuẩn bị cache, truy vấn và đánh giá | Corpus, cấu hình RAG, bộ test tùy lệnh | Câu trả lời hoặc báo cáo đánh giá |

Trợ giúp của từng nhóm lệnh:

```powershell
.venv\Scripts\python -m vigovbot --help
.venv\Scripts\python -m vigovbot rag --help
```

Quy trình tạo corpus từ PDF và chạy đánh giá được trình bày trong
[hướng dẫn vận hành RAG](docs/trien-khai-rag-co-ban.md).

## Cấu trúc repository

| Đường dẫn | Nội dung |
|---|---|
| `src/vigovbot/` | Package và CLI chính |
| `configs/` | Cấu hình chuẩn cho ingestion, chunking và RAG |
| `tests/` | Kiểm thử tự động không phụ thuộc model thật |
| `scripts/` | Công cụ sinh notebook, xuất lock và kiểm tra package |
| `ipynb/` | Notebook nghiên cứu và thực thi trên Colab |
| `examples/` | Fixture và dữ liệu minh họa có kích thước nhỏ |
| `docs/` | Kiến trúc, vận hành, migration và báo cáo kiểm chứng |

## Tài liệu

Mục lục và phạm vi của từng tài liệu được quản lý tại
[docs/README.md](docs/README.md). Quy định đóng góp mã nguồn nằm trong
[CONTRIBUTING.md](CONTRIBUTING.md).

## Giấy phép

Repository chưa cấp quyền sử dụng lại mã nguồn. Điều khoản hiện hành được ghi tại
[LICENSE](LICENSE).
