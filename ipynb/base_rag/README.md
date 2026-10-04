# Qwen + RAG trên Colab

Mở `lqwen2_5_7B_rag.ipynb`, chọn GPU và chạy tuần tự.
Đặt `GIT_REF` tới commit đã có trên GitHub. Notebook cài package từ checkout,
thêm thư mục `src` vào đường dẫn import của kernel, mount Drive, tạo YAML riêng
từ `configs/rag.yaml` và gọi `python -m vigovbot qa-v4 run/score`.

Chuẩn bị corpus có đủ index, metadata và `corpus_manifest.json` tại
`/content/drive/MyDrive/RAG_Data/unified.zip` (hoặc thư mục corpus).
Đưa bộ test đã giải nén lên Drive tại
`/content/drive/MyDrive/RAG_Data/rag_tthc_three_1500`, gồm ít nhất
`runner_queries.jsonl`, `cases.jsonl` và các file view cần chạy. Dữ liệu không
được tải cùng git clone vì `Data/` bị gitignore.

Ô cấu hình có ba view `views_single_1500.json`, `views_multi_1500.json`
và `views_coverage_1500.json`. Single/coverage dùng `reference_history`; multi
dùng `free_running` để đo lỗi dây chuyền. `LIMIT = 10` để smoke;
đặt `LIMIT = 0` để chạy đủ 1.500 lượt của view đã chọn.

Bật `NO_RETRIEVAL` để chạy baseline Qwen/Ollama; chế độ này không cần corpus.
Đổi `RUN_NAME` mỗi lượt chạy: runner không ghi đè kết quả và chưa hỗ trợ resume.
Kết quả nằm trong `OUTPUT_DIR/RUN_NAME` trên Drive:
`predictions.jsonl` (câu hỏi/câu trả lời hoặc lỗi), `predictions.jsonl.run.json`, `scores.json`,
`comparison.csv` (câu hỏi/câu trả lời/đáp án tham chiếu/điểm), cấu hình và thông tin commit.
Đáp án tham chiếu chỉ đọc khi chấm và xuất bảng, không gửi vào model.
Notebook hiện chấm lexical tùy chọn; không bật BERTScore hay semantic judge tự động.

Trong ô sinh câu trả lời, mỗi câu hiển thị thời gian còn lại và giờ hoàn thành dự
kiến của toàn bộ tập đã chọn. ETA dùng tốc độ trung bình thực tế nên có thể dao
động ở các câu đầu; file `predictions.jsonl.run.json` lưu thời điểm bắt đầu/kết
thúc và tổng thời gian sau khi runner hoàn tất.

Các thay đổi mã nguồn phải được commit/push lên GitHub trước khi Colab fetch.
Đổi nhánh/commit khi đã import package cần khởi động lại runtime để tránh dùng module cũ.

[Migration dữ liệu cũ](../../docs/migration.md) · [Kiến trúc](../../docs/architecture.md)

Sinh lại notebook: `python scripts/build_colab_notebooks.py`.
