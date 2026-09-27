"""Experiment manifests and resumable JSONL results."""

import json
import os
import platform
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from uuid import uuid4
from vigovbot.artifacts import output_lock


def runtime_identity():
    packages = {}
    for name in ("vigovbot", "numpy", "faiss-cpu", "sentence-transformers", "transformers", "torch", "requests"):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    return {"python": platform.python_version(), "platform": platform.system(), "packages": packages}


def read_results(path, repair_tail=False):
    """Khôi phục dòng cuối bị ngắt; không bỏ qua lỗi JSON nằm giữa file."""
    path = Path(path)
    if not path.exists():
        return []
    rows = []
    with path.open("rb") as handle:
        while True:
            offset = handle.tell()
            line = handle.readline()
            if not line:
                break
            try:
                if line.strip():
                    rows.append(json.loads(line))
            except (ValueError, UnicodeDecodeError):
                if repair_tail and not handle.read(1) and not line.endswith(b"\n"):
                    with path.open("r+b") as writer:
                        writer.truncate(offset)
                    break
                raise ValueError(f"Kết quả JSONL bị lỗi tại byte {offset}: {path}") from None
    return rows


def append_result(path, value):
    path = Path(path)
    # Một bản ghi hợp lệ nhưng thiếu newline vẫn có thể xuất hiện sau gián đoạn.
    with path.open("ab+") as handle:
        handle.seek(0, 2)
        if handle.tell():
            handle.seek(-1, 2)
            if handle.read(1) != b"\n":
                handle.write(b"\n")
        handle.write((json.dumps(value, ensure_ascii=False) + "\n").encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())


def ensure_run(output_dir, configuration):
    with output_lock(output_dir, ".manifest.lock"):
        _ensure_run(output_dir, configuration)


def _ensure_run(output_dir, configuration):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    path = output / "run_manifest.json"
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != configuration:
            raise ValueError("Cấu hình/dữ liệu đã đổi. Chọn OUTPUT_DIR mới để không trộn kết quả.")
    else:
        if (output / "raw_predictions.jsonl").exists():
            raise ValueError("Có kết quả cũ nhưng thiếu run_manifest.json; chọn OUTPUT_DIR mới")
        temporary = output / f".manifest-{uuid4().hex}.partial"
        try:
            temporary.write_text(json.dumps(configuration, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
