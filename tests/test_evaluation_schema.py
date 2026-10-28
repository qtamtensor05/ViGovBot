import unittest
from jsonschema import ValidationError
from tests.schema_fixtures import metric, scored, validator


class EvaluationSchemaTests(unittest.TestCase):
    def test_shared_prediction_envelope(self):
        row = scored()
        validator("evaluation_case").validate(row)
        validator("evaluation_case").validate(row)
        validator("prediction").validate({k: v for k, v in row.items() if k not in {"golden", "evaluation_results"}})

    def test_sparse_extensible_metrics(self):
        row = scored()
        row["evaluation_results"]["metrics"] = {}
        validator("evaluation_case").validate(row)
        row["evaluation_results"]["metrics"] = {"groundedness": {"ragas.faithfulness": metric(0.8)}}
        validator("evaluation_case").validate(row)

    def test_metric_consistency(self):
        for change in ({"value": None}, {"scorer_version": None}, {"status": "missing_input"}):
            row = scored()
            row["evaluation_results"]["metrics"]["retrieval"]["recall_at_5"].update(change)
            with self.assertRaises(ValidationError):
                validator("evaluation_case").validate(row)
        row = scored()
        row["evaluation_results"]["metrics"]["retrieval"]["recall_at_5"] = metric(None, "missing_input")
        validator("evaluation_case").validate(row)

    def test_golden_rules_reused(self):
        for group, key, value in (
            ("taxonomy", "turn_type", "follow_up"), ("taxonomy", "complexity_type", "multi_intent"),
            ("taxonomy", "domain", "Đất Đai"), ("ground_truth", "ground_truth_context_ids", []),
            ("ground_truth", "expected_route", "typo")):
            row = scored()
            row["golden"][group][key] = value
            with self.subTest(key=key), self.assertRaises(ValidationError):
                validator("evaluation_case").validate(row)

    def test_failed_generation_not_scored(self):
        row = scored()
        row["execution"].update(status="timeout", error="Timeout")
        row["execution"]["generation"] = {"actual_output": None, "partial_output": "Part", "citations": [], "prompt_messages": [{"role": "user", "content": "Fixture"}], "prompt_contexts": []}
        row["evaluation_results"]["metrics"]["generation"] = {"token_f1": metric(0.5)}
        with self.assertRaises(ValidationError):
            validator("evaluation_case").validate(row)
        row["evaluation_results"]["metrics"]["generation"]["token_f1"] = metric(None, "not_applicable")
        validator("evaluation_case").validate(row)

    def test_not_scored_and_old_layout(self):
        row = scored()
        row["evaluation_results"]["scoring_status"] = "not_scored"
        with self.assertRaises(ValidationError):
            validator("evaluation_case").validate(row)
        row["evaluation_results"]["metrics"] = {}
        validator("evaluation_case").validate(row)
        row["evaluation_results"]["metric_details"] = {}
        with self.assertRaises(ValidationError):
            validator("evaluation_case").validate(row)

    def test_not_run_cannot_claim_computed_metric(self):
        from tests.schema_fixtures import prediction
        row = scored()
        row["execution"] = prediction(status="not_run")["execution"]
        with self.assertRaises(ValidationError):
            validator("evaluation_case").validate(row)
        row["evaluation_results"]["metrics"] = {}
        validator("evaluation_case").validate(row)
