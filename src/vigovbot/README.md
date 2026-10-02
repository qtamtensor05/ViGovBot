# Package `vigovbot`

Đây là package chính của dự án, được đóng gói theo cấu hình trong `pyproject.toml`.
Điểm vào dòng lệnh là `vigovbot.cli:main`.

## Bản đồ module

| Lớp | Module |
|---|---|
| Hợp đồng và hạ tầng | `schemas`, `configuration`, `artifacts`, `experiments` |
| Indexing | `ingestion`, `chunking`, `pipelines` |
| Vector hóa và lưu trữ | `embeddings`, `vectordb` |
| Inference | `retrieval`, `prompts`, `llm`, `rag` |
| Đánh giá | `evaluation` |
| Tiện ích runtime | `utils`, `console` |

README trong từng module mô tả trách nhiệm, luồng xử lý, đầu vào, đầu ra và các
ràng buộc cục bộ. Cài đặt và vận hành được quản lý ở tài liệu cấp repository để
không lặp lại giữa các module.

[Kiến trúc hệ thống](../../docs/architecture.md) · [Giao diện CLI](../../README.md)
