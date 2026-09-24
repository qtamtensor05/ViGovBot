"""Tạo các notebook chỉ làm nhiệm vụ clone và gọi mã Python trong src/."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def cell(kind, source):
    result = {"cell_type": kind, "metadata": {}, "source": source.strip().splitlines(keepends=True)}
    if kind == "code":
        result.update(execution_count=None, outputs=[])
    return result


CLONE = '''
from pathlib import Path
import subprocess
import sys
import os

REPO_URL = "https://github.com/qtamtensor05/ViGovBot.git"
GIT_REF = "codex/feat-multi-embedding-colab"  # Nhánh hiện tại; đổi main sau khi merge hoặc dùng commit cố định.
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
'''
DRIVE = '''
from google.colab import drive
drive.mount("/content/drive")
'''


def bootstrap(title, requirements):
    return [cell("markdown", f"# {title}\n\nNotebook chỉ clone dự án và gọi mã trong `src/`. Chọn **Runtime > Change runtime type > GPU** khi chạy mô hình. Chạy các ô từ trên xuống.\n\n**Trước khi chạy:** mã nguồn mới phải có trên GitHub; đặt `GIT_REF` đúng nhánh/tag/commit. Notebook không lấy được các thay đổi chỉ nằm trên máy cá nhân. Không đặt token GitHub trong URL hoặc lưu trong notebook. Dự án riêng tư cần cấu hình xác thực Git của phiên Colab trước.\n\n## 1. Clone dự án\nNếu đổi phiên bản mã sau khi đã import module, khởi động lại phiên Python trước khi tiếp tục."),
            cell("code", CLONE),
            cell("markdown", "## 2. Cài thư viện\nCài từ file requirements của đúng phiên bản dự án vừa clone."),
            cell("code", f'subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "{requirements}"], check=True)'),
            cell("markdown", "## 3. Kết nối Google Drive\nChọn tài khoản chứa dữ liệu và cấp quyền khi Colab yêu cầu."),
            cell("code", DRIVE)]


def save(path, cells, gpu=False):
    for i, item in enumerate(cells):
        item["id"] = f"cell-{i:02d}"
    metadata = {"colab": {"name": path.name, "provenance": []},
                "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                "language_info": {"name": "python"}}
    if gpu:
        metadata["accelerator"] = "GPU"
    path.write_text(json.dumps({"cells": cells, "nbformat": 4, "nbformat_minor": 5,
                                "metadata": metadata}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    cells = bootstrap("Qwen2.5:7B + RAG — clone dự án và đánh giá qa_test", "requirements-rag.txt")
    cells.extend([
        cell("markdown", """
## 4. Tạo cấu hình cho phiên Colab
Mã pipeline nằm trong `src/`; file `rag_config.yaml` chứa cấu hình mặc định.
Ô này chỉ thay đường dẫn/tài nguyên rồi lưu bản cấu hình riêng bên ngoài checkout.

Chuẩn bị trên Drive: `RAG_Data/unified.zip` chứa hai file unified, và `RAG_Data/qa_test/dataset.jsonl`.
Có thể dùng thư mục unified đã giải nén hoặc `qa_test.zip` chứa `dataset.jsonl` trong thư mục con.
Metadata 6 GB sẽ được đọc theo luồng sang SQLite trên ổ đĩa Colab, không nạp toàn bộ vào RAM.
"""),
        cell("code", '''
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
'''),
        cell("markdown", "## 5. Chuẩn bị Ollama\nHàm trong dự án cài Ollama khi cần, khởi động dịch vụ và tải Qwen2.5:7B. Lần đầu cần tải trọng số mô hình."),
        cell("code", '''
from src.utils.colab_runtime import ensure_ollama
ensure_ollama(config["llm"]["model"], config["llm"]["ollama_url"])
'''),
        cell("markdown", """
## 6. Chạy pipeline từ src
`run` thực hiện: chuẩn bị SQLite → nạp BGE-M3/FAISS → thử 5 câu → đánh giá → giải phóng mô hình → tính điểm và xuất báo cáo.
Giữ cùng cấu hình và thư mục kết quả để tiếp tục các câu chưa thành công nếu Colab bị ngắt.
Nếu đổi code, dữ liệu hoặc tham số, dùng `output_dir` mới.

