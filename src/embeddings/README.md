# Embeddings — tạo vector bằng BGE-M3

Module tạo vector cho tài liệu và nạp encoder cho câu hỏi. Mô hình hiện dùng
`BAAI/bge-m3`, đầu ra dense vector 1024 chiều. Tính tương thích giữa vector tài liệu
và câu hỏi phụ thuộc vào cùng mô hình và phiên bản trọng số.

## Thành phần và đầu vào/đầu ra

| File | Vai trò | Đầu vào → đầu ra |
| --- | --- | --- |
| [pack_worker.py](pack_worker.py) | Xử lý một pack tài liệu | ZIP chứa chunks → `.npy` và metadata `.json` |
| [embedder.py](embedder.py) | `load_encoder()` | Model/revision/device → đối tượng SentenceTransformer |

Schema chunks do [chunking](../chunking/README.md#schema-json) định nghĩa.
Worker nhận JSON object, JSON array hoặc JSON Lines trong file `.json`/`.txt`.

## Luồng tạo vector tài liệu

1. Chuẩn hóa `PACK_ID`, tìm ZIP và kiểm tra file kết quả chưa tồn tại.
2. Giải nén vào thư mục tạm; chặn đường dẫn không an toàn và giới hạn dung lượng.
3. Đọc file theo thứ tự tên, giữ thứ tự bản ghi; kiểm tra schema và ID trùng.
4. Dùng `text_content`; chỉ thêm `context_prefix` nếu văn bản chưa bắt đầu bằng tiền tố đó.
5. Encode theo batch, ghi vào ma trận float32 đã cấp phát. Nếu CUDA OOM, giảm batch và thử lại cùng các dòng.
6. Ghi tạm rồi công bố `vectors_<pack_id>.npy` và `metadata_<pack_id>.json`; dọn thư mục giải nén.

Dòng vector `i` luôn đi với phần tử metadata `i`. Worker không sửa metadata gốc.
Vector tài liệu được chuẩn hóa L2 ở [bước gộp](../vectordb/README.md), không phải worker.

## Cấu hình worker

Worker nhận tham số qua CLI; `load_encoder()` nhận cấu hình từ bộ điều phối RAG.

| Tham số worker | Ý nghĩa |
| --- | --- |
| `--batch-size` | Mặc định 32; tự giảm khi CUDA OOM |
| `--device` | Tự chọn nếu bỏ trống; có thể đặt `cuda` hoặc `cpu` |
| `--revision` | Cố định phiên bản trọng số |
| `--scratch-dir` | Thư mục giải nén tạm |
| `--max-extract-gib` | Giới hạn dung lượng giải nén, mặc định 10 GiB |

`pack_01` sinh `vectors_pack_01.npy`; nhập `pack1` sẽ được chuẩn hóa thành
`pack_pack1`, sinh `vectors_pack_pack1.npy`. Mã pack là định danh ghép cặp vector và metadata.

## Encoder câu hỏi và giới hạn

[rag_config.yaml](../../rag_config.yaml) dùng nhóm `embedding.model/revision/device`;
mặc định encoder câu hỏi chạy CPU. [Retrieval](../retrieval/README.md) gọi encode
cho từng câu hỏi rồi chuẩn hóa L2. Không tạo lại vector tài liệu khi truy vấn.

Worker giữ metadata và ma trận của một pack trong RAM. Kích thước pack quyết định
bộ nhớ dữ liệu; batch ảnh hưởng bộ nhớ suy luận. Nếu CUDA OOM vẫn xảy ra với batch
bằng 1, worker báo lỗi.
Đầu vào vượt giới hạn mô hình bị thư viện cắt bớt; giới hạn BGE-M3 là 8192 token.

[Kiến trúc tổng thể](../README.md)
