import tempfile
import unittest
from pathlib import Path

from vigovbot.qa_v4.adapter import normalize_result, existing_rag
from vigovbot.qa_v4.io import read_jsonl
from vigovbot.qa_v4.report import finalize_report
from unittest.mock import patch, MagicMock
from vigovbot.qa_v4.runner import run_queries
from vigovbot.qa_v4.scoring import evaluate


class QAV4Tests(unittest.TestCase):
    def test_adapter_preserves_chunk_ids_without_inventing_units(self):
        result = normalize_result({"prediction": "answer", "action": "answer",
                                   "retrieved": [{"chunk_id": "chunk-1"}], "retrieval_s": .2})
        self.assertEqual(result["retrieved_chunk_ids"], ["chunk-1"])
        self.assertNotIn("retrieved_unit_ids", result)
        self.assertEqual(result["unit_mapping_status"], "unavailable")
        mapped = normalize_result({"prediction": "answer", "retrieved": [{"chunk_id": "chunk-1"}]},
                                  {"chunk-1": ["doc#u001"]})
        self.assertEqual(mapped["retrieved_unit_ids"], ["doc#u001"])
        self.assertEqual(mapped["unit_mapping_status"], "mapped")
        partial = normalize_result({"prediction": "answer", "retrieved_chunk_ids": ["missing"]}, {})
        self.assertEqual(partial["unit_mapping_status"], "incomplete_mapping")

    def test_existing_rag_uses_same_config_and_session(self):
        config = MagicMock()
        config.inference_settings.return_value = {"model": "existing-model"}
        with patch("vigovbot.rag.config.load_config", return_value=config), \
                patch("vigovbot.rag.pipeline.prepare", return_value="paths") as prepare, \
                patch("vigovbot.llm.llm_client.check_model"), \
                patch("vigovbot.rag.pipeline.inference_session") as session, \
                patch("vigovbot.rag.pipeline.answer_question", return_value={"prediction": "generated"}) as generate:
            session.return_value.__enter__.return_value = ("retriever", "tokenizer")
            with existing_rag("same-config.yaml") as answer:
                answer("question", history=[])
                answer("next", history=[])
            prepare.assert_called_once_with(config)
            session.assert_called_once_with(config, "paths")
            generate.assert_any_call("question", "retriever", "tokenizer", {"model": "existing-model"},
                                     history=[], structured=True)
            self.assertEqual(generate.call_count, 2)

    def test_report_does_not_claim_zero_recall_without_mapping(self):
        report = {"overall_available": {"mrr_at_k": {"mean": 0}, "action_accuracy": {"mean": 1}},
                  "per_case": [{"id": "1", "judged_evidence_recall_at_k": 0}]}
        result = finalize_report(report, [{"id": "1", "answer": "x"}], {"1"}, "nonexistent")
        self.assertFalse(result["retrieval_evaluation"]["available"])
        self.assertNotIn("mrr_at_k", result["overall_available"])
        self.assertIn("action_accuracy", result["overall_available"])

    def test_free_running_isolation_and_no_gold_forwarding(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "predictions.jsonl"
            calls = []
            def answer(question, history):
                calls.append((question, list(history)))
                return {"answer": "generated", "action": "answer", "retrieved_unit_ids": []}
            queries = [{"id": "1", "question": "first", "conversation_id": "a", "turn_index": 1,
                        "history": [], "reference_answer": "secret"},
                       {"id": "2", "question": "next", "conversation_id": "a", "turn_index": 2,
                        "history": [{"role": "assistant", "content": "gold"}]},
                       {"id": "3", "question": "other", "conversation_id": "b", "turn_index": 2,
                        "history": []}]
            report = run_queries(queries, answer, path, "free_running")
            self.assertEqual(report["failed"], 1)
            self.assertEqual(calls[1][1][-1]["content"], "generated")
            self.assertNotIn("secret", str(calls))
            self.assertIn("error", list(read_jsonl(path))[-1])
            with self.assertRaises(FileExistsError):
                run_queries(queries, answer, path)

    def test_score_failed_predictions_are_missing(self):
        case = {"id": "1", "field_id": "f", "expected_action": "answer", "evidence": [],
                "reference_answer": "x", "conversation_id": None}
        report = evaluate([case], [{"id": "1", "error": "offline"}], [], lexical=False)
        self.assertEqual(report["coverage"]["failed_or_missing"], 1)


if __name__ == "__main__":
    unittest.main()
