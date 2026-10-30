from tests.dependencies import skip_missing_dependency

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from copy import deepcopy
from pathlib import Path

try:
    from vigovbot.evaluation.io import read_jsonl
    from vigovbot.evaluation.records import (
        ARCHITECTURES, DEFAULT_WEB_MODELS, build_record, capture_predictions,
        export_scores, load_golden, load_predictions,
    )
except ModuleNotFoundError as exc:
    skip_missing_dependency(exc)

from tests.schema_fixtures import prediction as prediction_fixture, validator
from tests.test_golden_schema import case as golden_fixture


def golden(test_id="GOLDEN_FIXTURE_1", *, unanswerable=False):
    row = deepcopy(golden_fixture())
    row["test_id"] = test_id
    if unanswerable:
        row["taxonomy"]["is_unanswerable"] = True
        row["ground_truth"].update(ground_truth_context_ids=[], ground_truth_contexts=[],
                                   expected_citations=[], key_facts_required=[])
        row["evaluation_plan"].update(expected_action="abstain", fact_evidence=[])
    return row


def prediction(row=None, architecture="rag"):
    row = row or golden()
    value = prediction_fixture()
    value.update(test_id=row["test_id"], input=deepcopy(row["input"]), architecture=architecture)
    value["provenance"]["dataset_version"] = row["version"]
    if architecture == "base":
        value["evaluation_context"]["requested_cutoffs"] = []
        value["provenance"].update(corpus_revision=None, index_revision=None)
        value["execution"].update(query_processing=None, retrieval=None,
                                  routing={"actual_route": "direct_answer", "canonical_route": "direct_answer",
                                           "scope": None, "conversation": None, "relation": None,
                                           "sections": [], "mixed_procedures": None, "backend": None,
                                           "fallback_reason": None},
                                  retrieval_skip_reason="architecture_without_retrieval")
        value["execution"]["generation"].update(citations=[], prompt_contexts=[])
        value["execution"]["telemetry"].update(query_processing_latency_ms=None,
                                                retrieval_latency_ms=None)
    return value


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def api_result():
    return {"model_id": "qwen-rag", "answer": "Miễn phí", "action": "answer",
            "sources": [{"chunk_id": "chunk-1", "score": 0.9, "text_content": "Miễn phí"}],
            "latency_s": 0.5,
            "evaluation_trace": {
                "actual_route": "rag_search",
                "routing": {"scope": "IN_SCOPE", "conversation": "NEW", "sections": [],
                            "mixed_procedures": False},
                "routing_backend": "fixture",
                "schema_version": "1.0", "retrieval_query": "Lệ phí?", "actual_sub_queries": [],
                "sub_query_retrieval": {}, "retrieval_top_k": 5, "decision_reason": "evidence_assessment",
                "context_used": [{"chunk_id": "chunk-1", "score": 0.9, "included_text": "Miễn phí",
                                  "content_truncated": False}],
                "prompt_messages": [{"role": "user", "content": "Lệ phí?\nTài liệu: Miễn phí"}],
                "citations": [{"source_id": "chunk-1", "claim": "Miễn phí"}],
                "finish_reason": "stop", "effective_settings": {"model": "fixture", "top_k": 5},
                "telemetry": {"routing_seconds": 0.02, "rewrite_seconds": 0.01,
                              "retrieval_seconds": 0.1, "generation_seconds": 0.37,
                              "prompt_tokens": 20, "completion_tokens": 4, "total_tokens": 24},
            }}


def base_api_result(answer="Miễn phí"):
    return {"model_id": "qwen-base", "answer": answer, "action": "answer", "sources": [],
            "latency_s": 0.2, "evaluation_trace": {
                "schema_version": "1.0", "actual_route": "direct_answer",
                "prompt_messages": [{"role": "user", "content": "Lệ phí?"}],
                "context_used": [], "citations": [], "effective_settings": {"model": "fixture"},
                "telemetry": {"generation_seconds": 0.2}}}


