# ViGovBot

Pipeline nghiên cứu tra cứu thủ tục hành chính tiếng Việt: PDF/OCR → chunking →
BGE-M3 → FAISS/SQLite → Qwen qua Ollama. Hỗ trợ hỏi đáp một câu, lưu nguồn truy hồi
và đánh giá trên bộ câu hỏi. QLoRA, API web và hội thoại nhiều lượt thuộc roadmap,
chưa phải tính năng hiện có.

## Chạy kiểm thử và ví dụ không cần GPU/model

Từ thư mục repository, dùng Python 3.10–3.14; đã kiểm chứng cục bộ Windows/Python 3.14.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[test,dev]"
.venv\Scripts\python -m unittest discover -s tests -v
.venv\Scripts\python scripts/demo_offline.py
.venv\Scripts\python -m vigovbot --help
```

Linux/macOS dùng `.venv/bin/python`. Demo in `status: ok` và `source_code: 1.000005`;
vector tổng hợp chỉ kiểm chứng luồng dữ liệu, không đo chất lượng mô hình.
Muốn cài đúng phiên bản đã khóa, xem [môi trường](docs/environments.md).

## Chạy dữ liệu và mô hình thật

Cài nhóm thư viện cần dùng trong môi trường đang chọn:

```powershell
python -m pip install -e ".[pdf,embedding,vector,rag,evaluation]"
python -m vigovbot ingest --config configs/pipeline.yaml
python -m vigovbot embed --pack-id pack_01 --zip-path Data/packs/pack_01.zip --output-dir Data/vector/completed --no-mount
python -m vigovbot merge Data/vector/completed --output-dir Data/vector/unified
python -m vigovbot rag --config configs/inference.yaml prepare
python -m vigovbot rag --config configs/inference.yaml ask --question "Cần những giấy tờ gì để cấp bản sao hộ tịch?"
python -m vigovbot rag --config configs/rag.yaml run
```

Chuẩn bị PDF trong `Data/pdf`, ZIP chứa JSON chunk và bộ test theo cấu hình trước
khi chạy. Cài/chạy Ollama, tải `qwen2.5:7b` trước khi `ask`/`run`; BGE-M3, tokenizer
và BERTScore cần tải trọng số ở lần đầu. OCR cần Tesseract/tessdata nếu có bản scan.
Trong nhiều worker, chốt cùng `--revision` bằng commit SHA của model.

Mỗi pack/corpus mới có manifest kiểm tra checksum và revision. Corpus cũ thiếu
manifest cần chế độ tương thích rõ ràng; đọc [migration](docs/migration.md).
Không dùng lại thư mục kết quả benchmark cũ sau khi đổi code/config/dữ liệu.

## Cấu trúc

```text
src/vigovbot/    Mã xử lý, hợp đồng dữ liệu và CLI
src/*/          Lớp tương thích cho import/điểm chạy cũ
configs/        Template ingestion, chunking, RAG và inference
scripts/        Sinh notebook, demo, xuất lock và kiểm tra đóng gói
ipynb/          Notebook nghiên cứu/Colab; giữ đường dẫn cũ
examples/       Dữ liệu mẫu nhỏ có chủ đích
locks/          Phiên bản dependency theo môi trường
tests/          Kiểm thử offline
docs/           Kiến trúc, migration, môi trường, roadmap và kiểm chứng
```

## Tài liệu

- [Kiến trúc và ranh giới module](docs/architecture.md)
- [Embedding và corpus](EMBEDDING.md)
- [Môi trường và lock](docs/environments.md)
- [Chuyển đổi từ phiên bản cũ](docs/migration.md)
- [Quy trình phát triển](CONTRIBUTING.md)
- [Trạng thái và roadmap](docs/roadmap.md)
- [Kết quả kiểm chứng](docs/verification.md)

## Giấy phép

Chưa cấp quyền sử dụng lại mã nguồn; chủ dự án sẽ chốt giấy phép sau.
Xem [LICENSE](LICENSE). Dependency, dữ liệu, tài liệu và model của bên thứ ba
vẫn tuân theo giấy phép và điều kiện riêng.
