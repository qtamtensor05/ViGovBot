# Qwen + RAG trên Colab

Mở `lqwen2_5_7B_rag.ipynb`, chọn GPU và chạy tuần tự.
Đặt `GIT_REF` tới commit đã có trên GitHub. Notebook cài package từ checkout,
thêm thư mục `src` vào đường dẫn import của kernel, mount Drive, tạo YAML riêng
từ `configs/rag.yaml` và gọi `python -m vigovbot rag`.

Chuẩn bị corpus có đủ index, metadata và `corpus_manifest.json`; bộ test
`qa_test/dataset.jsonl` hoặc ZIP. Dùng output mới khi đổi code/config/dữ liệu.

[Migration dữ liệu cũ](../../docs/migration.md) · [Kiến trúc](../../docs/architecture.md)

Sinh lại notebook: `python scripts/build_colab_notebooks.py`.
