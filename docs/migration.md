# Chuyển từ cấu trúc cũ

## Mã nguồn và cấu hình

1. Cài package từ repository: `python -m pip install -e ".[test,dev]"`
   cho kiểm thử; chọn thêm nhóm runtime theo README.
2. Import mới dùng `vigovbot.*`; các import `src.*` cũ vẫn chạy trong checkout.
3. `main.py`, `colab_worker_embed.py`, `merge_vector_packs.py` và
   `python -m src.rag` vẫn được giữ. CLI mới: `python -m vigovbot`.
4. Template chính nằm trong `configs/`. `config.yaml`, `rag_config.yaml` và
   YAML trong module cũ còn để tương thích. Đường dẫn tương đối tính từ YAML.
5. Dữ liệu mẫu trước đây ở `pipeline_observe_steps/` chuyển tới
   `examples/pipeline_observe_steps/`. Notebook giữ đường dẫn `ipynb/` để không
   làm mất liên kết cũ. Generator chuyển sang `scripts/build_colab_notebooks.py`.

Các file cài thư viện trung gian ở thư mục gốc đã được bỏ. Cài trực tiếp nhóm
trong `pyproject.toml`: `.[pdf]`, `.[embedding]`, `.[vector]`, `.[rag,evaluation]`
hoặc `.[test,dev]`. Khi cần đúng phiên bản đã kiểm chứng, dùng file tương ứng
trong `locks/` theo [hướng dẫn môi trường](environments.md).

## Pack/corpus đã có nhưng thiếu manifest

Khuyến nghị tạo lại pack bằng worker mới để có revision model thực tế. Không
tự viết manifest có revision suy đoán chỉ để vượt kiểm tra. Hai vector cùng
1024 chiều không chứng minh chúng dùng cùng không gian embedding.

Nếu cần dùng dữ liệu cũ trong giai đoạn chuyển đổi:

```powershell
python -m vigovbot merge Data/vector/completed --output-dir Data/vector/legacy-unified --allow-legacy
```

Trong bản cấu hình riêng cho corpus cũ:

```yaml
data:
  unified_source: ../Data/vector/legacy-unified
  cache_dir: ../outputs/legacy_cache
  allow_legacy_corpus: true
```

Corpus legacy được ghi rõ `embedding: null`; bật cờ không bỏ qua checksum
nếu đã có manifest, và không cho phép trộn các revision đã biết là khác nhau.
Đối với corpus cũ chỉ có index/metadata, cờ trên cho phép đọc trực tiếp và vẫn
kiểm tra cấu trúc FAISS, metadata và ánh xạ số dòng. Log luôn báo hạn chế này.

## Kết quả đánh giá và cache

Pipeline version đã tăng, định danh corpus chuyển sang checksum nội dung.
Chọn `output_dir` mới khi chạy phiên bản này; không trộn prediction cũ với
manifest mới. Giữ nguyên kết quả cũ để đối chiếu và dùng checkout phiên bản
cũ khi cần tạo lại báo cáo của lần chạy cũ. Cache mới tự chọn thư mục theo
định danh nội dung/manifest; không cần xóa cache cũ.

## Colab

Chỉ chạy notebook sau khi thay đổi đã được đưa lên GitHub. Đặt `GIT_REF` thành
commit đã phát hành/merge; mặc định `main` tiện dùng nhưng không cố định thí nghiệm.
Copy đủ ba file của mỗi pack/corpus khi chuyển lên Drive hoặc nén ZIP.
Trong cùng một đợt embedding, dùng cùng commit SHA cho `MODEL_REVISION` ở mọi worker.
