# Module `vigovbot.embeddings`

## Trách nhiệm

Module nạp encoder BGE-M3 và tạo trực tiếp corpus FAISS có manifest từ dữ liệu
chunk. Encoder cũng được `rag` sử dụng để mã hóa câu hỏi.

## Luồng xử lý

```text
thư mục/ZIP chunk → kiểm tra schema → BGE-M3 encode → chuẩn hóa L2
                  → FAISS index + metadata + corpus manifest
```

## Đầu vào và đầu ra

`corpus_builder.build_corpus()` nhận thư mục hoặc ZIP chứa JSON/JSONL, thư mục
đầu ra, model revision, thiết bị và batch size. Mỗi bản ghi phải thỏa hợp đồng
trường trong `vigovbot.schemas`.

Đầu ra gồm:

- `tthc_unified.index`: chỉ mục FAISS;
- `tthc_unified_metadata.json`: metadata theo đúng thứ tự row;
- `corpus_manifest.json`: revision, số dòng và checksum artifact.

## Ràng buộc

Revision được phân giải thành commit SHA trước khi encode. Retry do CUDA OOM được
phép giảm batch size nhưng phải giữ nguyên thứ tự bản ghi. File ZIP bị path
traversal, vượt giới hạn, vector rỗng/không hữu hạn hoặc metadata sai schema đều
bị từ chối. Công bố artifact sử dụng khóa và không ghi đè corpus đã tồn tại.

[Đặc tả embedding](../../../EMBEDDING.md) · [Kiến trúc hệ thống](../../../docs/architecture.md)
