# Module `vigovbot.vectordb`

## Trách nhiệm

Module xác minh corpus FAISS và chuẩn bị cache metadata SQLite phục vụ truy hồi.
Việc tạo corpus thuộc `vigovbot.embeddings`; module này không tạo embedding hoặc
sinh câu trả lời.

## Luồng xử lý

```text
corpus FAISS + metadata + manifest ──> prepare_corpus() ──> index + SQLite cache
```

## Đầu vào và đầu ra

`prepare_corpus()` nhận corpus dạng thư mục hoặc ZIP và `cache_root`; kết quả là
đường dẫn index cục bộ, database `metadata.sqlite` và dictionary thông tin cache.
Khóa SQLite `row_id` giữ đúng vị trí 0-based của metadata trong FAISS.

## Ràng buộc

- Corpus phải có FAISS index 1024 chiều, metadata tương ứng và manifest hợp lệ.
- FAISS sử dụng inner product trên vector đã chuẩn hóa L2.
- Cache chỉ được tái sử dụng khi identity, version, embedding và checksum khớp.

[Đặc tả embedding](../../../EMBEDDING.md) · [Kiến trúc hệ thống](../../../docs/architecture.md)
