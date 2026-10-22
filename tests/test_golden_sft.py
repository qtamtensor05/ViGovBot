import copy
import tempfile
import unittest
from pathlib import Path

from tests.dependencies import skip_missing_dependency

try:
    from vigovbot.training.data import read_jsonl
    from vigovbot.training.golden_sft import convert_golden, convert_record, encode_jsonl, load_golden
except ModuleNotFoundError as exc:
    skip_missing_dependency(exc)


def golden(identifier="TC_1", history=None):
    return {"test_id": identifier, "input": {"chat_history": history or [], "question": " Hỏi e\u0302́?\n"},
            "ground_truth": {"expected_answer": " Không đủ thông tin.\n", "ground_truth_contexts": ["SECRET"]},
            "taxonomy": {"is_unanswerable": True}}


class GoldenSftTests(unittest.TestCase):
    def test_single_turn_and_unanswerable_preserved(self):
        row = golden()
        before = copy.deepcopy(row)
        result = convert_record(row, "source:1")
        self.assertEqual(result, {"id": "TC_1", "messages": [
            {"role": "user", "content": row["input"]["question"]},
            {"role": "assistant", "content": row["ground_truth"]["expected_answer"]}]})
        self.assertEqual(row, before)
        self.assertNotIn(b"SECRET", encode_jsonl([result]))

    def test_follow_up(self):
        history = [{"role": "user", "content": "Câu trước"}, {"role": "assistant", "content": "Đáp trước"}]
        for turns in (history, history * 2):
            row = golden(history=turns)
            self.assertEqual(convert_record(row, "source:2")["messages"][:-2], turns)

    def test_invalid_history(self):
        for history in (None, {}, [dict(role="user", content="a")],
                        [dict(role="assistant", content="a"), dict(role="user", content="b")],
                        [dict(role="user", content=" "), dict(role="assistant", content="b")],
                        [dict(role="user", content="a", label="bad"), dict(role="assistant", content="b")],
                        [dict(role="user", content="a"), dict(role="assistant", content="b")] * 3):
            row = golden()
            row["input"]["chat_history"] = history
            with self.subTest(history=history), self.assertRaisesRegex(ValueError, "source:7: test_id='TC_1'"):
                convert_record(row, "source:7")

    def test_empty_question_answer_and_id(self):
        for field, owner in (("question", "input"), ("expected_answer", "ground_truth")):
            for value in ("", " \n", None, 12):
                row = golden()
                row[owner][field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    convert_record(row, "source:1")
        row = golden("")
        with self.assertRaises(ValueError):
            convert_record(row, "source:1")

    def test_duplicate_and_malformed_location(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.jsonl"
            path.write_bytes(encode_jsonl([golden(), golden()]))
            with self.assertRaisesRegex(ValueError, r"input.jsonl:2: test_id='TC_1': duplicate"):
                load_golden(path)
            path.write_bytes(b"{invalid}\n")
            with self.assertRaisesRegex(ValueError, r"input.jsonl:1:.*test_id=<unavailable>"):
                load_golden(path)

    def test_deterministic_files_and_training_reader(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, identifier in (("train", "TC_1"), ("val", "TC_2")):
                (root / f"{name}_golden.jsonl").write_bytes(encode_jsonl([golden(identifier)]))
            self.assertEqual(convert_golden(root, root / "out"), {"train": 1, "validation": 1})
            convert_golden(root, root / "out2")
            convert_golden(root, root / "out")
            for name in ("train_sft.jsonl", "validation_sft.jsonl"):
                payload = (root / "out" / name).read_bytes()
                self.assertEqual(payload, (root / "out2" / name).read_bytes())
                self.assertTrue(payload.endswith(b"\n"))
                self.assertNotIn(b"\\u", payload)
                self.assertEqual(len(read_jsonl(root / "out" / name)), 1)
            self.assertFalse((root / "out" / "test_sft.jsonl").exists())
            (root / "val_golden.jsonl").write_bytes(encode_jsonl([golden()]))
            with self.assertRaisesRegex(ValueError, "ID overlaps train"):
                convert_golden(root, root / "bad")
            self.assertFalse((root / "bad").exists())

    def test_invalid_validation_leaves_output_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "train_golden.jsonl").write_bytes(encode_jsonl([golden()]))
            (root / "val_golden.jsonl").write_bytes(b"{}\n")
            with self.assertRaises(ValueError):
                convert_golden(root, root / "out")
            self.assertFalse((root / "out").exists())

    def test_existing_artifact_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, identifier in (("train", "TC_1"), ("val", "TC_2")):
                (root / f"{name}_golden.jsonl").write_bytes(encode_jsonl([golden(identifier)]))
            out = root / "out"
            out.mkdir()
            (out / "validation_sft.jsonl").write_bytes(b"existing user artifact\n")
            with self.assertRaisesRegex(ValueError, "Refusing to replace"):
                convert_golden(root, out)
            self.assertEqual((out / "validation_sft.jsonl").read_bytes(), b"existing user artifact\n")
            self.assertFalse((out / "train_sft.jsonl").exists())
