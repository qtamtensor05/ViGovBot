import copy
import json
import tempfile
import unittest
from pathlib import Path

from vigovbot.training.golden_sft import encode_jsonl
from vigovbot.training.leakage_filter import filter_splits


def row(identifier, code, question, answer, chunk_suffix="metadata_identity_1_p1"):
    chunk_id = f"tthc_{code.replace('.', '_')}_sec_{chunk_suffix}"
    return {
        "test_id": identifier,
        "input": {"chat_history": [], "question": question, "metadata_filters": {"source_code": code}},
        "ground_truth": {
            "ground_truth_standalone_query": f"{question} Mã {code}",
            "ground_truth_context_ids": [chunk_id],
            "ground_truth_contexts": [f"Nguồn {code}: {answer}"],
            "expected_answer": answer,
        },
        "evaluation_plan": {"expected_action": "answer"},
    }


class LeakageFilterTests(unittest.TestCase):
    def test_strict_filter_removes_procedure_and_long_answer_leakage(self):
        repeated = "Nội dung dài " * 30
        train = [
            row("TRAIN_CODE", "1.000001", "Câu khác", "Đáp án riêng"),
            row("TRAIN_ANSWER", "2.000002", "Câu riêng", repeated),
            row("TRAIN_TEMPLATE", "3.000003", "Còn cơ quan thì sao?", "Một đáp án ngắn"),
        ]
        validation = [row("VAL_CLEAN", "4.000004", "Câu validation", "Đáp án validation")]
        test = [
            row("TEST_CODE", "1.000001", "Câu test", "Đáp án test", "procedure_step_2_p1"),
            row("TEST_ANSWER", "5.000005", "Câu test khác", repeated),
            row("TEST_TEMPLATE", "6.000006", "Còn cơ quan thì sao?", "Một đáp án khác"),
        ]
        before = copy.deepcopy(test)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "source", root / "clean"
            source.mkdir()
            (source / "train.jsonl").write_bytes(encode_jsonl(train))
            (source / "val.jsonl").write_bytes(encode_jsonl(validation))
            test_path = root / "test.jsonl"
            test_path.write_bytes(encode_jsonl(test))
            report = filter_splits(source, [test_path], output)
            kept = [json.loads(line) for line in (output / "train.jsonl").read_text(
                encoding="utf-8"
            ).splitlines()]
            excluded = [json.loads(line) for line in (output / "excluded_cases.jsonl").read_text(
                encoding="utf-8"
            ).splitlines()]
            self.assertEqual([item["test_id"] for item in kept], ["TRAIN_TEMPLATE"])
            self.assertEqual({item["test_id"] for item in excluded}, {"TRAIN_CODE", "TRAIN_ANSWER"})
            self.assertEqual(report["splits"]["train"]["excluded_records"], 2)
            self.assertEqual(
                report["splits"]["train"]["template_match_counts"]["final_question_exact_not_filter"], 1
            )
            self.assertTrue(all(value == 0 for value in report["postconditions"].values()
                                if isinstance(value, int)))
            self.assertEqual(test, before)

    def test_publication_is_deterministic_and_preserves_existing_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "source", root / "clean"
            source.mkdir()
            (source / "train.jsonl").write_bytes(encode_jsonl([
                row("TRAIN", "1.000001", "Train", "Answer")
            ]))
            (source / "val.jsonl").write_bytes(encode_jsonl([
                row("VAL", "2.000002", "Val", "Answer val")
            ]))
            test_path = root / "test.jsonl"
            test_path.write_bytes(encode_jsonl([row("TEST", "3.000003", "Test", "Answer test")]))
            first = filter_splits(source, [test_path], output)
            self.assertEqual(first, filter_splits(source, [test_path], output))
            (source / "train.jsonl").write_bytes(encode_jsonl([
                row("TRAIN_CHANGED", "1.000001", "Train", "Answer")
            ]))
            with self.assertRaisesRegex(ValueError, "Refusing to replace"):
                filter_splits(source, [test_path], output)

    def test_source_or_test_output_and_conflicting_test_ids_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            for name, identifier in (("train", "TRAIN"), ("val", "VAL")):
                (source / f"{name}.jsonl").write_bytes(encode_jsonl([
                    row(identifier, f"1.00000{len(identifier)}", name, name)
                ]))
            left, right = root / "left.jsonl", root / "right.jsonl"
            left.write_bytes(encode_jsonl([row("TEST", "3.000003", "A", "A")]))
            right.write_bytes(encode_jsonl([row("TEST", "4.000004", "B", "B")]))
            with self.assertRaisesRegex(ValueError, "Conflicting test record"):
                filter_splits(source, [left, right], root / "out")
            with self.assertRaisesRegex(ValueError, "must not overwrite"):
                filter_splits(source, [left], source)


if __name__ == "__main__":
    unittest.main()
