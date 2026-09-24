# Utils — lưu kết quả và chuẩn bị môi trường

Module cung cấp tiện ích dùng chung. Logic truy hồi, prompt và chấm điểm nằm ở
các module tương ứng; notebook chỉ gọi chúng qua CLI.

## Thành phần

| File | Trách nhiệm |
| --- | --- |
| [helpers.py](helpers.py) | Hash, định danh file, đọc/ghi JSONL, kiểm tra manifest |
| [colab_runtime.py](colab_runtime.py) | Cài/khởi động Ollama và tải model cho Colab |
| [build_colab_notebooks.py](build_colab_notebooks.py) | Sinh notebook clone dự án và gọi `src` |

## JSONL và manifest

- `json_hash()` tạo SHA-256 từ JSON sắp khóa; `file_hash()` đọc file theo khối.
- `stat_identity()` lấy đường dẫn tuyệt đối, kích thước, thời gian sửa; đây không phải hash nội dung.
- `append_result()` thêm bản ghi UTF-8, bổ sung newline nếu cần, flush và fsync.
- `read_results(repair_tail=True)` có thể cắt dòng JSON cuối bị ngắt và chưa có newline;
  lỗi nằm giữa file hoặc dòng lỗi đã kết thúc vẫn được báo ra.
- `ensure_run()` ghi manifest lần đầu và yêu cầu khớp chính xác khi dùng lại thư mục.
  Có prediction mà thiếu manifest cũng bị từ chối.

[RAG orchestrator](../rag/README.md) xây nội dung manifest, gồm cấu hình, hash bộ test,
định danh corpus, dấu vân tay mã nguồn và digest model Ollama. Cơ chế ghi kết quả
không có khóa liên tiến trình để điều phối nhiều bên cùng ghi vào một thư mục.

## Chuẩn bị Ollama trên Colab

`ensure_ollama(model, base_url)` kiểm tra dịch vụ local. Nếu chưa có binary trên
Colab, cài `zstd`, tải script cài Ollama, cài dịch vụ. Nếu chưa chạy, khởi động
`ollama serve`, ghi log `/tmp/ollama.log`, chờ sẵn sàng rồi `ollama pull` model.

Với URL không phải localhost/127.0.0.1, hàm chỉ kiểm tra model ở dịch vụ từ xa.
Ngoài Colab, hàm phụ thuộc vào Ollama đã có trong môi trường. Hàm không tự cấu hình API key hoặc xác thực Git.
[LLM client](../llm/README.md) quản lý các request inference sau khi dịch vụ sẵn sàng.

## Sinh notebook

`build_colab_notebooks.py` tạo lại ba notebook từ các mẫu cell trong mã nguồn.
Các notebook được tạo với trạng thái chưa thực thi và không có output cell:

- [Worker embedding](../../ipynb/colab_worker_embed.ipynb).
- [Gộp FAISS](../../ipynb/merge_vector_packs.ipynb).
- [Qwen + RAG](../../ipynb/base_rag/lqwen2_5_7B_rag.ipynb).

Luồng notebook: clone/fetch đúng ref → cài requirements → mount Drive → cấu hình
→ gọi module bằng subprocess. Không chứa bản sao mã pipeline.
Generator là nguồn định nghĩa cấu trúc ba notebook này. Notebook baseline trong
`ipynb/base` và notebook parse nằm ngoài phạm vi cập nhật của generator.

[Kiến trúc tổng thể](../README.md)
