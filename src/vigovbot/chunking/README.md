# Module `vigovbot.chunking`

## Trách nhiệm

Module chuyển Markdown của một thủ tục hành chính thành các chunk có cấu trúc,
giữ ngữ cảnh đề mục, bảng và metadata cần cho embedding/truy hồi.

## Luồng xử lý

```text
Markdown → làm sạch → trích xuất metadata → phân loại section
         → tách block/bảng → áp dụng giới hạn và overlap → TTHCChunk[]
```

## Đầu vào và đầu ra

Đầu vào chính của `TTHCStructureAwareChunker.process_document()` là Markdown,
tên file nguồn và mã thủ tục. Đầu ra là `TTHCDocument`, chứa metadata cấp tài liệu
và danh sách `TTHCChunk`.

Mỗi chunk có các trường nhận diện nguồn, tên thủ tục, loại section, tiền tố ngữ
cảnh, nội dung và section cha. `split_markdown_by_structure()` là giao diện đơn
giản hơn khi chỉ cần danh sách đoạn văn bản.

## Ràng buộc

- Kích thước chunk, overlap và giới hạn bảng lấy từ `ChunkingSettings`.
- Header của bảng được lặp lại khi bảng phải chia thành nhiều chunk.
- Nội dung rỗng hoặc cấu trúc không thể xử lý phát sinh `TTHCChunkingError`.
- Module không đọc PDF và không ghi artifact; trách nhiệm đó thuộc pipeline indexing.

[Kiến trúc hệ thống](../../../docs/architecture.md) · [Hướng dẫn vận hành](../../../docs/trien-khai-rag-co-ban.md)
