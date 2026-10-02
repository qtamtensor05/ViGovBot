# Hướng dẫn migration và tương thích ngược

Tài liệu áp dụng khi chuyển từ namespace, cấu hình hoặc artifact của phiên bản
cũ sang package `vigovbot` và hợp đồng artifact hiện hành.

## Namespace, điểm chạy và cấu hình

1. Cài package từ repository: `python -m pip install -e ".[test,dev]"`
   cho kiểm thử; chọn thêm nhóm runtime theo README.
2. Lớp tương thích `src.*` đã được bỏ. Đổi import sang `vigovbot.*`, kể cả
   đường dẫn module trong mock/patch của kiểm thử.
3. Đổi `python -m src.rag` thành `python -m vigovbot rag`. `main.py` gọi
   trực tiếp package mới; cần cài package trước khi chạy.
4. Template chính nằm trong `configs/`. `config.yaml`, `rag_config.yaml` và
   các cấu hình gốc vẫn sử dụng được. YAML trong module cũ đã được bỏ.
   Đường dẫn tương đối tính từ YAML.
5. Dữ liệu mẫu trước đây ở `pipeline_observe_steps/` chuyển tới
   `examples/pipeline_observe_steps/`. Notebook giữ đường dẫn `ipynb/` để không
   làm mất liên kết cũ. Generator chuyển sang `scripts/build_colab_notebooks.py`.

Các file cài thư viện trung gian ở thư mục gốc đã được bỏ. Cài trực tiếp nhóm
trong `pyproject.toml`: `.[pdf]`, `.[embedding]`, `.[vector]`, `.[rag,evaluation]`
hoặc `.[test,dev]`. Khi cần đúng phiên bản đã kiểm chứng, dùng file tương ứng
trong `locks/` theo [hướng dẫn môi trường](environments.md).

## Corpus không có manifest

Khuyến nghị tạo lại corpus bằng lệnh `vigovbot embed` để ghi nhận revision model
thực tế. Không tự viết manifest có revision suy đoán chỉ để vượt kiểm tra. Hai
vector cùng 1024 chiều không chứng minh chúng dùng cùng không gian embedding.

Nếu cần dùng dữ liệu cũ trong giai đoạn chuyển đổi:

```yaml
data:
  unified_source: ../Data/vector/legacy-unified
  cache_dir: ../outputs/legacy_cache
  allow_legacy_corpus: true
```

Corpus legacy không có thông tin embedding đã xác minh. Cờ tương thích không bỏ
qua checksum nếu corpus đã có manifest. Đối với corpus cũ chỉ có index/metadata,
cờ trên cho phép đọc trực tiếp và vẫn kiểm tra cấu trúc FAISS, metadata cùng ánh
xạ số dòng. Log luôn báo hạn chế này.

## Kết quả đánh giá và cache cũ

Pipeline version đã tăng, định danh corpus chuyển sang checksum nội dung.
Chọn `output_dir` mới khi chạy phiên bản này; không trộn prediction cũ với
manifest mới. Giữ nguyên kết quả cũ để đối chiếu và dùng checkout phiên bản
cũ khi cần tạo lại báo cáo của lần chạy cũ. Cache mới tự chọn thư mục theo
định danh nội dung/manifest; không cần xóa cache cũ.

## Notebook Colab

Notebook cài editable package với nhóm dependency phù hợp, thêm `REPO_DIR / "src"`
vào đường dẫn import của kernel hiện tại và chỉ sử dụng `vigovbot.*`.
Sinh lại cả ba notebook bằng `python scripts/build_colab_notebooks.py`.
Notebook RAG lấy template từ `configs/rag.yaml`.

Chỉ chạy notebook sau khi thay đổi đã được đưa lên GitHub. Đặt `GIT_REF` thành
commit đã phát hành/merge; mặc định `main` tiện dùng nhưng không cố định thí nghiệm.
Copy đủ ba file corpus khi chuyển lên Drive hoặc nén ZIP.
