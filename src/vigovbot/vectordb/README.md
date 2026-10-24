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

Cache v2 giữ mọi metadata JSON từ corpus, trừ `parent_section` là bản sao nội
dung dài. Chỉ `chunk_id` và `text_content` bắt buộc; metadata nghiệp vụ tùy chọn.
`row_id` và score truy hồi luôn do FAISS/SQLite xác định, không lấy từ payload.
Version nằm trong khóa thư mục cache: lần chạy đầu tạo cache mới từ corpus đã
xác minh, không ghi đè cache v1 và không tạo lại embedding. Cần dung lượng cho
bản sao index/cache mới; cache cũ chỉ xóa khi người vận hành chủ động quyết định.

[Đặc tả embedding](../../../docs/architecture/embedding.md) · [Kiến trúc hệ thống](../../../docs/architecture/architecture.md)
