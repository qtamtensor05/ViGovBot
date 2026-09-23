# Embeddings — tạo vector bằng BGE-M3

Module tạo vector cho tài liệu và nạp encoder cho câu hỏi. Mô hình hiện dùng
`BAAI/bge-m3`, đầu ra dense vector 1024 chiều. Dùng cùng mô hình và revision
ở bước tạo dữ liệu và bước truy vấn.

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

## Cách chạy

Từ thư mục gốc repository:

```sh
pip install -r requirements-embedding.txt
python -m src.embeddings.pack_worker --pack-id pack_01 --zip-path pack_01.zip --output-dir completed --no-mount
```

Trên Colab dùng [notebook worker](../../ipynb/colab_worker_embed.ipynb), notebook
clone mã và mount Drive trước khi gọi module. Hướng dẫn 5 pack: [EMBEDDING.md](../../EMBEDDING.md).

| Tham số worker | Ý nghĩa |
| --- | --- |
| `--batch-size` | Mặc định 32; tự giảm khi CUDA OOM |
| `--device` | Tự chọn nếu bỏ trống; có thể đặt `cuda` hoặc `cpu` |
| `--revision` | Cố định phiên bản trọng số |
| `--scratch-dir` | Thư mục giải nén tạm |
| `--max-extract-gib` | Giới hạn dung lượng giải nén, mặc định 10 GiB |

`pack_01` sinh `vectors_pack_01.npy`; nhập `pack1` sẽ được chuẩn hóa thành
`pack_pack1`, sinh `vectors_pack_pack1.npy`. Dùng tên tương ứng khi gộp.

## Encoder câu hỏi và giới hạn

[rag_config.yaml](../../rag_config.yaml) dùng nhóm `embedding.model/revision/device`;
mặc định encoder câu hỏi chạy CPU. [Retrieval](../retrieval/README.md) gọi encode
cho từng câu hỏi rồi chuẩn hóa L2. Không tạo lại vector tài liệu khi truy vấn.

Worker vẫn giữ metadata và ma trận của một pack trong RAM, nên cần chia pack vừa bộ nhớ.
Giảm batch chỉ giảm bộ nhớ inference. Nếu một đoạn vẫn OOM, dùng GPU lớn hơn hoặc CPU.
Đầu vào vượt giới hạn mô hình bị thư viện cắt bớt; giới hạn BGE-M3 là 8192 token.

[Quay lại tổng quan](../README.md)
