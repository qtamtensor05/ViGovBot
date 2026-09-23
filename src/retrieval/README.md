# Retrieval — tìm đoạn liên quan

[retriever.py](retriever.py) triển khai `Retriever`, kết hợp encoder BGE-M3,
FAISS inner product và metadata SQLite. Hiện tại là truy hồi dense vector cơ bản.

## Đầu vào và đầu ra

Constructor nhận `index_path`, `db_path` từ [vector store](../vectordb/README.md)
và encoder từ [embeddings](../embeddings/README.md). Khi khởi tạo, module nạp FAISS
vào RAM, mở SQLite chỉ đọc và kiểm tra số dòng, số chiều, loại chỉ mục.

`search(question, top_k=5)` trả về danh sách kết quả theo thứ tự điểm FAISS.
Mỗi kết quả gồm `row_id`, `score` và các trường metadata như `chunk_id`,
`source_code`, `source_file`, `text_content`.

## Luồng xử lý

1. Encode một câu hỏi thành vector float32 `(1, 1024)`.
2. Kiểm tra vector hữu hạn, khác zero; chuẩn hóa L2.
3. Tìm `min(top_k, index.ntotal)` kết quả qua `index.search()`.
4. Với từng ID, đọc payload từ SQLite và gắn điểm cosine.
5. Trả kết quả cho [prompts](../prompts/README.md); không đưa đáp án bộ test vào truy hồi.

## Cấu hình và vòng đời

`index_path` và `db_path` là kết quả chuẩn bị của `prepare_corpus()`.
Nhóm `retrieval.top_k` trong [rag_config.yaml](../../rag_config.yaml) điều khiển
số đoạn truy hồi. Bộ điều phối tạo retriever khi bắt đầu phiên suy luận và gọi
`close()` để đóng SQLite khi kết thúc. FAISS được giải phóng khi không còn tham chiếu.

## Phạm vi hiện tại

Không có BM25/hybrid search, reranker, bộ lọc metadata, query rewriting hoặc ngưỡng
điểm để loại kết quả yếu. Không mở rộng sang `parent_section`. Vì vậy top-k vẫn
có thể trả đoạn không liên quan; yêu cầu từ chối khi thiếu thông tin nằm trong prompt.
`IndexFlatIP` tìm kiếm chính xác trên toàn bộ vector, thời gian tăng theo kích thước corpus.

[Kiến trúc tổng thể](../README.md)
