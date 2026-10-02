# Module `vigovbot.ingestion`

## Trách nhiệm

Module cung cấp hai nhóm chức năng: trích xuất nội dung PDF/OCR và truy cập corpus
đã hợp nhất. Điều phối PDF thành chunk thuộc `vigovbot.pipelines.indexing`.

## Vị trí trong kiến trúc

```text
PDF ──> recovery.extract_pdf() ──> Markdown + metadata trích xuất
Corpus/ZIP ──> unified.verify_corpus() ──> danh tính + manifest đã xác minh
```

## Đầu vào và đầu ra

| Thành phần | Đầu vào | Đầu ra |
|---|---|---|
| `extract_pdf()` | Đường dẫn PDF, `IngestionSettings` | Markdown và dictionary thông tin trích xuất |
| `corpus_stream()` | Thư mục hoặc ZIP corpus, tên artifact | Luồng byte của artifact |
| `corpus_identity()` | Thư mục hoặc ZIP corpus | SHA-256 của index và metadata |
| `verify_corpus()` | Corpus và chính sách legacy | Danh tính nội dung và manifest hợp lệ |

## Ràng buộc

Corpus có manifest phải vượt qua kiểm tra định dạng và checksum. Corpus không có
manifest bị từ chối, trừ khi caller bật `allow_legacy`. Module chỉ xác minh tính
toàn vẹn và nguồn gốc kỹ thuật được khai báo; không chứng minh độ tin cậy của nội
dung tài liệu.

[Kiến trúc hệ thống](../../../docs/architecture.md) · [Hướng dẫn vận hành](../../../docs/trien-khai-rag-co-ban.md)
