# Module `vigovbot.retrieval`

## Trách nhiệm

Module mã hóa câu hỏi, truy vấn FAISS và ánh xạ kết quả sang metadata trong
SQLite. `Retriever` là đối tượng trạng thái, sở hữu FAISS index, kết nối SQLite
chỉ đọc và encoder truy vấn.

## Đầu vào và đầu ra

`Retriever(index_path, db_path, encoder)` nhận index FAISS, cache SQLite và một
encoder có giao diện `encode()`. `search(question, top_k)` trả về danh sách hit
theo điểm giảm dần; mỗi hit gồm `row_id`, `score` và payload metadata của chunk.

```text
câu hỏi → encoder → vector 1024 chiều → chuẩn hóa L2 → FAISS search
                                                      → SQLite lookup → hit[]
```

## Ràng buộc

Số hàng SQLite phải bằng số vector FAISS. Index phải có 1024 chiều và metric
inner product. Vector câu hỏi phải hữu hạn, khác vector không và đúng shape.
`top_k` phải dương và được giới hạn bởi số vector trong index. Caller phải gọi
`close()` hoặc quản lý `Retriever` qua vòng đời của phiên inference. Kết nối
SQLite được mở read-only với khả năng dùng từ thread HTTP khác thread khởi tạo;
`search()` và `close()` dùng khóa nội bộ để tuần tự hóa truy cập vào encoder,
FAISS và SQLite dùng chung.

[Kiến trúc hệ thống](../../../docs/architecture.md) · [Module RAG](../rag/README.md)
