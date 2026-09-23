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
định danh corpus, dấu vân tay mã nguồn và digest model Ollama. Không có khóa liên tiến trình;
không chạy đồng thời nhiều phiên ghi cùng output.

## Chuẩn bị Ollama trên Colab

`ensure_ollama(model, base_url)` kiểm tra dịch vụ local. Nếu chưa có binary trên
Colab, cài `zstd`, tải script cài Ollama, cài dịch vụ. Nếu chưa chạy, khởi động
`ollama serve`, ghi log `/tmp/ollama.log`, chờ sẵn sàng rồi `ollama pull` model.

Với URL không phải localhost/127.0.0.1, hàm chỉ kiểm tra model ở dịch vụ từ xa.
Máy cá nhân cần cài Ollama trước. Hàm không tự cấu hình API key hoặc xác thực Git.
[LLM client](../llm/README.md) quản lý các request inference sau khi dịch vụ sẵn sàng.

## Sinh notebook

Từ thư mục gốc repository:

```sh
python -m src.utils.build_colab_notebooks
```

Lệnh ghi lại ba notebook, xóa output cell cũ:

- [Worker embedding](../../ipynb/colab_worker_embed.ipynb).
- [Gộp FAISS](../../ipynb/merge_vector_packs.ipynb).
- [Qwen + RAG](../../ipynb/base_rag/lqwen2_5_7B_rag.ipynb).

Luồng notebook: clone/fetch đúng ref → cài requirements → mount Drive → cấu hình
→ gọi module bằng subprocess. Không chứa bản sao mã pipeline.
Muốn sửa lâu dài cấu trúc notebook, sửa generator rồi sinh lại; đổi tham số cho
một phiên có thể làm ngay trong các cell cấu hình. Notebook baseline trong `ipynb/base`
và notebook parse không được generator này cập nhật.

Mã sửa trên máy cá nhân cần được push lên GitHub trước khi Colab clone.
Xem [hướng dẫn Colab](../../ipynb/base_rag/README.md) để chọn `REPO_URL`, `GIT_REF`.

[Quay lại tổng quan](../README.md)
