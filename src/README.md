# Tổng quan các module trong src

Code xử lý nằm trong các module Python; notebook Colab clone dự án và gọi code
để tận dụng tài nguyên. Mỗi thư mục có README riêng mô tả kiến trúc và quy trình.

```text
Chuẩn bị dữ liệu:
PDF → ingestion → chunking → embeddings → vectordb (unified)

Trả lời và đánh giá:
unified → ingestion + vectordb (FAISS/SQLite)
câu hỏi → embeddings → retrieval → prompts → llm → evaluation
                         rag điều phối; utils hỗ trợ
```

## Đọc tài liệu theo module

| Module | Nội dung README |
| --- | --- |
| [ingestion](ingestion/README.md) | Đọc PDF/OCR và mở nguồn unified ZIP/thư mục |
| [chunking](chunking/README.md) | Chia section/chunk, metadata và schema |
| [embeddings](embeddings/README.md) | Worker embedding pack và encoder câu hỏi BGE-M3 |
| [vectordb](vectordb/README.md) | Gộp FAISS, chuyển metadata sang SQLite, ánh xạ ID |
| [retrieval](retrieval/README.md) | Encode câu hỏi, tìm top-k và lấy nội dung |
| [prompts](prompts/README.md) | Prompt Qwen và giới hạn ngữ cảnh |
| [llm](llm/README.md) | Ollama, tham số sinh và xử lý lỗi |
| [evaluation](evaluation/README.md) | Bộ qa_test, metric, checkpoint và báo cáo |
| [rag](rag/README.md) | Điều phối, YAML và CLI toàn pipeline |
| [utils](utils/README.md) | JSONL, manifest, môi trường Colab và tạo notebook |

## Điểm bắt đầu

Chạy lệnh từ thư mục gốc repository:

| Công việc | Lệnh | Cấu hình |
| --- | --- | --- |
| PDF → chunks | `python main.py` | [config.yaml](../config.yaml) |
| Embedding pack | `python -m src.embeddings.pack_worker --help` | Tham số CLI, xem README embeddings |
| Gộp pack | `python -m src.vectordb.merge --help` | Tham số CLI, xem README vectordb |
| Qwen + RAG | `python -m src.rag --config rag_config.yaml run` | [rag_config.yaml](../rag_config.yaml) |

Cài requirements tương ứng trước khi chạy: [PDF](../requirements.txt),
[embedding](../requirements-embedding.txt), [gộp vector](../requirements-vector-db.txt),
[RAG](../requirements-rag.txt). Chi tiết môi trường và lệnh riêng nằm trong README module.

[configuration.py](configuration.py) kiểm tra YAML cho pipeline PDF;
[rag/config.py](rag/config.py) kiểm tra YAML cho RAG. Hai cấu hình độc lập,
đường dẫn tương đối tính từ thư mục chứa YAML.

## Notebook Colab

- [Parse metadata](../ipynb/parse_metadata.ipynb).
- [Worker embedding](../ipynb/colab_worker_embed.ipynb).
- [Gộp FAISS](../ipynb/merge_vector_packs.ipynb).
- [Qwen + RAG](../ipynb/base_rag/lqwen2_5_7B_rag.ipynb), kèm [hướng dẫn Colab](../ipynb/base_rag/README.md).

Các notebook trên dùng mã từ repository; thay đổi local cần được push trước khi
Colab clone. [Notebook baseline](../ipynb/base/lqwen2_5_7B.ipynb) hiện vẫn chứa mã trực tiếp.

Kiểm thử từ thư mục gốc: `python -m unittest discover -s tests -v`.
Khi thay đổi một module, cập nhật README của module đó; README này chỉ giữ bản đồ hệ thống.
