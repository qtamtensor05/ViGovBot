"""Tạo các notebook chỉ làm nhiệm vụ clone và gọi mã Python trong src/."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def cell(kind, source):
    result = {"cell_type": kind, "metadata": {}, "source": source.strip().splitlines(keepends=True)}
    if kind == "code":
        result.update(execution_count=None, outputs=[])
    return result


CLONE = """
from pathlib import Path
import subprocess
import sys
import os

REPO_URL = "https://github.com/qtamtensor05/ViGovBot.git"
GIT_REF = "main"  # Nhánh hiện tại; đổi main sau khi merge hoặc dùng commit cố định.
REPO_DIR = Path("/content/ViGovBot")

if not REPO_DIR.exists():
    subprocess.run(["git", "clone", REPO_URL, str(REPO_DIR)], check=True)
else:
    origin = subprocess.check_output(["git", "-C", str(REPO_DIR), "remote", "get-url", "origin"], text=True).strip()
    if origin != REPO_URL:
        raise RuntimeError("REPO_DIR đang trỏ tới dự án khác; chọn thư mục mới")
    changes = subprocess.check_output(["git", "-C", str(REPO_DIR), "status", "--porcelain"], text=True)
    if changes.strip():
        raise RuntimeError("Có thay đổi trong checkout Colab; lưu lại hoặc chọn REPO_DIR mới trước khi cập nhật")
subprocess.run(["git", "-C", str(REPO_DIR), "fetch", "origin", GIT_REF], check=True)
subprocess.run(["git", "-C", str(REPO_DIR), "checkout", "--detach", "FETCH_HEAD"], check=True)
os.chdir(REPO_DIR)
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))
print("Commit đang chạy:", subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip())
"""
DRIVE = """
from google.colab import drive
drive.mount("/content/drive")
"""


def bootstrap(title, extras):
    return [
        cell(
            "markdown",
            f"# {title}\n\nNotebook chỉ clone dự án và gọi mã trong `src/`. Chọn **Runtime > Change runtime type > GPU** khi chạy mô hình. Chạy các ô từ trên xuống.\n\n**Trước khi chạy:** mã nguồn mới phải có trên GitHub; đặt `GIT_REF` đúng nhánh/tag/commit. Notebook không lấy được các thay đổi chỉ nằm trên máy cá nhân. Không đặt token GitHub trong URL hoặc lưu trong notebook. Dự án riêng tư cần cấu hình xác thực Git của phiên Colab trước.\n\n## 1. Clone dự án\nNếu đổi phiên bản mã sau khi đã import module, khởi động lại phiên Python trước khi tiếp tục.",
        ),
        cell("code", CLONE),
        cell(
            "markdown",
            f"## 2. Cài thư viện\nCài nhóm `{extras}` được khai báo trong `pyproject.toml` của phiên bản dự án vừa clone.",
        ),
        cell(
            "code",
            f'subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-e", ".[{extras}]"], cwd=REPO_DIR, check=True)',
        ),
        cell("markdown", "## 3. Kết nối Google Drive\nChọn tài khoản chứa dữ liệu và cấp quyền khi Colab yêu cầu."),
        cell("code", DRIVE),
    ]


def save(path, cells, gpu=False):
    for i, item in enumerate(cells):
        item["id"] = f"cell-{i:02d}"
    metadata = {
        "colab": {"name": path.name, "provenance": []},
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python"},
    }
    if gpu:
        metadata["accelerator"] = "GPU"
    path.write_text(
        json.dumps(
            {"cells": cells, "nbformat": 4, "nbformat_minor": 5, "metadata": metadata}, ensure_ascii=False, indent=2
        )
        + "\n",
        encoding="utf-8",
    )


def build_ingestion():
    cells = bootstrap("PDF → metadata/chunks", "pdf")[:-2]
    cells.extend(
        [
            cell(
                "markdown",
                "## 3. Chọn dữ liệu\nDùng thư mục PDF trên Drive hoặc tải file lên phiên Colab. OCR bản scan cần cài Tesseract và tessdata vie/eng riêng.",
            ),
            cell(
                "code",
                """
