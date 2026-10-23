# Kiến trúc hệ thống ViGovBot

Tài liệu mô tả cấu trúc thành phần, ranh giới phụ thuộc và hợp đồng artifact của
pipeline ViGovBot. Nội dung phản ánh package `vigovbot` phiên bản 0.2.0.

## Mô hình thành phần

Mã chính nằm trong `src/vigovbot`. Package cài bằng pip và CLI `vigovbot`
không phụ thuộc thư mục làm việc của repository. Notebook cài package từ
checkout và sử dụng namespace `vigovbot.*`; lớp tương thích `src.*` đã được bỏ.

```mermaid
flowchart LR
    PDF --> ingestion --> chunking --> embeddings --> vectordb
    question[Câu hỏi + Lịch sử] --> router[router: Phân loại / Viết lại]
    router -->|ngoài phạm vi / mơ hồ| answer[Câu trả lời trực tiếp]
    router -->|câu mới / hỏi tiếp| retrieval
    vectordb --> retrieval --> prompts --> llm
    llm --> answer
    answer --> evaluation
    dataset[Bộ test và đáp án chuẩn] --> evaluation
    sft[Dataset SFT] --> training[training: QLoRA 4-bit]
    training --> checkpoint[Checkpoint / best_adapter]
    checkpoint --> local[local_transformers: Base + Adapter]
    question --> local --> answer
```

| Thành phần | Trách nhiệm |
|---|---|
| `ingestion` | Trích xuất PDF/OCR; đọc corpus dạng thư mục/ZIP |
| `chunking` | Metadata thủ tục, phân mục, chia đoạn có giới hạn kích thước |
| `embeddings` | BGE-M3, tạo pack; nạp encoder câu hỏi |
| `vectordb` | Kiểm tra/gộp pack, FAISS, cache SQLite |
| `retrieval` | Chuẩn hóa vector câu hỏi, tra FAISS và đọc metadata |
| `prompts` | Prompt tiếng Việt, ngân sách ngữ cảnh, ghi lại nguồn đã dùng |
| `llm` | Giao tiếp Ollama |
| `training` | SFT QLoRA 4-bit, chat template, masking multi-turn, checkpoint/resume và inference adapter |
| `rag` | Chuẩn bị corpus, phiên inference, điều phối hỏi đáp/benchmark |
| `evaluation` | Bộ test, metric và báo cáo; đáp án chuẩn không đưa vào inference |
| `pipelines/indexing.py` | Điều phối PDF → chunk → báo cáo và CLI ingestion |
| `schemas.py` | Hợp đồng dữ liệu, model/kích thước vector, version artifact/cache |
| `artifacts.py` | Checksum, revision, khóa ghi và công bố artifact |
| `experiments.py` | Manifest lượt chạy và JSONL có thể tiếp tục |
| `scripts/` | Sinh notebook, xuất lock, kiểm chứng package/môi trường |

## Ranh giới phụ thuộc

`vectordb` không phụ thuộc vào pipeline tạo embedding hoặc version của `rag`.
Hợp đồng corpus dùng `schemas.py`; version cache độc lập với version pipeline đánh giá.
`utils` chỉ giữ helper nhỏ và re-export tương thích. Notebook không chứa
bản sao logic embedding/RAG; sinh lại bằng `python scripts/build_colab_notebooks.py`.

`prepare` phụ thuộc corpus; `ask` phụ thuộc corpus và mô hình. Các lệnh
`smoke`, `evaluate`, `run`, `report` phụ thuộc thêm bộ test. API Python
`answer_question()` nhận retriever/tokenizer/settings, không nhận đáp án chuẩn.

Manifest thí nghiệm lưu cấu hình, fingerprint mã xử lý, checksum bộ test/corpus,
revision embedding, digest Ollama và phiên bản runtime Python/thư viện chính.
Giữ model/tokenizer revision cố định trong cấu hình khi chốt benchmark; ghi
commit repository trong báo cáo để liên kết kết quả với lần phát hành.

## Hợp đồng artifact và tính toàn vẹn

- Corpus: `tthc_unified.index`, `tthc_unified_metadata.json`, `corpus_manifest.json`.
- Manifest: phiên bản định dạng, số dòng, SHA-256 từng file, model BGE-M3,
  commit SHA của model, kích thước 1024 và phiên bản cách ghép prefix.
- Pipeline embedding phân giải revision thành commit bất biến trước khi nạp mô hình.
- Pipeline kiểm tra metadata và vector trước khi công bố corpus hoàn chỉnh.
- RAG kiểm tra checksum trước khi FAISS đọc index, rồi kiểm tra encoder.
  `embedding.revision: null` chọn revision từ manifest; giá trị khác bị từ chối.
