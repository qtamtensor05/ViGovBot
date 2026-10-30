import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from scripts.group_duplicate_procedure_metadata import duplicate_groups, export_groups, folder_name


def _row(test_id, code, name):
    return {
        "test_id": test_id,
        "ground_truth": {
            "ground_truth_contexts": [f"[Thủ tục: {name} | Mã TTHC: {code} | Mục: HỒ SƠ]\nNội dung"]
        },
    }


class GroupDuplicateProcedureMetadataTest(unittest.TestCase):
    def test_duplicate_groups_normalize_punctuation_and_diacritics(self):
        rows = [_row("a", "1.000001", "Cấp giấy."), _row("b", "2.000002", "CẤP GIẤY")]
        groups = duplicate_groups(rows)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["source_codes"], ["1.000001", "2.000002"])
        self.assertRegex(folder_name(groups[0]["normalized_name"]), r"^cap-giay--[0-9a-f]{10}$")

    def test_export_groups_writes_manifest_and_metadata_per_code(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            dataset = root / "golden.jsonl"
            rows = [_row("a", "1.000001", "Cấp giấy"), _row("b", "2.000002", "Cấp giấy")]
            dataset.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
            database = root / "metadata.sqlite"
            with closing(sqlite3.connect(database)) as connection:
                connection.execute("CREATE TABLE chunks (row_id INTEGER, payload TEXT)")
                for row_id, code in enumerate(("1.000001", "2.000002"), 1):
                    payload = {"chunk_id": f"c{row_id}", "source_code": code, "procedure_name": "Cấp giấy", "section_type": "required_documents"}
                    connection.execute("INSERT INTO chunks VALUES (?, ?)", (row_id, json.dumps(payload, ensure_ascii=False)))
                connection.commit()
            pdf_root = root / "pdf"
            pdf_root.mkdir()
            for code in ("1.000001", "2.000002"):
                (pdf_root / f"{code}.pdf").write_bytes(b"%PDF-1.4\n%%EOF\n")
            output = root / "groups"
            manifest = export_groups(dataset, database, output, [pdf_root])
            self.assertEqual((manifest["group_count"], manifest["procedure_count"], manifest["metadata_chunk_count"]), (1, 2, 2))
            self.assertEqual(manifest["pdf_count"], 2)
            self.assertEqual(len(manifest["source_dataset"]["sha256"]), 64)
            self.assertEqual(len(manifest["source_metadata"]["sha256"]), 64)
            self.assertTrue((output / "README.md").is_file())
            group_dir = next(path for path in output.iterdir() if path.is_dir())
            group = json.loads((group_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(group["source_codes"], ["1.000001", "2.000002"])
            self.assertTrue((group_dir / "1.000001.json").is_file())
            self.assertTrue((group_dir / "2.000002.json").is_file())
            self.assertTrue((group_dir / "1.000001.pdf").is_file())
            self.assertEqual(len(group["procedures"][0]["pdf_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
