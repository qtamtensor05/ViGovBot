# Môi trường và tái lập

Nguồn khai báo dependency duy nhất là `pyproject.toml`. Cài trực tiếp các nhóm
thư viện từ thư mục gốc repository; không cần file cài đặt trung gian.

| Extra | Mục đích |
|---|---|
| `pdf` | Trích xuất PDF; OCR thật cần Tesseract/tessdata riêng |
| `embedding` | Tạo vector BGE-M3, cần trọng số mô hình |
| `vector` | Merge, FAISS/SQLite, không cần tải mô hình |
| `rag` | Encoder, retrieval và Ollama client |
| `evaluation` | Metric và biểu đồ, BERTScore cần trọng số riêng |
| `test` | Test offline với FAISS/SQLite thật, encoder/HTTP được mô phỏng |
| `dev` | Ruff để kiểm tra mã và định dạng |

```powershell
python -m pip install -e ".[pdf]"
python -m pip install -e ".[embedding,vector]"
python -m pip install -e ".[rag,evaluation]"
python -m pip install -e ".[test,dev]"
```

Chọn lệnh phù hợp với công việc. Nếu cần cài toàn bộ:

```powershell
python -m pip install -e ".[pdf,embedding,vector,rag,evaluation,test,dev]"
```

Khai báo Python hỗ trợ: 3.10–3.14. Môi trường kiểm chứng cục bộ hiện tại:
Windows x64, Python 3.14. CI cấu hình thêm Windows/Linux, Python 3.11/3.14;
chưa coi những tổ hợp này là đã chạy thành công cho tới khi có kết quả CI.

## Lock theo nền tảng

`locks/*-windows-py314.txt` chứa phiên bản của cả dependency trực tiếp và
bắc cầu theo nhóm, xuất từ môi trường đã cài. Không sao chép toàn bộ `pip freeze`
của môi trường cá nhân. Không dùng lock Windows cho Colab/Linux.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r locks/test-windows-py314.txt
.venv\Scripts\python -m pip install --no-deps -e .
.venv\Scripts\python -m unittest discover -s tests -v
```

RAG: thay lock trên bằng `locks/rag-windows-py314.txt`. Embedding/merge dùng
`locks/embedding-windows-py314.txt`. PDF dùng `locks/pdf-windows-py314.txt`.
Các file trong `locks/` giữ phiên bản đã kiểm chứng; `pyproject.toml` khai báo
nhóm thư viện và khoảng phiên bản được phép.

Các lock này cố định phiên bản, chưa khóa hash của từng wheel. Chúng không
khóa driver GPU, CUDA, Ollama, model weights hoặc Tesseract. Với thí nghiệm
GPU/Colab, tạo môi trường riêng, cài extras phù hợp, kiểm thử rồi xuất lock:

```powershell
python scripts/export_lock.py --extras rag,evaluation --output locks/rag-local.txt
```

Script chỉ xuất dependency hợp lệ đang cài, không tự giải quyết hoặc nâng cấp
phiên bản. Chạy `python -m pip check` trước khi chốt. Commit lock kèm tên OS,
Python, thiết bị, phiên bản Ollama và lệnh benchmark trong báo cáo thí nghiệm.

## Lệnh kiểm chứng

```powershell
python -m pip check
python -m ruff check src/vigovbot scripts tests main.py colab_worker_embed.py merge_vector_packs.py
python -m ruff check --select S src/vigovbot
python -m ruff format --check src/vigovbot scripts tests main.py colab_worker_embed.py merge_vector_packs.py
python -m unittest discover -s tests -v
python scripts/demo_offline.py
python -m pip wheel --no-deps --wheel-dir dist .
python scripts/check_wheel.py
```

`scripts/check_clean_env.py` tạo venv tạm trên Windows/Python 3.14, cài test
lock và chạy lại test/demo; cần mạng để tải dependency, không tải model.
Test/demo dùng thư mục tạm, không sửa corpus hoặc kết quả nghiên cứu trong `Data/`.
