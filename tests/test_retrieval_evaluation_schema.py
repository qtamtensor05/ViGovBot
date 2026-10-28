import unittest
from jsonschema import ValidationError
from tests.schema_fixtures import metric, scored, validator


class RetrievalEvaluationSchemaTests(unittest.TestCase):
    def test_shared_case_contract(self):
        row = scored("retrieval")
        validator("evaluation_case").validate(row)
        validator("evaluation_case").validate(row)

    def test_scope_and_generation_rejected(self):
        validator("evaluation_case").validate(scored())
        row = scored("retrieval")
        row["evaluation_results"]["metrics"]["generation"] = {"token_f1": metric()}
        with self.assertRaises(ValidationError):
            validator("evaluation_case").validate(row)

    def test_no_answer_case(self):
        row = scored("retrieval")
        row["golden"]["taxonomy"]["is_unanswerable"] = True
        row["golden"]["evaluation_plan"].update(expected_action="abstain", fact_evidence=[])
        for key in ("ground_truth_context_ids", "ground_truth_contexts", "expected_citations"):
            row["golden"]["ground_truth"][key] = []
        with self.assertRaises(ValidationError):
            validator("evaluation_case").validate(row)
        row["evaluation_results"]["metrics"]["retrieval"]["recall_at_5"] = metric(None, "not_applicable")
        validator("evaluation_case").validate(row)
        row["evaluation_results"]["metrics"] = {}
        validator("evaluation_case").validate(row)

    def test_metric_range_and_relevance(self):
        row = scored("retrieval")
        row["evaluation_results"]["metrics"]["retrieval"]["recall_at_5"]["value"] = 1.1
        with self.assertRaises(ValidationError):
            validator("evaluation_case").validate(row)
        row = scored("retrieval")
        row["evaluation_results"]["relevance_contract"] = "graded_0_3"
        with self.assertRaises(ValidationError):
            validator("evaluation_case").validate(row)
