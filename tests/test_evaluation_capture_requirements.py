"""The new contract rejects successful runs missing evaluable core traces."""
import unittest
from copy import deepcopy

from jsonschema import ValidationError

from tests.schema_fixtures import prediction, scored, validator
from tests.test_golden_schema import case


class CaptureRequirementsTests(unittest.TestCase):
    def test_success_cannot_omit_query_or_stage_timing(self):
        for key, value in (("query_processing", None), ("telemetry", {})):
            row = prediction()
            row["execution"][key] = value
            with self.subTest(key=key), self.assertRaises(ValidationError):
                validator("prediction").validate(row)
        for key in ("total_latency_ms", "query_processing_latency_ms", "retrieval_latency_ms", "generation_latency_ms"):
            row = prediction()
            row["execution"]["telemetry"][key] = None
            with self.subTest(key=key), self.assertRaises(ValidationError):
                validator("prediction").validate(row)

    def test_full_evidence_and_prompt_required(self):
        for key in ("prompt_messages", "prompt_contexts", "citations"):
            row = prediction()
            del row["execution"]["generation"][key]
            with self.subTest(key=key), self.assertRaises(ValidationError):
                validator("prediction").validate(row)
        row = prediction()
        del row["execution"]["retrieval"]["contexts"][0]["text"]
        with self.assertRaises(ValidationError):
            validator("prediction").validate(row)

    def test_decomposition_requires_per_query_retrieval(self):
        row = prediction()
        row["execution"]["query_processing"].update(
            decomposition_applied=True, sub_queries=[
                {"sub_query_id": "s1", "query": "q1"}, {"sub_query_id": "s2", "query": "q2"}])
        with self.assertRaises(ValidationError):
            validator("prediction").validate(row)
        row["execution"]["retrieval"]["sub_query_results"] = [
            {"sub_query_id": sid, "query": q, "top_k": 5, "contexts": []}
            for sid, q in (("s1", "q1"), ("s2", "q2"))]
        validator("prediction").validate(row)

    def test_optional_provider_measurements_must_explain_absence(self):
        row = prediction()
        measurement = row["execution"]["telemetry"]["measurements"]["ttft_ms"]
        measurement["reason"] = None
        with self.assertRaises(ValidationError):
            validator("prediction").validate(row)
        measurement.update(status="measured", value=25, source="provider", reason=None)
        validator("prediction").validate(row)
        measurement["value"] = None
        with self.assertRaises(ValidationError):
            validator("prediction").validate(row)

    def test_cost_requires_pricing(self):
        row = prediction()
        row["execution"]["telemetry"]["measurements"]["cost_usd"].update(
            status="measured", value=0.01, source="provider usage and price table", reason=None)
        with self.assertRaises(ValidationError):
            validator("prediction").validate(row)

    def test_golden_requires_evaluation_plan_and_evidence_links(self):
        row = case()
        del row["evaluation_plan"]
        with self.assertRaises(ValidationError):
            validator("golden_dataset").validate(row)
        row = case()
        row["evaluation_plan"]["fact_evidence"] = []
        with self.assertRaises(ValidationError):
            validator("golden_dataset").validate(row)

    def test_subquery_targets_and_noise_pair_required(self):
        row = case()
        row["taxonomy"]["complexity_type"] = "multi_intent"
        row["ground_truth"]["ground_truth_sub_queries"] = ["q1", "q2"]
        with self.assertRaises(ValidationError):
            validator("golden_dataset").validate(row)
        row = case()
        row["ground_truth"]["distractor_injection"].update(
            injected_noise_ratio=0.5, conflict_type="irrelevant", distractor_context_ids=["noise"],
            distractor_contexts=["Noise text"])
        with self.assertRaises(ValidationError):
            validator("golden_dataset").validate(row)
        row["evaluation_plan"]["robustness_pair"] = {
            "pair_id": "p1", "condition": "noisy", "counterpart_test_id": "clean"}
        validator("golden_dataset").validate(row)

    def test_judge_requires_provenance(self):
        row = scored()
        judgment = {"metric": "faithfulness", "value": 1.0, "reason": "Supported",
                    "claims": [{"text": "Miễn phí", "verdict": "supported", "context_ids": ["chunk-1"]}]}
        row["evaluation_results"]["judgments"] = [judgment]
        with self.assertRaises(ValidationError):
            validator("evaluation_case").validate(row)
        judgment["judge"] = {"name": "fixture", "version": "v1", "prompt_sha256": "a"*64, "input_sha256": "b"*64}
        validator("evaluation_case").validate(deepcopy(row))
