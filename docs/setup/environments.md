# Môi trường thực thi và khả năng tái lập

> Tài liệu này dành cho môi trường phát triển/training/evaluation chuyên biệt.
> Runtime web và hỏi đáp thông thường dùng [Docker Compose](docker.md), không
> yêu cầu virtual environment hay Ollama trên Windows.

Tài liệu quy định các nhóm dependency, nền tảng hỗ trợ, lock file và quy trình
kiểm chứng môi trường.

## Nhóm dependency

Nguồn khai báo dependency duy nhất là `pyproject.toml`. Cài trực tiếp các nhóm
thư viện từ thư mục gốc repository; không cần file cài đặt trung gian.

| Extra | Mục đích |
|---|---|
| `pdf` | Trích xuất PDF; OCR thật cần Tesseract/tessdata riêng |
| `embedding` | Mã hóa chunk bằng BGE-M3, cần trọng số mô hình |
| `vector` | Tạo và đọc FAISS/SQLite |
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

Cài đặt toàn bộ nhóm dependency:

```powershell
python -m pip install -e ".[pdf,embedding,vector,rag,evaluation,test,dev]"
```

## Nền tảng hỗ trợ

`requires-python >=3.10,<3.15` là phạm vi package core, không phải cam kết mọi
extra/GPU wheel đều hỗ trợ mọi nền tảng. Python 3.12/Linux x86_64 là môi trường
Docker hiện dùng; Windows/Python 3.14 có lock test/RAG resolve riêng.

| Phạm vi | Chính sách |
|---|---|
| Core/CLI | Python 3.10–3.14; dependency resolver vẫn quyết định phiên bản cài được |
| Test/RAG CPU Windows 3.14 | Có lock riêng; không suy ra QLoRA GPU được hỗ trợ |
| Training/GPU | Dùng Python 3.12 làm baseline; cần wheel của toàn bộ stack, CUDA và smoke trên host đích |
| Python/OS khác với GPU pins | Chưa xác nhận; không dùng claim core để cam kết wheel tồn tại |

`torch==2.9.1` thuộc extra `gpu` và nằm trong range `torch>=2.2,<3` của RAG;
đây không phải xung đột ràng buộc. Extra `training` chứa công cụ dữ liệu/report,
training GPU cần thêm `[training,gpu]`. Thiếu wheel theo Python/OS khác với
xung đột version. `huggingface-hub>=0.34,<1` nay là dependency trực tiếp vì
artifact revision/preflight import nó; không dựa vào dependency bắc cầu.

## Cài đặt tái lập bằng lock file

`locks/*-windows-py314.txt` chứa phiên bản của cả dependency trực tiếp và
bắc cầu theo nhóm, resolve từ `pyproject.toml` bằng `uv pip compile`. Không sao chép toàn bộ `pip freeze`
của môi trường cá nhân. Không dùng lock Windows cho Colab/Linux.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r locks/test-windows-py314.txt
.venv\Scripts\python -m pip install --no-deps -e .
.venv\Scripts\python -m unittest discover -s tests -v
```

RAG: thay lock trên bằng `locks/rag-windows-py314.txt`. Tạo corpus dùng
`locks/embedding-windows-py314.txt`. PDF dùng `locks/pdf-windows-py314.txt`.
Các lock được resolve lại ngày 2026-10-18 với Transformers 4.57.3 cho các
nhóm sử dụng Transformers. Resolve thành công không chứng minh cài đặt hoặc
runtime GPU đã pass. `locks/inference-linux-py312.txt` dành riêng cho Docker
Linux x86_64/Python 3.12, extras `rag,gpu`; Dockerfile cài trực tiếp lock này.
Bản lock mới chưa được kiểm chứng bằng clean install/model inference.

Các lock này cố định phiên bản, chưa khóa hash của từng wheel. Chúng không
khóa driver GPU, CUDA, Ollama, model weights hoặc Tesseract. Với thí nghiệm
GPU/Colab, tạo môi trường riêng, cài extras phù hợp, kiểm thử rồi xuất lock:

```powershell
python scripts/export_lock.py --extras rag,evaluation --output locks/rag-local.txt
```

Script chỉ xuất dependency hợp lệ đang cài, không tự giải quyết hoặc nâng cấp
phiên bản. Chạy `python -m pip check` trước khi chốt. Commit lock kèm tên OS,
Python, thiết bị, phiên bản Ollama và lệnh benchmark trong báo cáo thí nghiệm.

## Quy trình kiểm chứng

```powershell
python -m pip check
python -m ruff check src/vigovbot scripts tests main.py
python -m ruff check --select S src/vigovbot
python -m ruff format --check src/vigovbot scripts tests main.py
python -m unittest discover -s tests -v
python scripts/demo_offline.py
python -m pip wheel --no-deps --wheel-dir dist .
python scripts/check_wheel.py
```

`scripts/check_clean_env.py` tạo venv tạm bằng interpreter đang chạy, chọn
Scripts/python.exe trên Windows hoặc bin/python trên POSIX. Mặc định resolve
`.[test,dev]`; `--lock PATH` dùng lock do người gọi chọn đúng nền tảng. Script
chạy pip check, suite và demo; cần mạng cài dependency, không tải model.
Test/demo dùng thư mục tạm, không sửa corpus hoặc kết quả nghiên cứu trong `Data/`.

## Tái tạo lock bằng resolver

Dùng `uv pip compile pyproject.toml --python-version 3.14
--python-platform x86_64-pc-windows-msvc --extra test --extra dev
--output-file locks/test-windows-py314.txt` (viết trên một dòng).
Các nhóm còn lại: `pdf`; `embedding,vector`; `rag,evaluation` (mỗi extra dùng
một cờ `--extra`). Docker dùng Python 3.12, platform
`x86_64-unknown-linux-gnu`, extras `rag,gpu`, output
`locks/inference-linux-py312.txt`. Không nâng riêng Transformers mà bỏ qua
ràng buộc `tokenizers`, `huggingface-hub`, PEFT và sentence-transformers.

`check_wheel.py --wheel-dir PATH` cài wheel vào thư mục tạm ngoài checkout,
kiểm tra defaults và cả console entrypoint `vigov`/`vigovbot` với help của
train/eva/data/doctor. `python main.py` không argument chỉ hiện unified help;
muốn ingestion phải gọi lệnh tường minh, ví dụ `vigov ingest`.
