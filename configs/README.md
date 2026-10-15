# Cấu hình ViGovBot

Cấu hình nguồn được chia theo trách nhiệm:

- `ingestion/`: pipeline nhập PDF, OCR/parser và chunking.
- `rag/`: suy luận chatbot và các profile đánh giá RAG.
- `training/`: QLoRA base, môi trường/phần cứng và thí nghiệm.

Đường dẫn dữ liệu trong YAML được giải quyết từ vị trí file cấu hình hoặc từ gốc
repository tùy loader. Không di chuyển `config.yaml` nằm trong các run ở
`outputs/`: đó là snapshot bất biến dùng để kiểm tra provenance và resume.

Các entry point chuẩn:

```text
configs/ingestion/pipeline.yaml
configs/rag/inference.yaml
configs/rag/evaluation.yaml
configs/training/base.yaml
configs/training/environments/gpu.yaml
configs/training/experiments/smoke.yaml
```
