from __future__ import annotations
from vigovbot.utils.jsonl import iter_jsonl, iter_jsonl_stream
import zipfile
from pathlib import Path
from vigovbot.ingestion.unified import zip_member


def load_cases(dataset_path=None, dataset_zip=None):
    """Đúng schema qa_test trong baseline; ZIP cho phép thư mục qa_test/ bên trong."""
    if dataset_path and Path(dataset_path).is_file():
        rows = [row for _, row in iter_jsonl(dataset_path, blank_lines="skip")]
    elif dataset_zip and Path(dataset_zip).is_file():
        with zipfile.ZipFile(dataset_zip) as archive:
            with archive.open(zip_member(archive, "dataset.jsonl")) as handle:
                rows = [row for _, row in iter_jsonl_stream(
                    handle, source=f"{dataset_zip}:{handle.name}", blank_lines="skip"
                )]
    else:
        raise FileNotFoundError("Đặt DATASET_PATH tới qa_test/dataset.jsonl hoặc DATASET_ZIP tới qa_test.zip")
    seen = set()
    for i, row in enumerate(rows):
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"]:
            raise ValueError(f"Case {i}: id phải là chuỗi không rỗng")
        if row["id"] in seen:
            raise ValueError(f"ID câu hỏi trùng: {row['id']}")
        seen.add(row["id"])
        for section, keys in (("question", ("text", "type", "difficulty")), ("ground_truth", ("answer",))):
            if not isinstance(row.get(section), dict) or any(not isinstance(row[section].get(k), str) for k in keys):
                raise ValueError(f"Case {row['id']}: sai schema {section}")
        if not row["question"]["text"].strip():
            raise ValueError(f"Case {row['id']}: câu hỏi rỗng")
    if not rows:
        raise ValueError("Bộ câu hỏi rỗng")
    return rows
