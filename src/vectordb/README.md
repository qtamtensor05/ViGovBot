# Vector DB — FAISS và SQLite

Module có hai công việc riêng: gộp vector của các pack thành unified, và chuẩn bị
unified để truy vấn với metadata lớn. FAISS giữ vector; SQLite giữ nội dung theo ID.

## Thành phần

| File | Vai trò |
| --- | --- |
| [merge.py](merge.py) | Ghép các pack, chuẩn hóa L2, tạo `IndexFlatIP(1024)` |
| [vector_store.py](vector_store.py) | `prepare_corpus()`: chép chỉ mục và chuyển metadata sang SQLite |

## Gộp pack

Đầu vào là một thư mục chứa các cặp `vectors_pack_*.npy` và `metadata_pack_*.json`.

1. Tìm cặp theo mã pack và sắp theo tên; từ chối file thiếu cặp.
2. Kiểm tra shape `(N, 1024)`, kiểu số thực, số dòng metadata và ID trùng giữa các pack.
3. Từ chối vector zero, NaN/vô cực hoặc không biểu diễn được bằng float32.
4. Nối bằng `np.vstack`, chuẩn hóa L2 rồi thêm vào `faiss.IndexFlatIP`.
5. Lưu `tthc_unified.index` và `tthc_unified_metadata.json`, không ghi đè kết quả có sẵn.

```sh
pip install -r requirements-vector-db.txt
python -m src.vectordb.merge completed --output-dir unified
```

CLI chỉ biết các cặp hiện có; không phát hiện pack thiếu cả hai file.
[Notebook merger](../../ipynb/merge_vector_packs.ipynb) kiểm tra thêm danh sách
`EXPECTED_PACK_IDS`. Hai file không được công bố nguyên tử cùng lúc: chờ worker
hoàn tất trước khi gộp, và chuyển kết quả chưa hoàn chỉnh sang nơi khác khi cần chạy lại.

## Chuẩn bị dữ liệu để truy vấn

`prepare_corpus(source, cache_root)` nhận ZIP hoặc thư mục unified, dùng
[ingestion/unified.py](../ingestion/README.md#đọc-unified-cho-rag) để mở luồng dữ liệu.

1. Lập định danh nguồn từ đường dẫn, kích thước, thời gian sửa; ZIP có thêm thông tin thành viên và CRC.
2. Tìm cache tương ứng; dùng lại khi có đủ file và marker `ready.json` hợp lệ.
3. Chép chỉ mục vào cache; kiểm tra 1024 chiều, inner product và không rỗng.
4. Đọc mảng metadata từng bản ghi bằng ijson, ghi SQLite theo batch.
5. Kiểm tra số bản ghi bằng số vector, hoàn tất DB rồi ghi marker.

Kết quả trả về: `(index_path, db_path, info)`; `info` chứa số vector và định danh nguồn.
Nhóm cấu hình: `data.unified_source`, `data.cache_dir` trong [rag_config.yaml](../../rag_config.yaml).
Có thể gọi qua CLI mà chưa tải BGE-M3/Qwen:

```sh
python -m src.rag --config rag_config.yaml prepare
```

## Ánh xạ và bộ nhớ

SQLite có bảng `chunks(row_id PRIMARY KEY, chunk_id UNIQUE, payload)`.
`row_id = i` tương ứng vector FAISS `i` và phần tử JSON `i`, bắt đầu từ 0.
Payload giữ `chunk_id`, `source_file`, `source_code`, `procedure_name`,
`section_type`, `context_prefix`, `text_content`; không lưu `parent_section`.
File unified gốc không bị sửa.

Bước gộp cần RAM cho cả ma trận và index, tối thiểu `N * 1024 * 8` byte, cộng metadata
và bộ nhớ tạm. Bước chuẩn bị truy vấn đọc JSON theo luồng, nhưng vẫn phải nạp chỉ mục
để kiểm tra. SQLite nằm trên ổ đĩa; [retriever](../retrieval/README.md) lấy nội dung theo ID.
Cache trên `/content` mất khi Colab reset. Kiểm tra count/shape không phát hiện được
metadata đã bị người dùng đảo thứ tự; luôn giữ đúng cặp unified.

[Quay lại tổng quan](../README.md)
