import tempfile
import unittest
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from tests.test_evaluation_v2 import base_api_result, golden, prediction, write_jsonl
from vigovbot.evaluation.extended import extend_record
from vigovbot.evaluation.records import build_record, capture_predictions


class ExtendedEvaluationTests(unittest.TestCase):
    def test_resume_does_not_regenerate_cached_answer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_jsonl(root / "test_golden.jsonl", [golden()])
            send = Mock(return_value={"results": [base_api_result("cached")]})
            args = dict(dataset=root, split="test", architecture="base", output=root / "p.jsonl",
                        post_json=send)
            capture_predictions(**args)
            capture_predictions(**args, resume=True)
            self.assertEqual(send.call_count, 1)
            with self.assertRaises(ValueError):
                capture_predictions(**args, resume=True, complete_trace=True)

    def test_subquery_coverage(self):
        case = golden()
        case["ground_truth"].update(ground_truth_sub_queries=["Lệ phí?"],
                                    sub_query_context_mapping={"Lệ phí?": ["chunk-1"]})
        pred = prediction(case)
        pred["execution"]["query_processing"].update(
            sub_queries=[{"query": "lệ phí", "sub_query_id": "sq-1"}], decomposition_applied=False)
        pred["execution"]["retrieval"]["sub_query_results"] = [{
            "query": "lệ phí", "sub_query_id": "sq-1", "top_k": 1,
            "contexts": pred["execution"]["retrieval"]["contexts"],
        }]
        record = build_record(case, pred, split="test", run_id="fixture", architecture="rag",
                              model_config={"model_name": "fixture"}, provenance={})
        extend_record(record, pred)
        metrics = record["evaluation_results"]["metrics"]
        self.assertEqual(metrics["query_processing"]["sub_query_recall"]["value"], 1)
        self.assertEqual(metrics["retrieval"]["multi_intent_retrieval_coverage"]["value"], 1)

    def test_map_requires_declared_depth_and_deduplicates(self):
        case = golden()
        pred = prediction(case)
        context = pred["execution"]["retrieval"]["contexts"][0]
        pred["execution"]["retrieval"].update(
            top_k=5, contexts=[{**context, "context_id": "noise"}, context, context])
        record = build_record(case, pred, split="test", run_id="fixture", architecture="rag",
                              model_config={"model_name": "fixture"}, provenance={})
        extend_record(record, pred)
        self.assertIsNone(record["evaluation_results"]["metrics"]["retrieval"]["map_at_10"]["value"])
        pred["execution"]["retrieval"]["top_k"] = 10
        extend_record(record, pred)
        self.assertEqual(record["evaluation_results"]["metrics"]["retrieval"]["map_at_10"]["value"], 0.5)

    def test_stream_records_first_content_and_provider_usage(self):
        from vigovbot.llm.llm_client import ollama_answer
        response = Mock()
        response.iter_lines.return_value = [
            b'{"message":{"content":"hello"},"done":false}',
            b'{"message":{"content":" world"},"done":true,"prompt_eval_count":7,"eval_count":2,"eval_duration":1000000000}',
        ]
        settings = dict(ollama_url="http://localhost:11434", model="fixture", temperature=0,
                        num_ctx=2048, num_predict=128, seed=42, keep_alive="0", timeout=5,
                        measure_ttft=True)
        import sys
        from types import SimpleNamespace
        with patch.dict(sys.modules, {"requests": SimpleNamespace(post=Mock(return_value=response))}):
            answer, raw, duration = ollama_answer([], settings)
        self.assertEqual(answer, "hello world")
        self.assertEqual(raw["eval_count"], 2)
        self.assertGreaterEqual(duration, raw["ttft_seconds"])
        response.close.assert_called_once()

    def test_rescore_rebuilds_derived_artifacts_without_changing_predictions(self):
        from vigovbot.artifacts import file_hash
        from vigovbot.evaluation.workflow import _dispatch
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = root / "dataset"
            output_root = root / "output"
            run = output_root / "run"
            run.mkdir(parents=True)
            case = golden()
            golden_path = dataset / "test/golden_test.jsonl"
            write_jsonl(golden_path, [case])
            pred = prediction(case)
            pred["run_id"] = "run"
            pred["provenance"]["dataset_sha256"] = file_hash(golden_path)
            predictions = run / "predictions.jsonl"
            write_jsonl(predictions, [pred])
            prediction_hash = file_hash(predictions)
            manifest = {
                "dataset": str(golden_path.resolve()), "sha256": file_hash(golden_path), "split": "test",
                "expected": 1, "selected_ids_sha256": "fixture", "profile": "rag", "scope": "full",
                "run_id": "run", "dataset_dir": str(dataset.resolve()), "endpoint": "fixture", "limit": None,
                "complete_trace": True, "top_k": 10, "config": "fixture", "config_sha256": "fixture",
                "model_metadata": None, "model_metadata_sha256": None, "model_id": "qwen-rag",
            }
            (run / "run-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            (run / "scores.json").write_text('{"stale":true}', encoding="utf-8")
            (run / "report.json").write_text('{"stale":true}', encoding="utf-8")
            args = SimpleNamespace(
                command="score", profile=None, other_run_id=None, output_root=output_root,
                rescore=True, allow_partial=False, judge_model=None, judge_endpoint="fixture",
                resume=False, bertscore=True, extended_metrics=True, bert_model="fixture",
                bert_device="cpu", bert_batch_size=1,
            )
            def supplemental(**kwargs):
                value = {
                    "schema_version": "3.2.0-supplement-1",
                    "metrics": {"metric_details": {"chrf": {"status": "computed"}}},
                    "per_case": [{"test_id": case["test_id"], "chrf": 80.0}],
                    "provenance": {
                        "golden_sha256": file_hash(golden_path),
                        "predictions_sha256": file_hash(predictions),
                        "scorer_version": "fixture-supplement-v1",
                    },
                }
                kwargs["output"].write_text(json.dumps(value), encoding="utf-8")
                return value
            with patch("vigovbot.evaluation.scoring.score_supplemental", side_effect=supplemental):
                summary = _dispatch(args, run)
            refreshed_report = json.loads((run / "report.json").read_text(encoding="utf-8"))
            prediction_hash_after = file_hash(predictions)
            supplemental_exists = (run / "supplemental.json").is_file()
        self.assertEqual(summary["execution_status"], {"success": 1})
        self.assertEqual(summary["metric_aggregates"]["generation"]["chrf"], {"mean": 80.0, "n": 1})
        self.assertEqual(refreshed_report["scores"], summary)
        self.assertEqual(prediction_hash_after, prediction_hash)
        self.assertTrue(supplemental_exists)


if __name__ == "__main__":
    unittest.main()