from google.colab import drive, files
USE_GOOGLE_DRIVE = False
if USE_GOOGLE_DRIVE:
    drive.mount("/content/drive")
    INPUT = Path("/content/drive/MyDrive/ViGovBot/Data")
else:
    INPUT = Path("/content/ViGovBot_uploaded")
    INPUT.mkdir(exist_ok=True)
    uploaded = files.upload()
    for name, content in uploaded.items():
        if Path(name).name != name or not name.lower().endswith(".pdf"):
            raise ValueError(f"Tên file không hợp lệ: {name}")
        destination = INPUT / name
        if destination.exists():
            raise FileExistsError(f"File đã tồn tại: {destination}")
        destination.write_bytes(content)
OUTPUT = Path("/content/ViGovBot_outputs")
""",
            ),
            cell(
                "markdown",
                "## 4. Chạy pipeline\nCLI quản lý bỏ qua file thành công, xử lý lại file lỗi và đưa dữ liệu chưa chắc chắn vào review. Nếu CLI báo lỗi, kiểm tra reports/review trước khi tạo corpus.",
            ),
            cell(
                "code",
                """
subprocess.run([sys.executable, "-m", "vigovbot", "ingest", str(INPUT),
                "--config", str(REPO_DIR / "configs/pipeline.yaml"),
                "--output-dir", str(OUTPUT)], cwd=REPO_DIR, check=True)
""",
            ),
            cell(
                "markdown",
                "## 5. Tải kết quả\nZIP này là bản sao toàn bộ output, kể cả reports/review. Chỉ đưa các JSON chunk đã kiểm tra vào bước tạo corpus.",
            ),
            cell(
                "code",
                """
import shutil
archive = shutil.make_archive("/content/ViGovBot_outputs", "zip", root_dir=OUTPUT)
files.download(archive)
""",
            ),
        ]
    )
    save(ROOT / "ipynb/parse_metadata.ipynb", cells)


def main():
    build_ingestion()
    cells = bootstrap("Qwen2.5:7B + RAG — clone dự án và đánh giá qa_test", "rag,evaluation")
    cells.extend(
        [
            cell(
                "markdown",
                """
## 4. Tạo cấu hình cho phiên Colab
Mã pipeline nằm trong `src/`; file `rag_config.yaml` chứa cấu hình mặc định.
Ô này chỉ thay đường dẫn/tài nguyên rồi lưu bản cấu hình riêng bên ngoài checkout.

Chuẩn bị trên Drive: `RAG_Data/unified.zip` chứa hai file unified, và `RAG_Data/qa_test/dataset.jsonl`.
Có thể dùng thư mục unified đã giải nén hoặc `qa_test.zip` chứa `dataset.jsonl` trong thư mục con.
Metadata 6 GB sẽ được đọc theo luồng sang SQLite trên ổ đĩa Colab, không nạp toàn bộ vào RAM.
""",
            ),
            cell(
                "code",
                """
import yaml
config = yaml.safe_load((REPO_DIR / "rag_config.yaml").read_text(encoding="utf-8"))
config["data"].update({
    "unified_source": "/content/drive/MyDrive/RAG_Data/unified.zip",
    "dataset_path": "/content/drive/MyDrive/RAG_Data/qa_test/dataset.jsonl",
    "dataset_zip": None,  # Nếu dùng ZIP: đặt dataset_path=None, dataset_zip=".../qa_test.zip".
    "cache_dir": "/content/tthc_rag_cache",
    "output_dir": "/content/drive/MyDrive/RAG_Data/qwen2_5_7b_rag_results",
})
config["embedding"]["device"] = "cpu"  # Dành VRAM cho Qwen; đổi cuda nếu đủ VRAM.
config["embedding"]["revision"] = None  # Cùng revision đã dùng khi tạo vector.
config["retrieval"]["top_k"] = 5
config["evaluation"]["max_cases"] = None  # None = toàn bộ 570 câu; thử 10 câu với output_dir riêng.
config["evaluation"]["smoke_test_n"] = 5
config["evaluation"]["bertscore_device"] = "cpu"
config["evaluation"]["bertscore_batch_size"] = 1
CONFIG_PATH = Path("/content/rag_colab.yaml")
CONFIG_PATH.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
print(CONFIG_PATH.read_text(encoding="utf-8"))
""",
            ),
            cell(
                "markdown",
                "## 5. Chuẩn bị Ollama\nHàm trong dự án cài Ollama khi cần, khởi động dịch vụ và tải Qwen2.5:7B. Lần đầu cần tải trọng số mô hình.",
            ),
            cell(
                "code",
                """
