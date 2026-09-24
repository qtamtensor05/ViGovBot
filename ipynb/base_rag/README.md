# Chạy Qwen + RAG trên Colab bằng cách clone dự án

Mở **[lqwen2_5_7B_rag.ipynb](lqwen2_5_7B_rag.ipynb)** trên Colab.
Notebook chỉ chuẩn bị môi trường và gọi CLI; toàn bộ pipeline nằm trong `src/`.
Không cần tải các file `.py` thủ công hoặc nhúng mã pipeline vào notebook.

## 1. Đưa phiên bản mã muốn chạy lên GitHub

Notebook mặc định clone `https://github.com/qtamtensor05/ViGovBot.git` và chọn
nhánh `codex/feat-multi-embedding-colab`. **Nhánh đó phải được push và chứa các
file mới trước khi chạy Colab.** Các thay đổi chỉ ở máy cá nhân không xuất hiện
trong bản clone. Sau khi merge vào main, có thể đặt `GIT_REF = "main"`; dùng
commit hash khi muốn cố định phiên bản để tái lập kết quả.

Notebook không tự push hay ghi đè thay đổi local trong checkout Colab. Với repo
riêng tư, cấu hình xác thực Git của phiên trước; không ghi token vào notebook
hoặc URL. Nếu sửa phiên bản đã import, khởi động lại phiên Python trước khi chạy tiếp.

## 2. Chuẩn bị Drive

```text
MyDrive/RAG_Data/
├── unified.zip
└── qa_test/
    └── dataset.jsonl
```

ZIP chứa `tthc_unified.index` và `tthc_unified_metadata.json`, có thể trong thư mục con.
Có thể đặt `unified_source` thành thư mục đã giải nén. Nếu dùng bộ test ZIP,
đặt `dataset_path = None`, `dataset_zip = ".../qa_test.zip"`.

## 3. Chạy notebook

1. Chọn **Runtime > Change runtime type > GPU**.
2. Chạy ô clone; kiểm tra `REPO_URL`, `GIT_REF`. Ô này in commit được sử dụng.
3. Chạy ô cài `requirements-rag.txt` và ô mount Drive.
4. Sửa đường dẫn trong ô cấu hình. YAML được lưu tại `/content/rag_colab.yaml`, ngoài repository.
5. Chạy ô chuẩn bị Ollama; mã trong `src/utils/colab_runtime.py` cài/chạy dịch vụ và tải Qwen.
6. Chạy ô pipeline với `COMMAND = "run"`.
7. Xem bảng kết quả và các file trong thư mục Drive đã chọn.

Lệnh chính do notebook gọi:

```sh
python -m src.rag --config /content/rag_colab.yaml run
```

`run` chuẩn bị SQLite → nạp BGE-M3 và FAISS → thử 5 câu → chạy đánh giá → giải phóng
mô hình → tính metric và lưu báo cáo. Đổi `COMMAND` thành `prepare`, `smoke`,
`evaluate` hoặc `report` để chạy riêng từng giai đoạn.

## 4. Tài nguyên và tiếp tục phiên bị ngắt

Metadata 6 GB được đọc theo luồng sang SQLite trên ổ đĩa Colab, không nạp toàn bộ
vào RAM. FAISS nạp RAM. Mặc định BGE-M3 dùng CPU, Qwen dùng tài nguyên do Ollama
quản lý. Có thể đặt `embedding.device = "cuda"` khi đủ VRAM.
BERTScore mặc định CPU, batch 1, chạy sau khi dỡ các mô hình inference; có thể chậm.

Cache ở `/content` bị mất khi reset runtime. Kết quả từng câu nằm trên Drive nên
có thể tiếp tục bằng cùng mã nguồn, cấu hình và thư mục đầu ra. Khi đổi code,
model, tham số hoặc bộ test, chọn `output_dir` mới để tránh trộn kết quả.

Kết quả gồm prediction, nguồn truy hồi, thời gian, lỗi, metric từng câu và tổng hợp.
Chỉ số giữ cách tính của baseline; không có điểm thật được điền sẵn.
Chi tiết kiến trúc/cấu hình: [src/rag/README.md](../../src/rag/README.md).
