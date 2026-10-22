from tests.dependencies import skip_missing_dependency

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

try:
    from vigovbot.evaluation.__main__ import main as evaluation_main
    from vigovbot.evaluation.io import read_jsonl
    from vigovbot.evaluation.v2 import build_record, export_v2, load_golden, load_predictions, run_v2
except ModuleNotFoundError as exc:
    skip_missing_dependency(exc)


def golden(test_id="TC_1", *, unanswerable=False):
    contexts = [] if unanswerable else ["chunk-1"]
    citations = [] if unanswerable else [{"claim": "Lệ phí 10.000 đồng", "source_id": "chunk-1"}]
    return {
        "test_id": test_id,
        "version": "test-v1",
        "taxonomy": {
            "domain": "test", "turn_type": "new_question", "complexity_type": "single_hop",
            "has_topic_shift": False, "difficulty": "easy", "eval_split": "in_domain",
            "is_unanswerable": unanswerable, "adversarial_type": "none",
        },
        "input": {"chat_history": [], "question": "Lệ phí bao nhiêu?", "task_constraint": None,
                  "metadata_filters": None},
        "ground_truth": {
            "expected_route": "rag_search", "ground_truth_standalone_query": "Lệ phí bao nhiêu?",
            "ground_truth_sub_queries": [], "sub_query_context_mapping": {},
            "ground_truth_context_ids": contexts, "ground_truth_contexts": [],
            "distractor_injection": {"distractor_context_ids": [], "distractor_contexts": [],
                                     "conflict_type": "none", "injected_noise_ratio": 0.0},
            "expected_answer": "Lệ phí 10.000 đồng.",
            "key_facts_required": [] if unanswerable else ["10.000 đồng"],
            "expected_citations": citations, "expected_format": "markdown_text",
            "negative_constraints": ["20.000 đồng"],
        },
    }


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