class EvaluationV3Tests(unittest.TestCase):
    def test_supported_architectures_are_schema_vocabulary(self):
        self.assertEqual(ARCHITECTURES, {"base", "finetuned", "rag", "finetuned_rag"})
        self.assertEqual(DEFAULT_WEB_MODELS["rag"], "qwen-rag")

    def test_v3_split_layout_and_legacy_layout_are_resolved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_jsonl(root / "test/golden_test.jsonl", [golden()])
            path, rows = load_golden(root, "test")
            self.assertEqual(path, root / "test/golden_test.jsonl")
            self.assertEqual(len(rows), 1)
            (root / "test/golden_test.jsonl").unlink()
            write_jsonl(root / "test_golden.jsonl", [golden()])
            self.assertEqual(load_golden(root, "test")[0], root / "test_golden.jsonl")

    def test_capture_writes_schema_v32_without_gold_leakage(self):
        captured = []
        def post_json(endpoint, payload, timeout):
            captured.append(payload)
            return {"results": [api_result()]}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_jsonl(root / "test/golden_test.jsonl", [golden()])
            output = root / "predictions.jsonl"
            progress = io.StringIO()
            with redirect_stderr(progress):
                report = capture_predictions(dataset=root, split="test", architecture="rag", output=output,
                                             post_json=post_json)
            row = next(read_jsonl(output))
        validator("prediction").validate(row)
        self.assertEqual(row["schema_version"], "3.2.0")
        self.assertEqual(row["execution"]["routing"]["canonical_route"], "rag_search")
        self.assertEqual(row["execution"]["retrieval"]["contexts"][0]["text"], "Miễn phí")
        self.assertEqual(row["execution"]["generation"]["prompt_contexts"], [
            {"context_id": "chunk-1", "text": "Miễn phí"}
        ])
        self.assertNotIn("ground_truth", json.dumps(captured[0], ensure_ascii=False))
        self.assertEqual(report["execution_status"], {"success": 1})
        self.assertIn("[run] 1/1 (100.0%)", progress.getvalue())

    def test_capture_failure_is_a_valid_error_prediction(self):
        def fail(*_):
            raise TimeoutError("request timed out")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_jsonl(root / "test/golden_test.jsonl", [golden()])
            output = root / "predictions.jsonl"
            capture_predictions(dataset=root, split="test", architecture="base", output=output, post_json=fail)
            row = next(read_jsonl(output))
        validator("prediction").validate(row)
        self.assertEqual(row["execution"]["status"], "error")
        self.assertIsNone(row["execution"]["generation"])

    def test_build_record_and_export_are_schema_v32(self):
        case = golden()
        pred = prediction(case)
        record = build_record(case, pred, split="test", run_id="fixture", architecture="rag",
                              model_config={"model_name": "fixture"}, provenance={})
        validator("evaluation_case").validate(record)
        metric = record["evaluation_results"]["metrics"]["generation"]["normalized_exact_match"]
        self.assertEqual(metric["status"], "computed")
        route = record["evaluation_results"]["metrics"]["routing"]["route_accuracy"]
        self.assertEqual((route["status"], route["value"]), ("computed", 1.0))

    def test_retrieval_only_prediction_builds_schema_v32_case_score(self):
        case = golden()
        pred = prediction_fixture("retrieval")
        pred.update(test_id=case["test_id"], input=deepcopy(case["input"]))
        pred["provenance"]["dataset_version"] = case["version"]
        pred["execution"]["action"] = None
        record = build_record(case, pred, split="test", run_id="fixture", architecture="rag",
                              model_config={"model_name": "fixture"}, provenance={})
        validator("evaluation_case").validate(record)
        performance = record["evaluation_results"]["metrics"]["performance"]
        self.assertEqual(performance["generation_latency_ms"]["status"], "not_applicable")

    def test_unanswerable_case_is_scored_by_expected_action(self):
        case = golden(unanswerable=True)
        pred = prediction(case)
        pred["execution"].update(action="abstain", retrieval=None,
                                 retrieval_skip_reason="source_does_not_contain_answer")
        pred["execution"]["generation"].update(citations=[], prompt_contexts=[])
        record = build_record(case, pred, split="test", run_id="fixture", architecture="rag",
                              model_config={"model_name": "fixture"}, provenance={})
        action = record["evaluation_results"]["metrics"]["robustness"]["action_accuracy"]
        self.assertEqual((action["status"], action["value"]), ("computed", True))

    def test_export_requires_coverage_and_supports_explicit_partial(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first, second = golden("GOLDEN_1"), golden("GOLDEN_2")
            golden_path = root / "test/golden_test.jsonl"
            write_jsonl(golden_path, [first, second])
            predictions = root / "predictions.jsonl"
            pred = prediction(first, "base")
            from vigovbot.artifacts import file_hash
            pred["provenance"]["dataset_sha256"] = file_hash(golden_path)
            write_jsonl(predictions, [pred])
            output = root / "case-scores.jsonl"
            with self.assertRaisesRegex(ValueError, "miss 1 Golden IDs"):
                export_scores(dataset=root, split="test", predictions=predictions, architecture="base",
                              model_name="fixture", run_id="fixture", output=output)
            summary = export_scores(dataset=root, split="test", predictions=predictions, architecture="base",
                                    model_name="fixture", run_id="fixture", output=output, allow_partial=True)
            records = list(read_jsonl(output))
        self.assertEqual(summary["schema_version"], "3.2.0")
        validator("evaluation_summary").validate(summary)
        self.assertEqual(summary["missing_predictions"], 1)
        self.assertEqual(summary["cohorts"]["turn_type:new_question"]["expected"], 2)
        self.assertIn("turn_type:new_question", summary["cohort_metric_aggregates"])
        self.assertEqual([row["evaluation_results"]["scoring_status"] for row in records],
                         ["partial", "not_scored"])
        for row in records:
            validator("evaluation_case").validate(row)

    def test_supplemental_scores_v3_cached_prediction(self):
        from vigovbot.evaluation.scoring import score_supplemental
        case = golden()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_jsonl(root / "test/golden_test.jsonl", [case])
            predictions = root / "predictions.jsonl"
            write_jsonl(predictions, [prediction(case)])
            report = score_supplemental(dataset=root, split="test", predictions=predictions,
                                        architecture="rag", output=root / "supplemental.json")
        self.assertEqual(report["schema_version"], "3.2.0-supplement-1")
        self.assertEqual(report["scored_records"], 1)
        for metric in ("chrf", "chrf_pp", "sacrebleu", "character_error_rate", "word_error_rate"):
            self.assertIn(metric, report["per_case"][0])

    def test_supplemental_metrics_merge_into_case_scores_and_summary(self):
        case = golden()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            golden_path = root / "test/golden_test.jsonl"
            predictions = root / "predictions.jsonl"
            write_jsonl(golden_path, [case])
            pred = prediction(case)
            from vigovbot.artifacts import file_hash
            pred["provenance"]["dataset_sha256"] = file_hash(golden_path)
            write_jsonl(predictions, [pred])
            supplemental_path = root / "supplemental.json"
            supplemental = {
                "schema_version": "3.2.0-supplement-1",
                "metrics": {"metric_details": {
                    "chrf": {"status": "computed", "contract": "sentence chrF"},
                    "bertscore_f1": {"status": "computed", "model": "fixture"},
                }},
                "per_case": [{"test_id": case["test_id"], "chrf": 75.0, "bertscore_f1": 0.9}],
                "provenance": {
                    "golden_sha256": file_hash(golden_path),
                    "predictions_sha256": file_hash(predictions),
                    "scorer_version": "fixture-supplement-v1",
                },
            }
            supplemental_path.write_text(json.dumps(supplemental), encoding="utf-8")
            output = root / "case-scores.jsonl"
            summary = export_scores(
                dataset=root, split="test", predictions=predictions, architecture="rag",
                model_name="fixture", run_id="fixture", output=output,
                supplemental=supplemental, supplemental_path=supplemental_path,
            )
            record = next(read_jsonl(output))
        self.assertEqual(record["evaluation_results"]["metrics"]["generation"]["chrf"]["value"], 75.0)
        self.assertEqual(record["evaluation_results"]["metrics"]["generation"]["bertscore_f1"]["value"], 0.9)
        self.assertEqual(summary["metric_aggregates"]["generation"]["chrf"], {"mean": 75.0, "n": 1})
        self.assertEqual(summary["provenance"]["scorer_versions"]["supplemental"],
                         "fixture-supplement-v1")
        validator("evaluation_case").validate(record)
        validator("evaluation_summary").validate(summary)

    def test_duplicate_ids_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_jsonl(root / "test_golden.jsonl", [golden(), golden()])
            with self.assertRaisesRegex(ValueError, "duplicate test_id"):
                load_golden(root, "test")
            predictions = root / "predictions.jsonl"
            write_jsonl(predictions, [prediction(), prediction()])
            with self.assertRaisesRegex(ValueError, "duplicate prediction ID"):
                load_predictions(predictions)


if __name__ == "__main__":
    unittest.main()