Có thể đổi `COMMAND` thành `prepare`, `smoke`, `evaluate`, hoặc `report` để chạy riêng từng bước.
`report` dùng kết quả đã lưu, không cần nạp Qwen/BGE-M3. BERTScore mặc định CPU có thể chạy lâu.
"""),
        cell("code", '''
COMMAND = "run"
subprocess.run([sys.executable, "-m", "src.rag", "--config", str(CONFIG_PATH), COMMAND],
               cwd=REPO_DIR, check=True)
'''),
        cell("markdown", "## 7. Xem kết quả trên Drive\nBáo cáo gồm Exact Match, Accuracy chuẩn hóa, BLEU-4, ROUGE, BERTScore như baseline; thêm nguồn truy hồi và thời gian. Accuracy là khớp chuỗi, không phải đánh giá đầy đủ độ đúng pháp lý. Tổng hợp ghi rõ số câu còn thiếu nếu có lỗi."),
        cell("code", '''
import json
import pandas as pd
output = Path(config["data"]["output_dir"])
summary_path = output / "summary.json"
if summary_path.exists():
    display(pd.DataFrame([json.loads(summary_path.read_text(encoding="utf-8"))]))
print("Thư mục kết quả:", output)
print("Các file:", [p.name for p in output.iterdir()] if output.exists() else [])
'''),
    ])
    save(ROOT / "ipynb/base_rag/lqwen2_5_7B_rag.ipynb", cells, True)

    cells = bootstrap("Tạo embedding BGE-M3 cho một pack ZIP", "requirements-embedding.txt")
    cells.extend([
        cell("markdown", "## 4. Chọn pack và chạy\nĐặt các pack ZIP trong `MyDrive/RAG_Data`. Mỗi phiên xử lý một pack khác nhau. Đổi `PACK_ID` và chạy lại ô này cho pack tiếp theo. Prefix đã có sẽ không bị lặp; khi thiếu VRAM, mã worker tự giảm batch và thử lại."),
        cell("code", '''
PACK_ID = "pack_01"
DATA_DIR = Path("/content/drive/MyDrive/RAG_Data")
OUTPUT_DIR = DATA_DIR / "completed"
BATCH_SIZE = 32
MODEL_REVISION = None
command = [sys.executable, "-m", "src.embeddings.pack_worker", "--pack-id", PACK_ID,
           "--zip-path", str(DATA_DIR / f"{PACK_ID}.zip"), "--output-dir", str(OUTPUT_DIR),
           "--batch-size", str(BATCH_SIZE), "--device", "cuda", "--no-mount"]
if MODEL_REVISION:
    command += ["--revision", MODEL_REVISION]
subprocess.run(command, cwd=REPO_DIR, check=True)
'''),
        cell("markdown", "Sau khi đủ các cặp vector/metadata, chạy notebook `merge_vector_packs.ipynb`. File đã có sẽ không bị ghi đè; chuyển kết quả chưa hoàn chỉnh sang nơi khác trước khi chạy lại.")
    ])
    save(ROOT / "ipynb/colab_worker_embed.ipynb", cells, True)

    cells = bootstrap("Gộp các pack vector thành FAISS unified", "requirements-vector-db.txt")
    cells.extend([
        cell("markdown", "## 4. Kiểm tra danh sách pack và gộp\nKhông cần GPU, nhưng cần đủ RAM cho ma trận và chỉ mục cuối. Chờ mọi worker hoàn tất trước khi gộp. Với tên `vectors_pack_pack1.npy`, mã tương ứng là `pack_pack1`; sửa danh sách dưới đây theo file thực tế."),
        cell("code", '''
from src.vectordb.merge import discover_pairs
INPUT_DIR = Path("/content/drive/MyDrive/RAG_Data/completed")
OUTPUT_DIR = Path("/content/drive/MyDrive/RAG_Data/unified")
EXPECTED_PACK_IDS = ["pack_pack1", "pack_pack2", "pack_pack3", "pack_pack4", "pack_pack5"]
pairs = discover_pairs(INPUT_DIR)
found = {p.stem.removeprefix("vectors_") for p, _ in pairs}
if found != set(EXPECTED_PACK_IDS):
    raise ValueError(f"Danh sách pack không khớp: đã có {sorted(found)}, cần {EXPECTED_PACK_IDS}")
subprocess.run([sys.executable, "-m", "src.vectordb.merge", str(INPUT_DIR), "--output-dir", str(OUTPUT_DIR)],
               cwd=REPO_DIR, check=True)
'''),
        cell("markdown", "Kết quả: `tthc_unified.index` và `tthc_unified_metadata.json`. Notebook RAG nhận trực tiếp thư mục `unified` hoặc ZIP chứa hai file này.")
    ])
    save(ROOT / "ipynb/merge_vector_packs.ipynb", cells)


if __name__ == "__main__":
    main()
