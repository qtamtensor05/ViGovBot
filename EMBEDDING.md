# Tạo embedding và gộp FAISS cho 5 pack ZIP

Mã xử lý nằm trong `src/embeddings/pack_worker.py` và `src/vectordb/merge.py`.
Notebook Colab chỉ clone repository, cài thư viện, kết nối Drive và gọi các module.
Trước khi chạy, đưa mã mới lên GitHub và đặt `GIT_REF` đúng nhánh hoặc commit.
Mặc định notebook dùng nhánh `codex/feat-multi-embedding-colab`.

## 1. Chuẩn bị dữ liệu

Đặt 5 ZIP trong `MyDrive/RAG_Data`: `pack_01.zip` đến `pack_05.zip`.
Mỗi ZIP chứa file JSON/TXT UTF-8: đối tượng JSON, mảng đối tượng hoặc JSON Lines.
Mỗi đoạn có các trường chuỗi `chunk_id`, `source_file`, `source_code`,
`procedure_name`, `section_type`, `context_prefix`, `text_content`, `parent_section`.
ID phải duy nhất và nội dung không rỗng.

## 2. Tạo embedding trên Colab

1. Tải [colab_worker_embed.ipynb](ipynb/colab_worker_embed.ipynb) lên Colab.
2. Bật GPU. Kiểm tra `REPO_URL`, `GIT_REF` rồi chạy ô clone.
3. Chạy ô cài thư viện và mount Drive.
4. Đặt `PACK_ID = "pack_01"` và chạy ô worker.
5. Khi xong, đổi lần lượt sang `pack_02`, `pack_03`, `pack_04`, `pack_05` và chạy lại ô worker.

Mỗi gói sinh hai file trong `MyDrive/RAG_Data/completed`:
`vectors_pack_01.npy` và `metadata_pack_01.json`, tương tự cho các pack còn lại.
Có thể chia mỗi phiên Colab một pack; không để hai phiên cùng ghi một cặp kết quả.

Batch mặc định 32; worker tự giảm batch khi CUDA OOM. Nếu một đoạn vẫn quá lớn,
dùng GPU nhiều bộ nhớ hơn hoặc đổi tham số thiết bị thành CPU.
BGE-M3 tạo vector 1024 chiều; `text_content` có tiền tố rồi sẽ không bị thêm lặp.
Giữ đoạn trong giới hạn 8192 token; thư viện cắt bớt đầu vào vượt giới hạn.
Dùng cùng revision mô hình trên mọi worker và khi embedding câu hỏi.

Nếu ZIP thực tế là `pack1.zip` và bạn đặt `PACK_ID = "pack1"`, worker tự chuẩn hóa
mã thành `pack_pack1`: kết quả là `vectors_pack_pack1.npy` và `metadata_pack_pack1.json`.
Đường dẫn ZIP truyền rõ ràng nên vẫn đọc đúng `pack1.zip`.

## 3. Gộp các pack

1. Chờ đủ 5 cặp file kết quả (10 file).
2. Mở [merge_vector_packs.ipynb](ipynb/merge_vector_packs.ipynb), chạy clone, cài thư viện và mount Drive.
3. Kiểm tra `INPUT_DIR`, `OUTPUT_DIR` và danh sách `EXPECTED_PACK_IDS`.
4. Chạy ô kiểm tra và gộp.

Với tên file hiện tại của bạn là `vectors_pack_pack1.npy` đến `vectors_pack_pack5.npy`:

```python
EXPECTED_PACK_IDS = ["pack_pack1", "pack_pack2", "pack_pack3", "pack_pack4", "pack_pack5"]
```

Nếu tên file là `vectors_pack_01.npy` đến `vectors_pack_05.npy`, dùng:

```python
EXPECTED_PACK_IDS = ["pack_01", "pack_02", "pack_03", "pack_04", "pack_05"]
```

Kết quả nằm trong `MyDrive/RAG_Data/unified`:

- `tthc_unified.index`
- `tthc_unified_metadata.json`

Dòng FAISS `i` tương ứng với phần tử metadata `i`, bắt đầu từ 0. Không đổi thứ tự
metadata. Merger kiểm tra cặp file, số dòng, số chiều, ID trùng và vector không hợp lệ.
Vector được chuẩn hóa L2, chỉ mục dùng `IndexFlatIP(1024)` để tìm kiếm cosine.
Bước gộp chạy CPU/RAM; riêng ma trận và chỉ mục cần ít nhất `N * 1024 * 8` byte,
chưa tính metadata và bộ nhớ tạm. Không cần GPU.

## 4. Kết quả cũ hoặc chạy bị ngắt

Chương trình không ghi đè kết quả đã có. Nếu gói đã chạy thành công, chuyển sang
gói tiếp theo. Nếu chỉ có một file hoặc lần chạy bị ngắt, chuyển cặp chưa hoàn chỉnh
sang nơi khác rồi chạy lại. Không gộp trong lúc worker đang lưu kết quả.

## 5. Chạy trên máy cá nhân

Từ thư mục gốc repository, với Python 3.10 trở lên:

```sh
pip install -r requirements-embedding.txt
python -m src.embeddings.pack_worker --pack-id pack_01 --zip-path ./pack_01.zip --output-dir ./completed --no-mount
python -m src.vectordb.merge ./completed --output-dir ./unified
```

Máy chỉ gộp cần `pip install -r requirements-vector-db.txt`.
Các lệnh cũ `python colab_worker_embed.py` và `python merge_vector_packs.py` vẫn
chạy bằng cách chuyển tiếp tới module trong `src`.

Worker hỗ trợ `--scratch-dir`, `--max-extract-gib`, `--batch-size`, `--device`,
`--revision`, `--output-dir`; dùng `--help` để xem. Scratch được dọn sau khi dùng.
Notebook mount Drive trước khi gọi worker bằng subprocess, nên truyền `--no-mount`.

## 6. Chạy chatbot RAG và đánh giá

Mở [notebook Qwen + RAG](ipynb/base_rag/lqwen2_5_7B_rag.ipynb).
Có thể trỏ trực tiếp tới thư mục unified trên Drive hoặc ZIP chứa hai file unified.
Không cần tạo lại embedding tài liệu. Metadata lớn được chuyển dạng luồng sang SQLite.
Chi tiết: [hướng dẫn Colab](ipynb/base_rag/README.md) và [kiến trúc src](src/rag/README.md).

Kiểm thử offline: `python -m unittest discover -s tests -v`.
Tài liệu tham khảo: [BGE-M3](https://huggingface.co/BAAI/bge-m3),
[cosine trong FAISS](https://github.com/facebookresearch/faiss/wiki/MetricType-and-distances).
