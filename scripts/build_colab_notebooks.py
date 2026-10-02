"""Tạo notebook Colab với một ô cấu hình tập trung cho người dùng."""

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
import os
import subprocess
import sys

REPO_DIR = Path(REPO_DIR)
if not REPO_DIR.exists():
    subprocess.run(["git", "clone", REPO_URL, str(REPO_DIR)], check=True)
else:
    origin = subprocess.check_output(
        ["git", "-C", str(REPO_DIR), "remote", "get-url", "origin"], text=True
    ).strip()
    if origin != REPO_URL:
        raise RuntimeError("REPO_DIR đang trỏ tới repository khác")
    changes = subprocess.check_output(
        ["git", "-C", str(REPO_DIR), "status", "--porcelain"], text=True
    )
    if changes.strip():
        raise RuntimeError("Checkout Colab có thay đổi chưa lưu")
subprocess.run(["git", "-C", str(REPO_DIR), "fetch", "origin", GIT_REF], check=True)
subprocess.run(["git", "-C", str(REPO_DIR), "checkout", "--detach", "FETCH_HEAD"], check=True)
os.chdir(REPO_DIR)
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))
print("Commit:", subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip())
"""


def bootstrap(title, extras, settings):
    return [
        cell("markdown", f"# {title}\n\nChạy lần lượt các mục từ trên xuống."),
        cell("markdown", "## 1. Cấu hình\nKhai báo input, output và tham số cần thay đổi cho lab."),
        cell("code", settings),
        cell("markdown", "## 2. Tải mã nguồn\nClone hoặc cập nhật mã nguồn theo cấu hình ở Mục 1."),
        cell("code", CLONE),
        cell("markdown", f"## 3. Cài thư viện\nCài nhóm thư viện `{extras}`."),
        cell(
            "code",
            f'subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-e", ".[{extras}]"], cwd=REPO_DIR, check=True)',
        ),
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
            {"cells": cells, "nbformat": 4, "nbformat_minor": 5, "metadata": metadata},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def build_ingestion():
    settings = """
# @title 1. Cấu hình input/output
# @markdown **Mã nguồn**
REPO_URL = "https://github.com/qtamtensor05/ViGovBot.git"  # @param {type:"string"}
GIT_REF = "main"  # @param {type:"string"}
REPO_DIR = "/content/ViGovBot"  # @param {type:"string"}

# @markdown **Input**
INPUT_MODE = "Google Drive"  # @param ["Google Drive", "Upload"]
INPUT_PATH = "/content/drive/MyDrive/ViGovBot/Data"  # @param {type:"string"}
PIPELINE_CONFIG = "configs/pipeline.yaml"  # @param {type:"string"}

# @markdown **Output**
OUTPUT_DIR = "/content/ViGovBot_outputs"  # @param {type:"string"}
DOWNLOAD_OUTPUT = True  # @param {type:"boolean"}
"""
    cells = bootstrap("Lab PDF → metadata/chunks", "pdf", settings)
    cells.extend(
        [
            cell("markdown", "## 4. Chuẩn bị input\nMount Drive hoặc tải PDF lên theo `INPUT_MODE`."),
            cell(
                "code",
                """
from google.colab import drive, files

if INPUT_MODE == "Google Drive":
    drive.mount("/content/drive")
    input_path = Path(INPUT_PATH)
else:
    input_path = Path("/content/ViGovBot_uploaded")
    input_path.mkdir(exist_ok=True)
    for name, content in files.upload().items():
        if Path(name).name != name or not name.lower().endswith(".pdf"):
            raise ValueError(f"Tên file không hợp lệ: {name}")
        destination = input_path / name
        if destination.exists():
            raise FileExistsError(f"File đã tồn tại: {destination}")
        destination.write_bytes(content)

output_dir = Path(OUTPUT_DIR)
print("Input:", input_path)
print("Output:", output_dir)
""",
            ),
            cell("markdown", "## 5. Chạy lab\nTrích xuất PDF và tạo metadata/chunks."),
            cell(
                "code",
                """
subprocess.run(
    [sys.executable, "-m", "vigovbot", "ingest", str(input_path),
     "--config", str(REPO_DIR / PIPELINE_CONFIG), "--output-dir", str(output_dir)],
    cwd=REPO_DIR,
    check=True,
)
""",
            ),
            cell("markdown", "## 6. Nhận output\nNén kết quả và tải xuống khi được bật ở Mục 1."),
            cell(
                "code",
                """
import shutil

archive = shutil.make_archive("/content/ViGovBot_outputs", "zip", root_dir=output_dir)
print("Output:", output_dir)
if DOWNLOAD_OUTPUT:
    files.download(archive)
""",
            ),
        ]
    )
    save(ROOT / "ipynb/parse_metadata.ipynb", cells)


def build_rag():
    settings = """
# @title 1. Cấu hình input/output
# @markdown **Mã nguồn**
REPO_URL = "https://github.com/qtamtensor05/ViGovBot.git"  # @param {type:"string"}
GIT_REF = "main"  # @param {type:"string"}
REPO_DIR = "/content/ViGovBot"  # @param {type:"string"}

# @markdown **Input**
CORPUS_PATH = "/content/drive/MyDrive/RAG_Data/unified.zip"  # @param {type:"string"}
DATASET_PATH = "/content/drive/MyDrive/RAG_Data/qa_test/dataset.jsonl"  # @param {type:"string"}
DATASET_ZIP = ""  # @param {type:"string"}
MODEL_REVISION = ""  # @param {type:"string"}

