# RAG — điều phối pipeline và CLI

Module kết nối các bước xử lý, quản lý cấu hình và vòng đời mô hình.
Chi tiết thuật toán/định dạng nằm trong README của từng module, xem [bản đồ src](../README.md).

## Thành phần

| File | Vai trò |
| --- | --- |
| [config.py](config.py) | Pydantic kiểm tra YAML, giá trị mặc định và đường dẫn |
| [pipeline.py](pipeline.py) | Chuẩn bị dữ liệu, quản lý inference, manifest và điều phối báo cáo |
| [__main__.py](__main__.py) | Nhận tham số CLI và gọi `execute()` |
| [version.py](version.py) | Phiên bản pipeline dùng trong cache/manifest |

## Luồng điều phối

`execute(config, command)` nhận cấu hình đã kiểm tra. Với lệnh `run`:

1. [Vector DB](../vectordb/README.md) chuẩn bị FAISS/SQLite; [evaluation](../evaluation/README.md) đọc và chọn bộ câu hỏi.
2. [LLM client](../llm/README.md) kiểm tra model Ollama; tạo/kiểm tra manifest lượt chạy.
3. Nạp [encoder](../embeddings/README.md), tokenizer Qwen và [retriever](../retrieval/README.md).
4. Chạy thử số câu đã cấu hình, sau đó chạy các câu chưa có prediction thành công.
5. Mỗi câu đi qua `answer_question()`: truy hồi → [prompt](../prompts/README.md) → Ollama; trả prediction, nguồn và thời gian.
6. Đóng SQLite, giải phóng encoder, yêu cầu Ollama dỡ Qwen trước khi tính metric.
7. Gọi evaluation xuất báo cáo vào `data.output_dir`.

Nếu lỗi xảy ra trong phiên inference, phần dọn tài nguyên vẫn được thực hiện.
Yêu cầu dỡ Qwen thất bại được ghi cảnh báo. Pipeline không chứa API web hoặc lịch sử hội thoại;
hiện dùng CLI để đánh giá RAG dense retrieval cơ bản.

## Cấu hình

[rag_config.yaml](../../rag_config.yaml) độc lập với [config PDF](../../config.yaml).
Khóa lạ bị từ chối; đường dẫn tương đối tính từ thư mục chứa YAML.

| Nhóm | Phạm vi | Chi tiết |
| --- | --- | --- |
| `data.unified_source`, `data.cache_dir` | Corpus và cache | [Vector DB](../vectordb/README.md) |
| `data.dataset_path/dataset_zip`, `data.output_dir` | Test và kết quả | [Evaluation](../evaluation/README.md) |
| `embedding` | Model/revision/device BGE-M3 | [Embeddings](../embeddings/README.md) |
| `retrieval.top_k` | Số đoạn tìm được | [Retrieval](../retrieval/README.md) |
| `retrieval.max_chunk_tokens`, `llm.tokenizer*` | Ngân sách ngữ cảnh | [Prompts](../prompts/README.md) |
| `llm` | Ollama và tham số sinh | [LLM](../llm/README.md) |
| `evaluation` | Chọn câu, BERTScore, đối chiếu baseline | [Evaluation](../evaluation/README.md) |

Cần `dataset_path` hoặc `dataset_zip`; `num_ctx` phải lớn hơn `num_predict + 256`.
`top_k`, `max_chunk_tokens`, timeout và batch BERTScore phải dương.
`max_cases: null` chọn toàn bộ bộ test; `smoke_test_n: 0` bỏ lượt thử trong `run`.

## Cách chạy trên máy cá nhân

Cài Python 3.10+, chuẩn bị Ollama theo [README llm](../llm/README.md), rồi chạy
các lệnh từ thư mục gốc repository:

```sh
pip install -r requirements-rag.txt
python -m src.rag --config rag_config.yaml run
```

Tương đương: `python main.py rag --config rag_config.yaml run`.
`python main.py` không có `rag` vẫn chạy PDF ingestion.

| Lệnh | Công việc |
| --- | --- |
| `prepare` | Chuẩn bị SQLite/FAISS, kiểm tra test; không tải mô hình |
| `smoke` | Thử `smoke_test_n` câu, in câu trả lời/nguồn; không ghi prediction chính |
| `evaluate` | Chạy đánh giá và lưu từng câu, chưa tính metric |
| `report` | Tính metric từ prediction đã lưu; không nạp Qwen/BGE-M3 |
| `run` | Chạy toàn bộ từ chuẩn bị đến báo cáo |

Ví dụ: `python -m src.rag --config rag_config.yaml evaluate`, sau đó đổi
`evaluate` thành `report` để tính điểm riêng. Lệnh `report` vẫn cần bộ test và
nguồn corpus còn truy cập được để kiểm tra lượt chạy, nhưng không chuyển lại SQLite.

## Tiếp tục và tính nhất quán

Manifest gồm cấu hình, hash bộ test, danh sách ID, prompt, định danh nguồn unified,
dấu vân tay mã Python liên quan và digest Qwen. `ensure_run()` trong
[utils](../utils/README.md) yêu cầu khớp khi dùng lại thư mục đầu ra.

Chạy lại cùng cấu hình để tiếp tục các câu chưa thành công. Khi đổi dữ liệu,
model, tham số hoặc mã pipeline, chọn thư mục kết quả mới. `report` xác minh
cấu hình/mã/dữ liệu với manifest nhưng không yêu cầu Ollama đang chạy.
Không chạy hai phiên ghi cùng output. Số câu lỗi và cách tính metric xem
[README evaluation](../evaluation/README.md).

## Colab

[Notebook RAG](../../ipynb/base_rag/lqwen2_5_7B_rag.ipynb) clone repository,
cài requirements, mount Drive, lưu YAML riêng ở `/content/rag_colab.yaml`, rồi
chạy cùng CLI. Hướng dẫn thao tác ở [ipynb/base_rag](../../ipynb/base_rag/README.md);
cách sinh notebook ở [utils](../utils/README.md).

[Quay lại tổng quan](../README.md)
