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
print("Commit:", subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip())
"""


def bootstrap(title, extras, settings):
    return [
        cell("markdown", f"# {title}\n\nChạy lần lượt các mục từ trên xuống."),
        cell("markdown", "## 1. Cấu hình\nKhai báo input, output và tham số cần thay đổi cho lab."),
        cell("code", settings),
        cell("markdown", "## 2. Tải mã nguồn\nClone hoặc cập nhật mã nguồn theo cấu hình ở Mục 1."),
        cell("code", CLONE),
        cell("markdown", f"## 3. Cài thư viện\nCài package `vigovbot` với nhóm `{extras}` và kích hoạt mã nguồn cho kernel hiện tại."),
        cell(
            "code",
            f'''subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-e", ".[{extras}]"], cwd=REPO_DIR, check=True)
# Kernel notebook đã chạy trước pip install nên cần kích hoạt src-layout ngay.
source_dir = str((REPO_DIR / "src").resolve())
if source_dir not in sys.path:
    sys.path.insert(0, source_dir)
import importlib
importlib.invalidate_caches()
import vigovbot
print("Package:", vigovbot.__file__)''',
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
    settings = '''
# @title 1. Cấu hình đánh giá QA v4 nhỏ
REPO_URL = "https://github.com/qtamtensor05/ViGovBot.git"  # @param {type:"string"}
GIT_REF = "main"  # @param {type:"string"}
REPO_DIR = "/content/ViGovBot"  # @param {type:"string"}
# @markdown Data không nằm trên GitHub; đặt bộ nhỏ đã giải nén trên Drive.
DATASET_DIR = "/content/drive/MyDrive/RAG_Data/rag_tthc_balanced_small"  # @param {type:"string"}
CORPUS_PATH = "/content/drive/MyDrive/RAG_Data/unified.zip"  # @param {type:"string"}
VIEW = "views_main_test.json"  # @param ["views_main_test.json", "views_challenge_test.json", "views_dev.json", "views_main_core_test.json", "views_main_sparse_test.json"]
SPLIT = "test"  # @param ["test", "dev"]
MODE = "free_running"  # @param ["free_running", "reference_history"]
NO_RETRIEVAL = False  # @param {type:"boolean"}
MODEL = "qwen2.5:7b"  # @param {type:"string"}
EMBEDDING_DEVICE = "cpu"  # @param ["cpu", "cuda"]
TOP_K = 5  # @param {type:"integer"}
# @markdown 10 để thử; 0 để chạy toàn bộ view. Không dùng limit cho báo cáo cuối.
LIMIT = 10  # @param {type:"integer"}
CACHE_DIR = "/content/tthc_rag_cache"  # @param {type:"string"}
OUTPUT_DIR = "/content/drive/MyDrive/RAG_Data/qa_v4_results"  # @param {type:"string"}
# @markdown Mỗi lần chạy dùng RUN_NAME mới; runner chưa hỗ trợ resume.
RUN_NAME = "small_main_smoke_rag"  # @param {type:"string"}
LEXICAL = True  # @param {type:"boolean"}
'''
    cells = bootstrap("Colab: đánh giá QA v4 nhỏ với Qwen/Ollama và RAG", "rag,evaluation", settings)
    cells[0] = cell("markdown", """# Đánh giá QA v4 nhỏ trên Colab
