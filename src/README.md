# Kiến trúc xử lý dữ liệu và RAG

Thư mục `src` chứa các module xử lý dữ liệu, truy hồi và đánh giá câu trả lời.
Hệ thống gồm hai luồng: chuẩn bị chỉ mục từ tài liệu và trả lời câu hỏi dựa trên chỉ mục.
Module `rag` điều phối luồng trả lời và đánh giá; `utils` cung cấp cơ chế dùng chung.

```text
Chuẩn bị dữ liệu:
PDF → ingestion → chunking → embeddings → vectordb (unified)

Trả lời và đánh giá:
unified → ingestion + vectordb (FAISS/SQLite)
câu hỏi → embeddings → retrieval → prompts → llm → evaluation
```

## Phân chia trách nhiệm

| Module | Trách nhiệm |
| --- | --- |
| [ingestion](ingestion/README.md) | Đọc PDF/OCR và mở nguồn unified ZIP/thư mục |
| [chunking](chunking/README.md) | Chia đoạn theo cấu trúc tài liệu và tạo metadata |
| [embeddings](embeddings/README.md) | Tạo vector tài liệu và nạp encoder câu hỏi BGE-M3 |
| [vectordb](vectordb/README.md) | Gộp FAISS, chuyển metadata sang SQLite, giữ ánh xạ ID |
| [retrieval](retrieval/README.md) | Tạo vector câu hỏi, tìm top-k và lấy nội dung |
| [prompts](prompts/README.md) | Xây dựng thông điệp Qwen và giới hạn ngữ cảnh |
| [llm](llm/README.md) | Giao tiếp với Ollama và tiếp nhận câu trả lời |
| [evaluation](evaluation/README.md) | Quản lý bộ test, kết quả từng câu và chỉ số đánh giá |
| [rag](rag/README.md) | Điều phối, quản lý cấu hình và vòng đời mô hình |
| [utils](utils/README.md) | JSONL, manifest, chuẩn bị môi trường và sinh notebook |

## Ranh giới dữ liệu

Ingestion và chunking tạo các bản ghi văn bản có metadata. Embeddings chuyển
`text_content` thành vector; vectordb gộp vector và duy trì ánh xạ với metadata.
Khi truy vấn, retrieval trả các đoạn liên quan cho prompts; llm nhận thông điệp
đã ghép ngữ cảnh và sinh câu trả lời. Evaluation đối chiếu kết quả với đáp án chuẩn.

Đáp án chuẩn và ngữ cảnh mẫu của bộ test chỉ thuộc luồng đánh giá, không được
đưa vào truy hồi hoặc prompt. Thứ tự metadata được giữ xuyên suốt để ID FAISS
ánh xạ đúng tới nội dung trong SQLite.

## Cấu hình và điểm tích hợp

[configuration.py](configuration.py) kiểm tra [cấu hình PDF](../config.yaml);
[rag/config.py](rag/config.py) kiểm tra [cấu hình RAG](../rag_config.yaml).
Hai cấu hình độc lập; đường dẫn tương đối được tính từ thư mục chứa YAML.

`main.py` định tuyến sang pipeline PDF hoặc RAG. Các module embedding, gộp vector
và RAG có điểm vào CLI riêng. Notebook Colab chuẩn bị môi trường và gọi các điểm
vào này; logic xử lý nằm trong `src`.

Kiến trúc truy hồi hiện tại sử dụng dense vector BGE-M3, FAISS inner product,
metadata SQLite và Qwen qua Ollama. Hệ thống chưa có tầng API web hoặc quản lý
lịch sử hội thoại. Quy trình và phạm vi của từng module được mô tả tại README tương ứng.
