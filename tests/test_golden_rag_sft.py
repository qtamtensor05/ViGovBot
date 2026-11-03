import copy
import json
import tempfile
import unittest
from pathlib import Path

from vigovbot.training.data import read_jsonl
from vigovbot.training.golden_rag_sft import convert_golden, convert_record
from vigovbot.training.golden_sft import encode_jsonl


def golden(identifier="TC_1", action="answer"):
    answer = "Cơ quan thực hiện: Bộ Tư pháp." if action == "answer" else "Chưa tìm thấy thông tin trong tài liệu."
    contexts = ["Cơ quan thực hiện: Bộ Tư pháp."] if action == "answer" else []
    context_ids = ["chunk-1"] if action == "answer" else []
    facts = ([{"fact": answer, "context_ids": context_ids}] if action == "answer" else [])
    return {
        "test_id": identifier,
        "input": {"chat_history": [], "question": "Cơ quan nào thực hiện?"},
        "ground_truth": {
            "expected_answer": answer,
            "ground_truth_contexts": contexts,
            "ground_truth_context_ids": context_ids,
        },
        "evaluation_plan": {"expected_action": action, "fact_evidence": facts},
    }


class GoldenRagSftTests(unittest.TestCase):
    def test_structured_runtime_contract_and_source_immutability(self):
        row = golden()
        before = copy.deepcopy(row)
        converted = convert_record(row, "source:1")
        self.assertEqual(converted["id"], "TC_1")
        self.assertEqual([message["role"] for message in converted["messages"]],
                         ["system", "user", "assistant"])
        self.assertIn("chunk-1", converted["messages"][1]["content"])
        target = json.loads(converted["messages"][-1]["content"])
        self.assertEqual(target, {
            "answer": row["ground_truth"]["expected_answer"],
            "action": "answer",
            "evidence_status": "sufficient",
            "citations": [{"chunk_id": "chunk-1", "claim": row["ground_truth"]["expected_answer"]}],
        })
        self.assertEqual(row, before)

    def test_abstain_has_missing_evidence_and_no_citations(self):
        target = json.loads(convert_record(golden(action="abstain"), "source:1")["messages"][-1]["content"])
        self.assertEqual(target["action"], "abstain")
        self.assertEqual(target["evidence_status"], "missing")
        self.assertEqual(target["citations"], [])

    def test_invalid_context_and_action_are_rejected(self):
        row = golden()
        row["ground_truth"]["ground_truth_context_ids"] = []
        with self.assertRaisesRegex(ValueError, "parallel lists"):
            convert_record(row, "source:1")
        row = golden()
        row["evaluation_plan"]["expected_action"] = "invented"
        with self.assertRaisesRegex(ValueError, "unsupported expected_action"):
            convert_record(row, "source:1")

    def test_deterministic_train_validation_publication_without_test(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "train.jsonl").write_bytes(encode_jsonl([golden("TRAIN")]))
            (root / "val.jsonl").write_bytes(encode_jsonl([golden("VAL", "abstain")]))
            (root / "test.jsonl").write_bytes(b"not read by converter\n")
            output = root / "out"
            first = convert_golden(root, output)
            second = convert_golden(root, output)
            self.assertEqual(first, second)
            self.assertFalse(first["test_split_read"])
            self.assertEqual(first["splits"]["train"]["records"], 1)
            self.assertEqual(first["splits"]["validation"]["actions"], {"abstain": 1})
            self.assertEqual(len(read_jsonl(output / "train_rag_sft.jsonl")), 1)
            self.assertFalse((output / "test_rag_sft.jsonl").exists())

    def test_cross_split_id_and_existing_artifact_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "train.jsonl").write_bytes(encode_jsonl([golden()]))
            (root / "val.jsonl").write_bytes(encode_jsonl([golden()]))
            with self.assertRaisesRegex(ValueError, "both train and validation"):
                convert_golden(root, root / "overlap")
            (root / "val.jsonl").write_bytes(encode_jsonl([golden("VAL")]))
            output = root / "out"
            output.mkdir()
            existing = output / "manifest.json"
            existing.write_text("user artifact", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Refusing to replace"):
                convert_golden(root, output)
            self.assertEqual(existing.read_text(encoding="utf-8"), "user artifact")


if __name__ == "__main__":
    unittest.main()
