# ViGovBot

ViGovBot là dự án nghiên cứu xây dựng chatbot tiếng Việt hỗ trợ dịch vụ hành chính công, kết hợp QLoRA (Quantized Low-Rank Adaptation) và RAG (Retrieval-Augmented Generation).

Dự án hướng tới hỗ trợ người dân tra cứu thủ tục, thành phần hồ sơ, điều kiện thực hiện và quy trình giải quyết bằng câu trả lời dễ hiểu, có dẫn nguồn. QLoRA phục vụ tinh chỉnh mô hình với chi phí tài nguyên thấp; RAG bổ sung ngữ cảnh từ tài liệu hành chính để hỗ trợ câu trả lời bám sát nguồn.

Nghiên cứu tập trung đánh giá độ chính xác, mức độ bám sát tài liệu, khả năng hạn chế thông tin sai lệch và hiệu quả sử dụng tài nguyên trong bối cảnh tiếng Việt.

## Tài liệu

- [Xử lý dữ liệu](src/README.md): pipeline, cấu hình, cách chạy và Colab.
- [Ingestion](src/ingestion/README.md): đọc PDF, OCR, lưu trữ và báo cáo.
- [Chunking](src/chunking/README.md): chia đoạn, metadata và cấu trúc dữ liệu RAG.
- [Qwen + RAG](src/rag/README.md): kiến trúc module trong `src`, CLI và cấu hình đánh giá.
- [Colab RAG](ipynb/base_rag/README.md): clone dự án, dùng GPU Colab và đọc dữ liệu trên Drive.

## Giấy phép

Mã nguồn được phát hành theo [giấy phép](LICENSE). Dữ liệu, tài liệu và mô hình của bên thứ ba tuân theo giấy phép và điều kiện sử dụng của từng nguồn.
