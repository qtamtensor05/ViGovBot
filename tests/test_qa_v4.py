import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from vigovbot.qa_v4.adapter import normalize_result, existing_rag, ollama_baseline
from vigovbot.qa_v4.io import read_jsonl
from vigovbot.qa_v4.report import finalize_report
from unittest.mock import patch, MagicMock
from vigovbot.qa_v4.runner import estimate_completion, run_queries
from vigovbot.qa_v4.scoring import evaluate
from vigovbot.qa_v4.__main__ import resolve_dataset, select_rows
from vigovbot.evaluation.multiturn import load_queries


class QAV4Tests(unittest.TestCase):
    def test_estimated_completion_uses_observed_average_for_full_selection(self):
        now = datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)
        eta = estimate_completion(30, completed=3, total=9, now=now)
        self.assertEqual(eta["estimated_remaining_seconds"], 60)
        self.assertEqual(eta["estimated_completion_at"], "2026-10-03T12:01:00+00:00")
        with self.assertRaises(ValueError):
            estimate_completion(1, completed=0, total=9, now=now)

    def test_small_dataset_alias_and_custom_view(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory)
            (dataset / "views_main_test.json").write_text('["test"]', encoding="utf-8-sig")
            (dataset / "runner_queries.jsonl").write_text(
                '{"id":"test","question":"Câu hỏi?","split":"test","history":[]}\n'
                '{"id":"dev","question":"Dev?","split":"dev","history":[]}\n', encoding="utf-8")
            resolved, view = resolve_dataset(dataset)
            queries = load_queries(resolved / "runner_queries.jsonl", resolved / view, "test")
            cases = select_rows([{"id": "test", "split": "test"}, {"id": "dev", "split": "dev"}],
                                resolved, view, "test")
            self.assertEqual([q["id"] for q in queries], [c["id"] for c in cases])
            self.assertEqual(resolve_dataset(dataset, "views_dev.json")[1], "views_dev.json")
        self.assertEqual(resolve_dataset("rag_v4_small")[0], Path("Data/qa_test_v4/rag_tthc_balanced_small"))
        self.assertEqual(resolve_dataset("rag_tthc_v4_1", "views_balanced.json")[1], "views_balanced.json")

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

    def test_ollama_baseline_does_not_prepare_or_load_corpus(self):
        config = MagicMock()
        config.llm.ollama_url = "http://ollama"
        config.llm.model = "qwen2.5:7b"
        config.inference_settings.return_value = {"model": "qwen2.5:7b"}
        raw = {"eval_count": 12}
        with patch("vigovbot.rag.config.load_config", return_value=config), \
                patch("vigovbot.llm.llm_client.check_model"), \
                patch("vigovbot.llm.llm_client.ollama_answer",
                      return_value=('{"answer":"baseline","action":"answer"}', raw, 0.5)) as generate, \
                patch("vigovbot.llm.llm_client.unload_model"):
            with ollama_baseline("config.yaml") as answer:
                result = answer("question", history=[])
        self.assertEqual(result["answer"], "baseline")
        self.assertEqual(result["retrieved_chunk_ids"], [])
        self.assertEqual(result["unit_mapping_status"], "unavailable")
        self.assertEqual(result["telemetry"]["generation_seconds"], 0.5)
        self.assertEqual(result["telemetry"]["output_tokens"], 12)
        self.assertEqual(generate.call_count, 1)

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
            self.assertIn("started_at", report)
            self.assertIn("completed_at", report)
            self.assertIn("eta_method", report)
            self.assertEqual(calls[1][1][-1]["content"], "generated")
            self.assertNotIn("secret", str(calls))
            saved = list(read_jsonl(path))
            self.assertEqual(saved[0]["question"], "first")
            self.assertEqual(saved[0]["answer"], "generated")
            self.assertNotIn("reference_answer", saved[0])
            self.assertEqual(saved[-1]["question"], "other")
            self.assertIn("error", saved[-1])
            with self.assertRaises(FileExistsError):
                run_queries(queries, answer, path)

    def test_score_failed_predictions_are_missing(self):
        case = {"id": "1", "field_id": "f", "expected_action": "answer", "evidence": [],
                "reference_answer": "x", "conversation_id": None}
        report = evaluate([case], [{"id": "1", "error": "offline"}], [], lexical=False)
        self.assertEqual(report["coverage"]["failed_or_missing"], 1)


if __name__ == "__main__":
    unittest.main()