- FAISS dùng inner product sau chuẩn hóa L2; thứ tự metadata là ID SQLite.

Manifest được ghi cuối. Lỗi Python trong lúc công bố sẽ dọn các file vừa công bố;
mất điện/kill tiến trình có thể để lại file dở dang nhưng thiếu manifest nên bị
từ chối ở chế độ mặc định. Không ghi đè artifact đã có; chọn thư mục đầu ra mới.

Khóa file bảo vệ việc công bố artifact, tạo cache và ghi kết quả trong một
filesystem hỗ trợ khóa hệ điều hành. Khóa này không phải cơ chế khóa phân tán
giữa nhiều phiên Colab qua Drive. Mỗi lần tạo corpus và benchmark phải sử dụng
thư mục đầu ra riêng.

Checksum xác minh tính nhất quán, không xác minh tác giả. Chỉ nạp index FAISS
từ nguồn đáng tin cậy. Chế độ legacy không thể chứng minh model tạo vector.

## Phạm vi hệ thống

Hiện phục vụ nghiên cứu qua CLI, notebook Colab và web UI/API cục bộ. Web dùng
FastAPI trên Uvicorn (ASGI), nạp một encoder/FAISS/SQLite dùng chung; các tác vụ
inference đồng bộ được chuyển sang worker thread để không chặn event loop, encoder và SQLite
có khóa riêng. Ollama/QLoRA tuần tự hóa theo model call để bảo vệ GPU và switching;
API ngoài không dùng khóa GPU. SQLite mở read-only để truy hồi từ thread request. Lịch sử nằm trong
trình duyệt và được gửi lại theo từng model/chế độ. Chưa có lưu phiên phía server,
quản lý người dùng hoặc xác thực/TLS.

Pipeline fine-tuning nằm tại `src/vigovbot/training/`, gọi qua `vigov train`.
Training dùng quantization 4-bit, chat template và loss masking; checkpoint
resume kiểm tra trạng thái optimizer/scheduler/RNG và dữ liệu trước khi tiếp tục.
Artifact nằm trong `outputs/qlora/`; web có chế độ QLoRA qua local Transformers.
QLoRA trực tiếp không truy hồi nguồn như RAG. Đây là pipeline nghiên cứu có
kiểm tra tính toàn vẹn, chưa phải chứng nhận vận hành production.
Các nội dung liên quan được quy định tại [migration](migration.md),
[môi trường](../setup/environments.md) và [quy trình phát triển](../../CONTRIBUTING.md).

## Ranh giới orchestration và helper (2026-10-18)

- `chunking/markdown.py`: schema, metadata/heading, chia section và lắp chunk.
  `chunking/tables.py`: hàm thuần sửa continuation, tìm/lặp header và flatten
  cell; gọi trực tiếp không cần tạo chunker. Method cũ giữ alias tương thích.
  `repair_table_continuations` vốn đã là hàm độc lập trước refactor.
- `rag/pipeline.py`: điều phối route → retrieval → budget/prompt → kết quả;
  `rag/response.py`: routing retry/fallback và generation JSON/citation retry.
  Helper nhận tokenizer/settings/answer_fn, không sở hữu FAISS hay dataset nhãn.
- `training/train.py`: điều phối vòng đời; `_prepare_training_data` giữ gate
  resume/hash/run identity, `_prepare_model` cấu hình quantization/LoRA,
  `_training_arguments` xây Trainer arguments, `_finalize_training` đánh giá
  best-restored model và xuất báo cáo. Stop/interruption vẫn thuộc orchestration.
  Đây là refactor source/test; chưa chứng minh GPU training/resume thật.

### Các tên module cùng basename không cùng trách nhiệm

| Module | Hợp đồng |
|---|---|
| `artifacts` | Checksum, corpus provenance, publication/lock |
| `training.artifacts` | Thư mục run training, config snapshot, đường dẫn báo cáo |
| `evaluation.report` | Báo cáo baseline notebook với metric legacy |
| `evaluation.benchmark_report` | Báo cáo benchmark QA và provenance |
| `training.report` | Báo cáo trạng thái/artifact training |
| `evaluation.metrics` | Metric baseline notebook legacy |
| `evaluation.lexical` | Hợp đồng lexical hiện đại dùng chung |
| `training.metrics` | Metric generation/loss training; lexical dùng module chung |

Dùng import đầy đủ namespace tại ranh giới subsystem. Không đổi tên hàng loạt
các module public chỉ vì cùng basename; chúng không ghi đè nhau trong Python.
