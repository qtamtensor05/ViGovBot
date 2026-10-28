import json
import unittest
from jsonschema import Draft202012Validator, ValidationError
from tests.schema_fixtures import ROOT, SCHEMAS, prediction, validator


class PredictionSchemaTests(unittest.TestCase):
    def test_only_three_self_contained_schemas(self):
        self.assertEqual(set(SCHEMAS), {"golden_dataset", "prediction", "evaluation_case"})
        def check(value):
            if isinstance(value, dict):
                if "$ref" in value:
                    self.assertTrue(value["$ref"].startswith("#/"))
                for child in value.values():
                    check(child)
            elif isinstance(value, list):
                for child in value:
                    check(child)
        for schema in SCHEMAS.values():
            check(schema)

    def test_prediction_and_evaluation_definitions_stay_aligned(self):
        prediction_schema, evaluation_schema = SCHEMAS["prediction"], SCHEMAS["evaluation_case"]
        for key, value in prediction_schema["properties"].items():
            self.assertEqual(value, evaluation_schema["properties"][key], key)
        for key, value in prediction_schema["$defs"].items():
            self.assertEqual(value, evaluation_schema["$defs"][key], key)

    def test_embedded_golden_definitions_stay_aligned(self):
        for name in SCHEMAS["evaluation_case"]["$defs"]:
            if not name.startswith("golden_"):
                continue
            key = name.removeprefix("golden_")
            value = SCHEMAS["golden_dataset"]["$defs"][key]
            expected = json.loads(json.dumps(value).replace("#/$defs/", "#/$defs/golden_"))
            self.assertEqual(expected, SCHEMAS["evaluation_case"]["$defs"]["golden_" + key], key)

    def test_documented_examples(self):
        for name in ("prediction", "case_score"):
            row = json.loads((ROOT / (name + ".example.json")).read_text(encoding="utf-8"))
            validator("evaluation_case" if name == "case_score" else name).validate(row)

    def test_schema_definitions(self):
        for name, schema in SCHEMAS.items():
            with self.subTest(name=name):
                Draft202012Validator.check_schema(schema)

    def test_scopes_and_statuses(self):
        for scope in ("end_to_end", "retrieval"):
            for status in ("success", "error", "timeout", "oom", "not_run"):
                with self.subTest(scope=scope, status=status):
                    validator("prediction").validate(prediction(scope, status))

    def test_old_contract_rejected(self):
        for key in ("id", "answer", "retrieved_chunk_ids", "evaluation_trace", "evaluation_results"):
            row = prediction()
            row[key] = "old-field"
            with self.subTest(key=key), self.assertRaises(ValidationError):
                validator("prediction").validate(row)
        row = prediction()
        row["schema_version"] = "2.0.0"
        with self.assertRaises(ValidationError):
            validator("prediction").validate(row)

    def test_failure_partial_output(self):
        for status in ("error", "timeout", "oom"):
            row = prediction(status=status)
            row["execution"]["generation"] = {"actual_output": None, "partial_output": "Part", "citations": [], "prompt_messages": [{"role": "user", "content": "Fixture"}], "prompt_contexts": []}
            validator("prediction").validate(row)
            row["execution"]["generation"]["actual_output"] = "Complete"
            with self.assertRaises(ValidationError):
                validator("prediction").validate(row)

    def test_success_requires_output(self):
        for scope, field in (("end_to_end", "generation"), ("retrieval", "retrieval")):
            row = prediction(scope)
            row["execution"][field] = None
            with self.assertRaises(ValidationError):
                validator("prediction").validate(row)
        row = prediction()
        row["execution"]["generation"]["partial_output"] = "Partial"
        with self.assertRaises(ValidationError):
            validator("prediction").validate(row)

    def test_not_run_and_numeric_constraints(self):
        row = prediction(status="not_run")
        row["execution"]["retrieval"] = prediction()["execution"]["retrieval"]
        with self.assertRaises(ValidationError):
            validator("prediction").validate(row)
        for field, value in (("top_k", 0), ("contexts", [{"rank": 0, "context_id": "c", "score": 0}])):
            row = prediction()
            row["execution"]["retrieval"][field] = value
            with self.assertRaises(ValidationError):
                validator("prediction").validate(row)
        row = prediction()
        row["execution"]["telemetry"]["retrieval_latency_ms"] = -1
        with self.assertRaises(ValidationError):
            validator("prediction").validate(row)
