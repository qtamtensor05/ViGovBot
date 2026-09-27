# Embedding BGE-M3 và corpus

Cài `python -m pip install -e ".[embedding,vector]"` từ repository.
ZIP đầu vào chứa JSON array/object hoặc JSON Lines trong file `.json`/`.txt`.
Mỗi chunk có: `chunk_id`, `source_file`, `source_code`, `procedure_name`,
`section_type`, `context_prefix`, `text_content`, `parent_section`.

```powershell
python -m vigovbot embed --pack-id pack_01 --zip-path Data/packs/pack_01.zip --output-dir Data/vector/completed --no-mount
python -m vigovbot merge Data/vector/completed --output-dir Data/vector/unified
```

Worker phân giải model revision thành commit SHA trước khi encode. Với nhiều
worker, lấy SHA từ `manifest_pack_01.json` và dùng `--revision SHA` cho mọi pack
còn lại; tốt nhất chọn SHA chung trước khi chạy song song. Vector chưa chuẩn hóa
được lưu float32; merge chuẩn hóa L2 và tạo `IndexFlatIP`.

Đầu ra mỗi pack gồm ba file:

- `vectors_pack_01.npy`
- `metadata_pack_01.json`
- `manifest_pack_01.json`

Manifest ghi revision, số dòng, checksum vector/metadata và checksum ZIP đầu vào.
Merge từ chối file bị sửa, ID trùng, vector không hữu hạn/rỗng, thiếu metadata hoặc
các pack khác revision. Không ghi đè đầu ra đã có. Mỗi worker dùng pack riêng,
không để hai phiên cùng xử lý một pack vào một thư mục trên Drive.

Corpus gồm `tthc_unified.index`, `tthc_unified_metadata.json`, `corpus_manifest.json`.
Copy/nén đủ cả ba file. RAG kiểm tra manifest và tự dùng đúng revision khi
`embedding.revision: null`. Chỉ nhận index từ nguồn đáng tin cậy; checksum không
chứng minh tác giả hay bảo vệ trước nguồn cố ý tạo index độc hại.

Dữ liệu cũ dùng `--allow-legacy` khi merge và `data.allow_legacy_corpus: true` khi
truy vấn. Cờ này đánh dấu không xác minh được model; không bỏ qua kiểm tra checksum
của artifact đã có manifest. Chi tiết: [migration](docs/migration.md).

Worker đọc metadata của một pack vào RAM. Merge hiện giữ metadata và ma trận
vector trong RAM; cần chia pack/đánh giá tài nguyên phù hợp. Với N vector 1024 chiều,
riêng ma trận float32 và FAISS cần khoảng `N * 1024 * 8` byte, chưa tính metadata.
RAG chuyển metadata unified sang SQLite theo luồng; kiểm tra SHA-256 vẫn phải đọc
file và có thể mất thời gian với corpus lớn.

Colab: `ipynb/colab_worker_embed.ipynb` và `ipynb/merge_vector_packs.ipynb`.
Generator: `python scripts/build_colab_notebooks.py`. Chọn `GIT_REF` đã có trên
GitHub; thay đổi local chưa push không xuất hiện trên Colab.
