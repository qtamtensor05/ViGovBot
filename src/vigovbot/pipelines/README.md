# Module `vigovbot.pipelines`

## Trách nhiệm

Module điều phối pipeline indexing từ PDF đến JSON chunk. Đây là lớp use case của
nhánh xử lý tài liệu, tương ứng với vai trò điều phối của `vigovbot.rag` ở nhánh
truy vấn.

## Luồng xử lý

```text
PDF → validate_pdf() → extract_pdf() → normalize/clean Markdown
    → TTHCStructureAwareChunker → JSON chunk + báo cáo xử lý
```

## Đầu vào và đầu ra

`parse_pdf_to_hybrid_data()` nhận đường dẫn PDF, cấu hình pipeline và các dependency
có thể inject cho kiểm thử. Đầu ra thành công là dữ liệu chunk được ghi nguyên tử
vào thư mục cấu hình. Trường hợp trích xuất thiếu hoặc cần kiểm tra thủ công được
ghi vào báo cáo thay vì công bố chunk hoàn chỉnh.

CLI `ingest` gọi `indexing.main()` để xử lý một file hoặc tập PDF theo
`PipelineSettings`, `IngestionSettings` và `ChunkingSettings`.

## Ràng buộc

- File đầu vào phải có chữ ký PDF hợp lệ và không vượt giới hạn kích thước.
- File JSON được ghi qua file tạm và replace nguyên tử.
- Cảnh báo từ bước trích xuất và chunking phải được bảo toàn trong báo cáo.
- Pipeline không tạo embedding hoặc corpus FAISS.

[Kiến trúc hệ thống](../../../docs/architecture.md) · [Module ingestion](../ingestion/README.md) · [Module chunking](../chunking/README.md)