class EvaluationV2Tests(unittest.TestCase):
    def test_supplemental_offline_scores_cached_predictions_without_inference(self):
        from vigovbot.evaluation.offline_v2 import score_offline_v2

        def bert_score(predictions, references, **kwargs):
            self.assertEqual(predictions, ["Lệ phí 10.000 đồng."])
            self.assertEqual(references, ["Lệ phí 10.000 đồng."])
            self.assertEqual(kwargs["model_type"], "fixture")
            return [0.1], [0.2], [0.3]

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_jsonl(root / "test_golden.jsonl", [golden()])
            predictions = root / "predictions.jsonl"
            write_jsonl(predictions, [{"id": "TC_1", "answer": "Lệ phí 10.000 đồng.",
                                       "retrieved_chunk_ids": ["chunk-1", "noise"]}])
            output = root / "offline.json"
            report = score_offline_v2(dataset=root, split="test", predictions=predictions,
                                      architecture="rag_base", output=output, bertscore=True,
                                      bert_model="fixture", bert_score_fn=bert_score)
            output_exists = output.exists()
        self.assertEqual(report["metrics"]["retrieval"]["map_at_5"], 1.0)
        self.assertEqual(report["metrics"]["lexical"]["bertscore_f1"], 0.3)
        self.assertEqual(report["metrics"]["metric_details"]["map_at_5"]["n"], 1)
        self.assertTrue(output_exists)

    def test_run_v2_sends_only_question_history_and_records_trace(self):
        captured = []

        def post_json(endpoint, payload, timeout):
            captured.append((endpoint, payload, timeout))
            return {"results": [{
                "model_id": "qwen-rag", "answer": "Lệ phí 10.000 đồng.", "action": "answer",
                "sources": [{"chunk_id": "chunk-1", "score": 0.9}], "latency_s": 0.5,
            }]}

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_jsonl(root / "test_golden.jsonl", [golden()])
            output = root / "predictions.jsonl"
            progress = io.StringIO()
            with redirect_stderr(progress):
                report = run_v2(dataset=root, split="test", architecture="rag_base", output=output,
                                endpoint="http://web/api/chat", post_json=post_json)
            prediction = next(read_jsonl(output))
        self.assertEqual(captured[0], (
            "http://web/api/chat",
            {"question": "Lệ phí bao nhiêu?", "models": ["qwen-rag"], "histories": {"qwen-rag": []},
             "evaluation_trace": True},
            300,
        ))
        serialized_payload = json.dumps(captured[0][1], ensure_ascii=False)
        self.assertNotIn("expected_answer", serialized_payload)
        self.assertNotIn("ground_truth", serialized_payload)
        self.assertNotIn("chunk-1", serialized_payload)
        self.assertEqual(prediction["id"], "TC_1")
        self.assertEqual(prediction["retrieved_chunk_ids"], ["chunk-1"])
        self.assertEqual(report["execution_status"], {"success": 1})
        self.assertFalse(report["gold_labels_sent_to_model"])
        self.assertIn("[run-v2] 1/1 (100.0%)", progress.getvalue())
        self.assertIsNone(prediction["citations"])
        self.assertEqual(prediction["citations_status"], "unavailable")
        self.assertEqual(report["evaluation_trace_status"], {"unavailable": 1})

    def test_citation_missing_is_distinct_from_observed_empty(self):
        variants = [
            ({"citations": None, "citations_status": "unavailable"}, None),
            ({"citations": [], "citations_status": "disabled"}, None),
            ({"citations": [], "web_model_id": "qwen-rag"}, None),
            ({}, None),
            ({"citations": [], "citations_status": "validated_references_not_semantic_support"}, 0.0),
            ({"citations": [], "citations_status": "invalid_model_output"}, 0.0),
            ({"citations": [{"source_id": "chunk-1"}]}, 1.0),
        ]
        for fields, expected in variants:
            with self.subTest(fields=fields):
                record = build_record(golden(), {"id": "TC_1", "answer": "x", **fields}, split="test",
                                      run_id="r", architecture="rag_base", model_config={"model_name": "m"}, provenance={})
                result = record["evaluation_results"]
                self.assertEqual(result["generation_scores"]["citation_recall"], expected)
                self.assertEqual(result["metric_details"]["citation_recall"]["status"],
                                 "missing_input" if expected is None else "computed")

    def test_local_http_trace_reaches_export_without_gold_leakage(self):
        import threading
        from http.server import ThreadingHTTPServer
        from types import SimpleNamespace
        try:
            from vigovbot.server.app import ChatApplication, make_handler
        except ModuleNotFoundError as exc:
            skip_missing_dependency(exc)
        model = SimpleNamespace(id="qwen-rag", provider="openai_compatible", model="fixture",
                                base_url="unused", api_key_env=None, mode="rag")
        config = SimpleNamespace(web=SimpleNamespace(models=[model]), inference_settings=lambda: {"top_k": 5})
        app = ChatApplication(config, "retriever", "tokenizer")
        result = {
            "prediction": "Lệ phí 10.000 đồng.", "action": "answer", "actual_route": "rag_search",
            "routing": {"scope": "in_scope", "relation": "new_question"},
            "retrieval_query": "Lệ phí bao nhiêu?", "retrieved": [{"chunk_id": "chunk-1", "score": 0.9}],
            "citations": [{"chunk_id": "chunk-1", "claim": "10.000 đồng"}],
            "citations_status": "validated_references_not_semantic_support",
            "routing_s": 0.1, "retrieval_s": 0.2, "generation_s": 0.3, "latency_s": 0.6,
            "prompt_tokens_estimated": 123, "raw_ollama": {"secret": "must-not-export"},
        }
        with patch("vigovbot.server.app.answer_question", return_value=result) as answer:
            server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(app))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with tempfile.TemporaryDirectory() as work:
                    root = Path(work)
                    write_jsonl(root / "test_golden.jsonl", [golden()])
                    predictions = root / "predictions.jsonl"
                    run_v2(dataset=root, split="test", architecture="rag_base", output=predictions,
                           endpoint=f"http://127.0.0.1:{server.server_port}/api/chat")
                    row = next(read_jsonl(predictions))
                    self.assertNotIn("must-not-export", json.dumps(row))
                    self.assertEqual(row["evaluation_trace"]["token_estimates"]["prompt_tokens_estimated"], 123)
                    self.assertIsNone(row["telemetry"]["prompt_tokens"])
                    output = root / "results.jsonl"
                    export_v2(dataset=root, split="test", architecture="rag_base", predictions=predictions,
                              model_name="fixture", run_id="r", output=output)
                    scores = next(read_jsonl(output))["evaluation_results"]
                    self.assertEqual(scores["query_processing_scores"]["router_accuracy"], 1.0)
                    self.assertEqual(scores["query_processing_scores"]["query_rewrite_similarity"], 1.0)
                    self.assertEqual(scores["generation_scores"]["citation_recall"], 1.0)
                    self.assertEqual(scores["performance_scores"]["generation_latency_ms"], 300.0)
                    self.assertEqual(scores["performance_scores"]["retrieval_latency_ms"], 200.0)
                    self.assertIsNone(scores["performance_scores"]["ttft_ms"])
                    self.assertNotIn("ground_truth", str(answer.call_args))
                    self.assertNotIn("10.000", str(answer.call_args))
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_run_v2_records_http_failure_without_fabricating_answer(self):
        def fail(*_):
            raise TimeoutError("request timed out")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_jsonl(root / "test_golden.jsonl", [golden()])
            output = root / "predictions.jsonl"
            report = run_v2(dataset=root, split="test", architecture="base", output=output, post_json=fail)
            prediction = next(read_jsonl(output))
        self.assertEqual(report["execution_status"], {"error": 1})
        self.assertIsNone(prediction["answer"])
        self.assertEqual(prediction["execution_status"], "error")
        self.assertIn("TimeoutError", prediction["error"])

    def test_build_rag_record_scores_only_available_offline_inputs(self):
        prediction = {
            "id": "TC_1", "answer": "Lệ phí 10.000 đồng.", "action": "answer",
            "retrieved_chunk_ids": ["chunk-1", "noise"], "citations": [{"source_id": "chunk-1"}],
            "retrieval_query": "Lệ phí bao nhiêu?", "latency_seconds": 1.25,
            "telemetry": {"retrieval_seconds": 0.25, "generation_seconds": 1.0},
        }
        record = build_record(
            golden(), prediction, split="test", run_id="run-1", architecture="rag_base",
            model_config={"model_name": "model"}, provenance={"inference_performed": False},
        )
        results = record["evaluation_results"]
        self.assertEqual(record["system_execution_output"]["execution_status"], "success")
        self.assertEqual(results["reference_based_scores"]["normalized_exact_match"], 1.0)
        self.assertEqual(results["retrieval_scores"]["recall_at_1"], 1.0)
        self.assertEqual(results["retrieval_scores"]["precision_at_3"], 0.5)
        self.assertEqual(results["generation_scores"]["citation_recall"], 1.0)
        self.assertEqual(results["performance_scores"]["total_latency_ms"], 1250.0)
        self.assertIsNone(results["generation_scores"]["semantic_correctness"])
        self.assertEqual(results["metric_details"]["semantic_correctness"]["status"], "missing_input")
        self.assertIsNone(results["robustness_and_style_scores"]["negative_constraint_pass"])
        self.assertEqual(results["metric_details"]["negative_constraint_pass"]["status"], "missing_input")

    def test_base_marks_retrieval_not_applicable_instead_of_zero(self):
        record = build_record(
            golden(), {"id": "TC_1", "answer": "x"}, split="test", run_id="run-1",
            architecture="base", model_config={"model_name": "model"}, provenance={},
        )
        retrieval = record["evaluation_results"]["retrieval_scores"]
        self.assertTrue(all(value is None for value in retrieval.values()))
        self.assertTrue(all(
            record["evaluation_results"]["metric_details"][key]["status"] == "not_applicable"
            for key in retrieval
        ))

    def test_unanswerable_without_relevance_labels_excludes_retrieval_metrics(self):
        record = build_record(
            golden(unanswerable=True), {"id": "TC_1", "answer": "Nguồn không nêu.", "action": "abstain"},
            split="test", run_id="run-1", architecture="rag_base", model_config={"model_name": "model"},
            provenance={},
        )
        self.assertTrue(record["evaluation_results"]["robustness_and_style_scores"]["abstention_correct"])
        self.assertEqual(record["evaluation_results"]["metric_details"]["recall_at_10"]["status"],
                         "not_applicable")

    def test_export_requires_exact_ids_by_default_and_supports_explicit_partial(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_jsonl(root / "test_golden.jsonl", [golden("TC_1"), golden("TC_2")])
            predictions = root / "predictions.jsonl"
            write_jsonl(predictions, [{"id": "TC_1", "answer": "Lệ phí 10.000 đồng."}])
            output = root / "run.jsonl"
            with self.assertRaisesRegex(ValueError, "miss 1 Golden IDs"):
                export_v2(dataset=root, split="test", predictions=predictions, architecture="finetuned",
                          model_name="adapter", run_id="run-1", output=output)
            progress = io.StringIO()
            with redirect_stderr(progress):
                summary = export_v2(
                    dataset=root, split="test", predictions=predictions, architecture="finetuned",
                    model_name="adapter", run_id="run-1", output=output, allow_partial=True,
                )
            rows = list(read_jsonl(output))
        self.assertEqual(summary["missing_predictions"], 1)
        self.assertEqual(summary["cohorts"]["answerable"], {"expected": 2, "predicted": 1, "successful": 1})
        self.assertEqual(summary["metric_aggregates"]["reference_based_scores"]["normalized_exact_match"]["n"], 1)
        self.assertEqual([row["scoring_status"] for row in rows], ["partial", "not_scored"])
        self.assertFalse(rows[0]["provenance"]["inference_performed"])
        self.assertIn("[export-v2] 2/2 (100.0%)", progress.getvalue())

    def test_export_rejects_prediction_ids_from_another_benchmark(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_jsonl(root / "test_golden.jsonl", [golden()])
            predictions = root / "predictions.jsonl"
            write_jsonl(predictions, [{"id": "qa2_00007", "answer": "cached"}])
            with self.assertRaisesRegex(ValueError, "outside Golden split"):
                export_v2(dataset=root, split="test", predictions=predictions, architecture="base",
                          model_name="model", run_id="run-1", output=root / "run.jsonl")

    def test_export_without_predictions_is_an_explicit_not_run_skeleton(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_jsonl(root / "test_golden.jsonl", [golden()])
            output = root / "run.jsonl"
            summary = export_v2(dataset=root, split="test", predictions=None, architecture="base",
                                model_name="model", run_id="run-1", output=output)
            row = next(read_jsonl(output))
        self.assertEqual(summary["missing_predictions"], 1)
        self.assertEqual(summary["execution_status"], {"not_run": 1})
        self.assertEqual(row["scoring_status"], "not_scored")
        self.assertEqual(row["evaluation_results"]["metric_details"]["token_f1"]["status"], "not_run")

    def test_duplicate_ids_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_jsonl(root / "test_golden.jsonl", [golden(), golden()])
            with self.assertRaisesRegex(ValueError, "duplicate test_id"):
                load_golden(root, "test")
            predictions = root / "predictions.jsonl"
            write_jsonl(predictions, [{"id": "TC_1", "answer": "a"}, {"id": "TC_1", "answer": "b"}])
            with self.assertRaisesRegex(ValueError, "duplicate prediction ID"):
                load_predictions(predictions)

    def test_cli_export_v2_routes_only_to_offline_exporter(self):
        with patch("vigovbot.evaluation.v2.export_v2", return_value={"status": "ok"}) as exporter:
            self.assertEqual(evaluation_main([
                "export-v2", "--run-id", "run-1", "--architecture", "base", "--model-name", "model",
                "--out", "out.jsonl",
            ]), 0)
        exporter.assert_called_once()
        self.assertIsNone(exporter.call_args.kwargs["predictions"])

    def test_cli_run_v2_routes_to_web_runner(self):
        report = {"execution_status": {"success": 2}}
        with patch("vigovbot.evaluation.v2.run_v2", return_value=report) as runner:
            self.assertEqual(evaluation_main([
                "run-v2", "--architecture", "base", "--limit", "2", "--out", "predictions.jsonl",
            ]), 0)
        runner.assert_called_once()
        self.assertEqual(runner.call_args.kwargs["model_id"], None)
        self.assertEqual(runner.call_args.kwargs["endpoint"], "http://localhost:8001/api/chat")

    def test_cli_noise_v2_routes_to_resumable_noise_runner(self):
        with patch("vigovbot.evaluation.noise.run_noise", return_value={"TC_1": "cached"}) as runner:
            self.assertEqual(evaluation_main([
                "noise-v2", "--model-id", "qwen-rag", "--predictions", "predictions.jsonl",
                "--out", "noise-predictions.jsonl",
            ]), 0)
        runner.assert_called_once()
        self.assertEqual(runner.call_args.kwargs["model_id"], "qwen-rag")
        self.assertEqual(runner.call_args.kwargs["endpoint"], "http://localhost:8001/api/chat")


if __name__ == "__main__":
    unittest.main()