# @markdown **Output**
CACHE_DIR = "/content/tthc_rag_cache"  # @param {type:"string"}
OUTPUT_DIR = "/content/drive/MyDrive/RAG_Data/qwen2_5_7b_rag_results"  # @param {type:"string"}

# @markdown **Tham số chạy**
COMMAND = "run"  # @param ["run", "prepare", "smoke", "evaluate", "report"]
EMBEDDING_DEVICE = "cpu"  # @param ["cpu", "cuda"]
TOP_K = 5  # @param {type:"integer"}
MAX_CASES = 0  # @param {type:"integer"}
SMOKE_TEST_N = 5  # @param {type:"integer"}
BERTSCORE_DEVICE = "cpu"  # @param ["cpu", "cuda"]
BERTSCORE_BATCH_SIZE = 1  # @param {type:"integer"}
"""
    cells = bootstrap("Lab Qwen2.5:7B + RAG", "rag,evaluation", settings)
    cells.extend(
        [
            cell("markdown", "## 4. Kết nối dữ liệu\nMount Google Drive chứa input và output."),
            cell("code", 'from google.colab import drive\ndrive.mount("/content/drive")'),
            cell("markdown", "## 5. Tạo cấu hình chạy\nTạo YAML từ các giá trị ở Mục 1."),
            cell(
                "code",
                """
import yaml

config = yaml.safe_load((REPO_DIR / "rag_config.yaml").read_text(encoding="utf-8"))
config["data"].update({
    "unified_source": CORPUS_PATH,
    "dataset_path": DATASET_PATH or None,
    "dataset_zip": DATASET_ZIP or None,
    "cache_dir": CACHE_DIR,
    "output_dir": OUTPUT_DIR,
})
config["embedding"]["device"] = EMBEDDING_DEVICE
config["embedding"]["revision"] = MODEL_REVISION or None
config["retrieval"]["top_k"] = TOP_K
config["evaluation"].update({
    "max_cases": MAX_CASES or None,
    "smoke_test_n": SMOKE_TEST_N,
    "bertscore_device": BERTSCORE_DEVICE,
    "bertscore_batch_size": BERTSCORE_BATCH_SIZE,
})
CONFIG_PATH = Path("/content/rag_colab.yaml")
CONFIG_PATH.write_text(
    yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8"
)
print("Config:", CONFIG_PATH)
""",
            ),
            cell("markdown", "## 6. Chuẩn bị mô hình\nKhởi động Ollama và tải model khi cần."),
            cell(
                "code",
                'from vigovbot.utils.colab_runtime import ensure_ollama\nensure_ollama(config["llm"]["model"], config["llm"]["ollama_url"])',
            ),
            cell("markdown", "## 7. Chạy lab\nThực thi lệnh đã chọn ở Mục 1."),
            cell(
                "code",
                """
subprocess.run(
    [sys.executable, "-m", "vigovbot.rag", "--config", str(CONFIG_PATH), COMMAND],
    cwd=REPO_DIR,
    check=True,
)
""",
            ),
            cell("markdown", "## 8. Xem output\nHiển thị báo cáo tổng hợp và danh sách file kết quả."),
            cell(
                "code",
                """
import json
import pandas as pd

output = Path(OUTPUT_DIR)
summary_path = output / "summary.json"
if summary_path.exists():
    display(pd.DataFrame([json.loads(summary_path.read_text(encoding="utf-8"))]))
print("Output:", output)
print("Files:", [p.name for p in output.iterdir()] if output.exists() else [])
""",
            ),
        ]
    )
    save(ROOT / "ipynb/base_rag/lqwen2_5_7B_rag.ipynb", cells, True)


def build_corpus():
    settings = """
# @title 1. Cấu hình input/output
# @markdown **Mã nguồn**
REPO_URL = "https://github.com/qtamtensor05/ViGovBot.git"  # @param {type:"string"}
GIT_REF = "main"  # @param {type:"string"}
REPO_DIR = "/content/ViGovBot"  # @param {type:"string"}

# @markdown **Input**
SOURCE = "/content/drive/MyDrive/RAG_Data/chunks.zip"  # @param {type:"string"}
MODEL_REVISION = ""  # @param {type:"string"}

# @markdown **Output**
OUTPUT_DIR = "/content/drive/MyDrive/RAG_Data/unified"  # @param {type:"string"}

# @markdown **Tham số chạy**
BATCH_SIZE = 32  # @param {type:"integer"}
DEVICE = "cuda"  # @param ["cuda", "cpu"]
"""
    cells = bootstrap("Lab tạo corpus BGE-M3 và FAISS", "embedding,vector", settings)
    cells.extend(
        [
            cell("markdown", "## 4. Kết nối dữ liệu\nMount Google Drive chứa input và output."),
            cell("code", 'from google.colab import drive\ndrive.mount("/content/drive")'),
            cell("markdown", "## 5. Chạy lab\nMã hóa chunks và tạo corpus FAISS."),
            cell(
                "code",
                """
command = [
    sys.executable, "-m", "vigovbot", "embed", SOURCE,
    "--output-dir", OUTPUT_DIR,
    "--batch-size", str(BATCH_SIZE),
    "--device", DEVICE,
]
if MODEL_REVISION:
    command += ["--revision", MODEL_REVISION]
subprocess.run(command, cwd=REPO_DIR, check=True)
print("Output:", OUTPUT_DIR)
""",
            ),
        ]
    )
    save(ROOT / "ipynb/build_corpus.ipynb", cells, True)


def main():
    build_ingestion()
    build_rag()
    build_corpus()


if __name__ == "__main__":
    main()