Chọn **Runtime → Change runtime type → GPU**, rồi chạy lần lượt.
Push mã nguồn mới lên GitHub và đặt `GIT_REF` đúng nhánh/commit trước khi chạy.
Đưa thư mục `rag_tthc_balanced_small` và corpus `unified.zip` lên Google Drive.
Notebook mặc định thử 10 câu; đặt `LIMIT = 0` để chạy toàn bộ view.
Kết quả ghi lên Drive từng câu, gồm câu hỏi và câu trả lời. Runner chưa hỗ trợ resume;
phiên bị ngắt cần dùng tên lượt chạy mới hoặc chia view thành các nhóm giữ nguyên hội thoại.
Baseline bật `NO_RETRIEVAL`; baseline không cần corpus. Chấm điểm không gọi model.
""")
    cells.extend([
        cell("markdown", "## 4. Mount Drive và kiểm tra đầu vào"),
        cell("code", '''
from google.colab import drive
drive.mount("/content/drive")
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "sacrebleu>=2,<3"], check=True)
from vigovbot.evaluation.multiturn import load_queries, validate_sequence
from vigovbot.qa_v4.io import read_jsonl
from vigovbot.qa_v4.__main__ import select_rows

dataset = Path(DATASET_DIR)
if LIMIT < 0 or TOP_K < 1:
    raise ValueError("LIMIT phải >= 0; TOP_K phải >= 1")
queries = load_queries(dataset / "runner_queries.jsonl", dataset / VIEW, SPLIT)
queries = queries[:LIMIT] if LIMIT else queries
cases = select_rows(read_jsonl(dataset / "cases.jsonl"), dataset, VIEW, SPLIT, LIMIT or None)
if [q["id"] for q in queries] != [c["id"] for c in cases]:
    raise ValueError("Câu hỏi và case chấm không khớp")
if MODE == "free_running":
    validate_sequence(queries)
if not NO_RETRIEVAL and not Path(CORPUS_PATH).exists():
    raise FileNotFoundError(CORPUS_PATH)
if not RUN_NAME or Path(RUN_NAME).name != RUN_NAME:
    raise ValueError("RUN_NAME phải là một tên thư mục")
output = Path(OUTPUT_DIR) / RUN_NAME
PREDICTIONS = output / "predictions.jsonl"
SCORES = output / "scores.json"
if PREDICTIONS.exists() or SCORES.exists():
    raise FileExistsError("Kết quả đã tồn tại; chọn RUN_NAME mới")
output.mkdir(parents=True, exist_ok=True)
print("Số câu:", len(queries), "| View:", VIEW, "| Baseline:", NO_RETRIEVAL)
print("Output:", output)
'''),
        cell("markdown", "## 5. Tạo cấu hình RAG và lưu thông tin lượt chạy"),
        cell("code", '''
import json
import yaml
config = yaml.safe_load((REPO_DIR / "configs/rag.yaml").read_text(encoding="utf-8"))
config["data"].update(unified_source=CORPUS_PATH, cache_dir=CACHE_DIR,
                      output_dir=str(output), dataset_path=None, dataset_zip=None)
config["embedding"]["device"] = EMBEDDING_DEVICE
config["llm"]["model"] = MODEL
config["retrieval"]["top_k"] = TOP_K
CONFIG_PATH = Path("/content/qa_v4_colab.yaml")
CONFIG_PATH.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
(output / "config.yaml").write_text(CONFIG_PATH.read_text(encoding="utf-8"), encoding="utf-8")
run_settings = {"git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                "dataset": DATASET_DIR, "view": VIEW, "split": SPLIT, "limit": LIMIT,
                "mode": MODE, "no_retrieval": NO_RETRIEVAL, "model": MODEL,
                "top_k": TOP_K, "lexical": LEXICAL}
(output / "notebook_run.json").write_text(json.dumps(run_settings, ensure_ascii=False, indent=2), encoding="utf-8")
'''),
        cell("markdown", "## 6. Cài Ollama, khởi động và tải model"),
        cell("code", '''
from vigovbot.utils.colab_runtime import ensure_ollama
ensure_ollama(config["llm"]["model"], config["llm"]["ollama_url"])
'''),
        cell("markdown", "## 7. Sinh câu trả lời và lưu từng câu lên Drive"),
        cell("code", '''
selection = ["--dataset", str(dataset), "--view", VIEW, "--split", SPLIT]
if LIMIT:
    selection += ["--limit", str(LIMIT)]
command = [sys.executable, "-m", "vigovbot", "qa-v4", "run", *selection,
           "--config", str(CONFIG_PATH), "--mode", MODE, "--out", str(PREDICTIONS)]
if NO_RETRIEVAL:
    command.append("--no-retrieval")
print("Bắt đầu sinh câu trả lời; tiến trình từng câu hiển thị bên dưới.", flush=True)
def stream_command(command):
    # Relay child output through the notebook kernel so Colab displays it reliably.
    with subprocess.Popen(command, cwd=REPO_DIR,
                          env=dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8"),
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, encoding="utf-8", errors="replace", bufsize=1) as process:
        print("PID tiến trình:", process.pid, flush=True)
        try:
            for line in process.stdout:
                print(line, end="", flush=True)
            return process.wait()
        except BaseException:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            raise

returncode = stream_command(command)
if returncode:
    print("Runner có lỗi. Nếu prediction tồn tại, vẫn chấm để báo coverage và lỗi.")
if not PREDICTIONS.exists():
    raise RuntimeError("Không có prediction; kiểm tra lỗi phía trên trước khi chấm")
'''),
        cell("markdown", "## 8. Chấm điểm offline với cùng view/split/limit"),
        cell("code", '''
command = [sys.executable, "-m", "vigovbot", "qa-v4", "score", *selection,
           "--top-k", str(TOP_K), "--predictions", str(PREDICTIONS), "--out", str(SCORES)]
if LEXICAL:
    command.append("--lexical")
print("Đang chấm điểm offline...", flush=True)
returncode = stream_command(command)
if returncode:
    raise RuntimeError(f"Chấm điểm thất bại: exit code {returncode}")
print("Đã chấm xong:", SCORES, flush=True)
'''),
        cell("markdown", "## 9. Xem câu hỏi, câu trả lời, đáp án tham chiếu và điểm\nRecall/MRR cần mapping chunk sang unit ID; correctness/faithfulness cần judgments ngữ nghĩa."),
        cell("code", '''
import pandas as pd
report = json.loads(SCORES.read_text(encoding="utf-8"))
display(pd.DataFrame([report["coverage"]]))
display(pd.DataFrame(report.get("overall_available", {})).T)
case_map = {c["id"]: c for c in cases}
metric_map = {m["id"]: m for m in report["per_case"]}
comparisons = []
for prediction in read_jsonl(PREDICTIONS):
    case = case_map.get(prediction["id"], {})
    comparisons.append({**metric_map.get(prediction["id"], {}),
                        "id": prediction["id"], "question": prediction.get("question", ""),
                        "answer": prediction.get("answer", ""),
                        "reference_answer": case.get("reference_answer", ""),
                        "error": prediction.get("error", ""),
                        "latency_seconds": prediction.get("latency_seconds")})
comparison = pd.DataFrame(comparisons)
comparison.to_csv(output / "comparison.csv", index=False, encoding="utf-8-sig")
display(comparison.head(10))
print("Kết quả:", output)
'''),
    ])
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