from vigovbot.utils.colab_runtime import ensure_ollama
ensure_ollama(config["llm"]["model"], config["llm"]["ollama_url"])
""",
            ),
            cell(
                "markdown",
                """
## 6. Chạy pipeline từ src
`run` thực hiện: chuẩn bị SQLite → nạp BGE-M3/FAISS → thử 5 câu → đánh giá → giải phóng mô hình → tính điểm và xuất báo cáo.
Giữ cùng cấu hình và thư mục kết quả để tiếp tục các câu chưa thành công nếu Colab bị ngắt.
Nếu đổi code, dữ liệu hoặc tham số, dùng `output_dir` mới.

Có thể đổi `COMMAND` thành `prepare`, `smoke`, `evaluate`, hoặc `report` để chạy riêng từng bước.
`report` dùng kết quả đã lưu, không cần nạp Qwen/BGE-M3. BERTScore mặc định CPU có thể chạy lâu.
""",
            ),
            cell(
                "code",
                """
COMMAND = "run"
subprocess.run([sys.executable, "-m", "vigovbot.rag", "--config", str(CONFIG_PATH), COMMAND],
               cwd=REPO_DIR, check=True)
""",
            ),
            cell(
                "markdown",
                "## 7. Xem kết quả trên Drive\nBáo cáo gồm Exact Match, Accuracy chuẩn hóa, BLEU-4, ROUGE, BERTScore như baseline; thêm nguồn truy hồi và thời gian. Accuracy là khớp chuỗi, không phải đánh giá đầy đủ độ đúng pháp lý. Tổng hợp ghi rõ số câu còn thiếu nếu có lỗi.",
            ),
            cell(
                "code",
                """
import json
import pandas as pd
output = Path(config["data"]["output_dir"])
summary_path = output / "summary.json"
if summary_path.exists():
    display(pd.DataFrame([json.loads(summary_path.read_text(encoding="utf-8"))]))
print("Thư mục kết quả:", output)
print("Các file:", [p.name for p in output.iterdir()] if output.exists() else [])
""",
            ),
        ]
    )
    save(ROOT / "ipynb/base_rag/lqwen2_5_7B_rag.ipynb", cells, True)

    cells = bootstrap("Tạo corpus BGE-M3 và FAISS", "embedding,vector")
    cells.extend(
        [
            cell(
                "markdown",
                "## 4. Tạo corpus\n`SOURCE` là thư mục hoặc ZIP chứa toàn bộ JSON chunk đã kiểm tra. Pipeline mã hóa dữ liệu và công bố trực tiếp FAISS index, metadata cùng manifest vào một thư mục corpus mới.",
            ),
            cell(
                "code",
                """
DATA_DIR = Path("/content/drive/MyDrive/RAG_Data")
SOURCE = DATA_DIR / "chunks.zip"
OUTPUT_DIR = DATA_DIR / "unified"
BATCH_SIZE = 32
MODEL_REVISION = None
command = [sys.executable, "-m", "vigovbot", "embed", str(SOURCE),
           "--output-dir", str(OUTPUT_DIR), "--batch-size", str(BATCH_SIZE), "--device", "cuda"]
if MODEL_REVISION:
    command += ["--revision", MODEL_REVISION]
subprocess.run(command, cwd=REPO_DIR, check=True)
""",
            ),
            cell(
                "markdown",
                "Đầu ra gồm `tthc_unified.index`, `tthc_unified_metadata.json` và `corpus_manifest.json`. Pipeline không ghi đè corpus đã tồn tại.",
            ),
        ]
    )
    save(ROOT / "ipynb/build_corpus.ipynb", cells, True)


if __name__ == "__main__":
    main()
