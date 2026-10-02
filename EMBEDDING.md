# Đặc tả embedding và corpus

Tài liệu quy định pipeline tạo corpus FAISS trực tiếp từ dữ liệu chunk. Pipeline
chạy trong một tiến trình và không có tầng worker, pack hoặc bước hợp nhất trung gian.

## Điều kiện tiên quyết

```powershell
python -m pip install -e ".[embedding,vector]"
```

Đầu vào là một thư mục hoặc ZIP chứa file `.json`/`.txt`. Mỗi file có thể chứa
JSON object, JSON array hoặc JSON Lines. Mỗi chunk phải có các trường:
`chunk_id`, `source_file`, `source_code`, `procedure_name`, `section_type`,
`context_prefix`, `text_content` và `parent_section`.

## Tạo corpus

```powershell
python -m vigovbot embed Data/meta --output-dir Data/vector/unified
```

Nguồn ZIP cũng được hỗ trợ:

```powershell
python -m vigovbot embed Data/chunks.zip --output-dir Data/vector/unified --device cuda --batch-size 32
```

Pipeline thực hiện tuần tự:

1. Đọc và kiểm tra toàn bộ chunk, bao gồm tính duy nhất của `chunk_id`.
2. Phân giải revision BGE-M3 thành commit SHA bất biến.
3. Mã hóa chunk thành vector float32 1024 chiều.
4. Chuẩn hóa L2 và xây dựng FAISS `IndexFlatIP`.
5. Ghi metadata theo đúng thứ tự row của FAISS.
6. Công bố index, metadata và manifest theo giao dịch.

## Artifact đầu ra

| File | Nội dung |
|---|---|
| `tthc_unified.index` | FAISS index sử dụng inner product trên vector đã chuẩn hóa |
| `tthc_unified_metadata.json` | Metadata chunk theo thứ tự row của index |
| `corpus_manifest.json` | Model, revision, số dòng và SHA-256 của artifact |

Manifest được ghi sau cùng và là dấu hoàn tất của corpus. Pipeline không ghi đè
artifact đã tồn tại; thư mục đầu ra của mỗi lần tạo corpus phải mới hoặc rỗng.

## Tính toàn vẹn và an toàn

- ZIP bị path traversal, symlink, mục trùng hoặc vượt giới hạn giải nén bị từ chối.
- Metadata thiếu trường, ID trùng hoặc nội dung rỗng bị từ chối trước khi mã hóa.
- Vector sai shape, không hữu hạn hoặc bằng không bị từ chối.
- Khi CUDA hết bộ nhớ, batch size được giảm và chính các hàng chưa hoàn thành được chạy lại.
- Corpus chỉ được công bố sau khi index, metadata và manifest đều được tạo thành công.
- RAG xác minh checksum và revision trước khi nạp FAISS hoặc encoder truy vấn.

Checksum bảo vệ tính toàn vẹn, không xác minh tác giả. Chỉ nạp corpus từ nguồn
đáng tin cậy vì FAISS index là artifact nhị phân.

## Tài nguyên

Toàn bộ metadata và ma trận vector hiện được giữ trong bộ nhớ trong giai đoạn tạo
corpus. Riêng ma trận float32 cần xấp xỉ `N × 1024 × 4` byte; FAISS cần thêm một
bản dữ liệu tương đương. Cần đánh giá RAM/VRAM theo kích thước corpus thực tế.

## Colab

Notebook `ipynb/build_corpus.ipynb` gọi trực tiếp CLI trên một nguồn chunk duy
nhất. Notebook được sinh bằng `python scripts/build_colab_notebooks.py`.
