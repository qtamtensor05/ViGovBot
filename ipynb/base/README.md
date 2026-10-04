# Qwen2.5:7B baseline trên Colab

Notebook `lqwen2_5_7B.ipynb` dùng cùng luồng QA v4 với notebook RAG nhưng
mặc định `NO_RETRIEVAL = True`. Model nhận trực tiếp câu hỏi/lịch sử,
không nạp corpus, encoder hay FAISS.

- Dataset: `rag_tthc_three_1500`.
- View: single, multi hoặc coverage.
- Single/coverage dùng `reference_history`; multi dùng `free_running` khi cần
  đánh giá lỗi dây chuyền.
- `LIMIT = 10` để smoke; `LIMIT = 0` để chạy đủ view.
- Dùng `RUN_NAME` riêng cho mỗi view/mode; runner chưa resume output cũ.

Baseline vẫn chấm coverage, action, độ tương đồng câu trả lời và latency.
Recall/MRR, unit recovery và citation của retrieval không áp dụng.

Sinh lại notebook: `python scripts/build_colab_notebooks.py`.
