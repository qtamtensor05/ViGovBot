# RAG — điều phối pipeline và CLI

Module kết nối các bước xử lý, quản lý cấu hình và vòng đời mô hình.
Quan hệ giữa các module được mô tả trong [kiến trúc tổng thể](../README.md).

## Thành phần

| File | Vai trò |
| --- | --- |
| [config.py](config.py) | Pydantic kiểm tra YAML, giá trị mặc định và đường dẫn |
| [pipeline.py](pipeline.py) | Chuẩn bị dữ liệu, quản lý phiên suy luận, manifest và điều phối báo cáo |
| [__main__.py](__main__.py) | Nhận tham số CLI và gọi `execute()` |
| [version.py](version.py) | Phiên bản pipeline dùng trong cache/manifest |

## Luồng điều phối

`execute(config, command)` nhận cấu hình đã kiểm tra. Với lệnh `run`:

1. [Vector DB](../vectordb/README.md) chuẩn bị FAISS/SQLite; [evaluation](../evaluation/README.md) đọc và chọn bộ câu hỏi.
2. Bộ điều phối kiểm tra mô hình qua [LLM client](../llm/README.md), sau đó tạo hoặc kiểm tra manifest lượt chạy.
3. Nạp [encoder](../embeddings/README.md), tokenizer Qwen và [retriever](../retrieval/README.md).
4. Chạy thử số câu đã cấu hình, sau đó chạy các câu chưa có prediction thành công.
5. Mỗi câu đi qua `answer_question()`: truy hồi → [prompt](../prompts/README.md) → Ollama; trả prediction, nguồn và thời gian.
6. Đóng SQLite, giải phóng encoder, yêu cầu Ollama dỡ Qwen trước khi tính metric.
7. Gọi evaluation xuất báo cáo vào `data.output_dir`.

Nếu lỗi xảy ra trong phiên suy luận, phần giải phóng tài nguyên vẫn được thực hiện.
Yêu cầu dỡ Qwen thất bại được ghi cảnh báo. Pipeline không chứa API web hoặc lịch sử hội thoại;
hiện dùng CLI để đánh giá RAG dense retrieval cơ bản.

## Cấu hình

[rag_config.yaml](../../rag_config.yaml) độc lập với [config PDF](../../config.yaml).
Các khóa ngoài schema bị từ chối; đường dẫn tương đối tính từ thư mục chứa YAML.

| Nhóm | Phạm vi | Chi tiết |
| --- | --- | --- |
| `data.unified_source`, `data.cache_dir` | Corpus và cache | [Vector DB](../vectordb/README.md) |
| `data.dataset_path/dataset_zip`, `data.output_dir` | Test và kết quả | [Evaluation](../evaluation/README.md) |
| `embedding` | Model/revision/device BGE-M3 | [Embeddings](../embeddings/README.md) |
| `retrieval.top_k` | Số đoạn tìm được | [Retrieval](../retrieval/README.md) |
| `retrieval.max_chunk_tokens`, `llm.tokenizer*` | Ngân sách ngữ cảnh | [Prompts](../prompts/README.md) |
| `llm` | Ollama và tham số sinh | [LLM](../llm/README.md) |
| `evaluation` | Chọn câu, BERTScore, đối chiếu baseline | [Evaluation](../evaluation/README.md) |

Cấu hình yêu cầu `dataset_path` hoặc `dataset_zip`; `num_ctx` phải lớn hơn `num_predict + 256`.
`top_k`, `max_chunk_tokens`, timeout và batch BERTScore phải dương.
`max_cases: null` chọn toàn bộ bộ test; `smoke_test_n: 0` bỏ lượt thử trong `run`.

## Giao diện điều phối

`__main__.py` nhận đường dẫn YAML và tên chế độ qua CLI, sau đó gọi `execute()`.
Điểm vào `main.py` ở thư mục gốc định tuyến nhánh `rag` tới giao diện này;
nhánh mặc định thuộc PDF ingestion.

| Lệnh | Công việc |
| --- | --- |
| `prepare` | Chuẩn bị SQLite/FAISS, kiểm tra test; không tải mô hình |
| `smoke` | Thử `smoke_test_n` câu, in câu trả lời/nguồn; không ghi prediction chính |
| `evaluate` | Chạy đánh giá và lưu từng câu, chưa tính metric |
| `report` | Tính metric từ prediction đã lưu; không nạp Qwen/BGE-M3 |
| `run` | Chạy toàn bộ từ chuẩn bị đến báo cáo |

Chế độ `report` đọc prediction đã lưu và kiểm tra định danh lượt chạy từ bộ test
và nguồn corpus. Chế độ này không chuyển lại SQLite và không thực hiện suy luận Qwen.

## Tiếp tục và tính nhất quán

Manifest gồm cấu hình, hash bộ test, danh sách ID, prompt, định danh nguồn unified,
dấu vân tay mã Python liên quan và digest Qwen. `ensure_run()` trong
[utils](../utils/README.md) yêu cầu khớp khi dùng lại thư mục đầu ra.

Khi manifest khớp, runner tiếp tục các câu chưa thành công. Thay đổi dữ liệu,
mô hình, tham số hoặc mã pipeline khiến lượt chạy không còn khớp kết quả cũ.
`report` xác minh cấu hình/mã/dữ liệu với manifest nhưng không yêu cầu Ollama hoạt động.
Cơ chế ghi output không có khóa giữa các tiến trình. Việc ghi nhận câu lỗi và
tính metric thuộc [evaluation](../evaluation/README.md).

## Quan hệ với môi trường Colab

[Notebook RAG](../../ipynb/base_rag/lqwen2_5_7B_rag.ipynb) clone repository,
cài requirements, mount Drive, lưu YAML riêng ở `/content/rag_colab.yaml`, rồi
gọi cùng giao diện CLI. Notebook không chứa bản sao logic RAG. Mẫu notebook
được quản lý bởi [utils](../utils/README.md).

[Kiến trúc tổng thể](../README.md)
