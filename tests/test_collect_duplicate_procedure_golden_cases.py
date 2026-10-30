import json
import tempfile
import unittest
from pathlib import Path

from scripts.collect_duplicate_procedure_golden_cases import (
    collect_cases,
    contains_name,
    load_groups,
    match_case,
)


def _row(test_id, question, name, code, history=None, standalone=None):
    return {
        "test_id": test_id,
        "taxonomy": {"turn_type": "follow_up" if history else "new_question"},
        "input": {"question": question, "chat_history": history or [], "metadata_filters": None},
        "ground_truth": {
            "ground_truth_standalone_query": standalone or question,
            "ground_truth_contexts": [f"[Thủ tục: {name} | Mã TTHC: {code} | Mục: TRÌNH TỰ]\nNội dung"],
        },
    }


def _write_group(root, index, folder, name, codes):
    root.mkdir(parents=True, exist_ok=True)
    (root / folder).mkdir()
    return {
        "group_id": f"duplicate-name-{index:03d}",
        "folder": folder,
        "procedure_name": name,
        "source_codes": codes,
    }


class CollectDuplicateProcedureGoldenCasesTest(unittest.TestCase):
    def test_contains_name_requires_token_boundary(self):
        self.assertTrue(contains_name("thủ tục cấp giấy mới", "cấp giấy"))
        self.assertTrue(contains_name("thủ tục cấp giấy tờ", "cấp giấy"))
        self.assertFalse(contains_name("thủ tục cấp giấychứng", "cấp giấy"))
        self.assertFalse(contains_name("thủ tục cấp giấy chứng", "cấp giấy chứng nhận"))

    def test_match_case_prefers_longest_normalized_name(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "groups"
            groups = [
                _write_group(root, 1, "tach-thua", "Tách thửa hoặc hợp thửa đất", ["1.1"]),
                _write_group(root, 2, "tach-thua-xa", "Tách thửa hoặc hợp thửa đất (cấp xã)", ["2.2"]),
            ]
            (root / "manifest.json").write_text(
                json.dumps({"group_count": 2, "groups": groups}, ensure_ascii=False), encoding="utf-8"
            )
            loaded = load_groups(root)
            assignment = match_case(
                _row("case", "Làm Tách thửa hoặc hợp thửa đất (cấp xã) cần gì?", "Tách thửa hoặc hợp thửa đất", "1.1"),
                loaded,
            )
            self.assertEqual([item.group.group_id for item in assignment], ["duplicate-name-002"])

    def test_collect_cases_writes_raw_cases_summary_and_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            duplicate_root = root / "duplicate"
            groups = [
                _write_group(duplicate_root, 1, "tach-thua", "Tách thửa hoặc hợp thửa đất", ["1.1", "1.2"]),
                _write_group(duplicate_root, 2, "tach-thua-xa", "Tách thửa hoặc hợp thửa đất (cấp xã)", ["2.2"]),
            ]
            (duplicate_root / "manifest.json").write_text(
                json.dumps({"group_count": 2, "groups": groups}, ensure_ascii=False), encoding="utf-8"
            )
            rows = [
                _row("in_group", "Thủ tục Tách thửa hoặc hợp thửa đất cần gì?", "Tách thửa hoặc hợp thửa đất", "1.1"),
                _row(
                    "outside_group",
                    "Còn gì nữa?",
                    "Tách thửa hoặc hợp thửa đất",
                    "9.9",
                    history=[{"role": "user", "content": "Tôi hỏi về Tách thửa hoặc hợp thửa đất."}],
                    standalone="Mã 9.9 cần gì?",
                ),
                _row(
                    "longer_name",
                    "Làm Tách thửa hoặc hợp thửa đất (cấp xã) cần gì?",
                    "Tách thửa hoặc hợp thửa đất (cấp xã)",
                    "2.2",
                ),
                _row("unrelated", "Thủ tục cấp hộ chiếu cần gì?", "Cấp hộ chiếu", "7.7"),
            ]
            dataset = root / "golden.jsonl"
            raw_lines = [json.dumps(row, ensure_ascii=False) for row in rows]
            dataset.write_text("\n".join(raw_lines) + "\n", encoding="utf-8")

            manifest = collect_cases(dataset, duplicate_root)

            self.assertEqual((manifest["case_count"], manifest["assignment_count"]), (3, 3))
            self.assertEqual((manifest["code_in_group_count"], manifest["code_outside_group_count"]), (2, 1))
            first = duplicate_root / "tach-thua"
            self.assertEqual(
                (first / "golden_cases.jsonl").read_text(encoding="utf-8"),
                "\n".join((raw_lines[0], raw_lines[1])) + "\n",
            )
            summary = json.loads((first / "golden_cases_summary.json").read_text(encoding="utf-8"))
            self.assertEqual([entry["test_id"] for entry in summary], ["in_group", "outside_group"])
            self.assertTrue(summary[0]["code_in_group"])
            self.assertFalse(summary[1]["code_in_group"])
            self.assertEqual(summary[1]["matched_fields"], ["chat_history"])
            second = json.loads(
                (duplicate_root / "tach-thua-xa" / "golden_cases_summary.json").read_text(encoding="utf-8")
            )
            self.assertEqual([entry["test_id"] for entry in second], ["longer_name"])
            self.assertTrue(second[0]["code_in_group"])


if __name__ == "__main__":
    unittest.main()
