"""Golden schema regressions; fixtures are in-memory, source JSONL is read-only."""
import json
import unittest
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schema/golden_dataset.schema.json").read_text(encoding="utf-8"))


def case():
    return {
        "test_id": "fixture", "version": "fixture",
        "evaluation_plan": {
            "cutoffs": [1, 3, 5], "expected_action": "answer", "reference_answers": ["Miễn phí"],
            "fact_evidence": [{"fact": "Miễn phí", "context_ids": ["chunk-1"]}],
            "sub_query_targets": [], "format_rules": [], "negative_rules": [],
            "robustness_pair": None, "relevance_completeness": "known_positives_only",
            "normalization_version": "unicode-nfc-casefold-whitespace-v1",
            "corpus_revision": "corpus-fixture",
        },
        "taxonomy": {
            "domain": "Hộ tịch", "turn_type": "new_question", "complexity_type": "single_hop",
            "has_topic_shift": False, "difficulty": "medium", "eval_split": "in_domain",
            "is_unanswerable": False, "adversarial_type": "none",
        },
        "input": {"question": "Lệ phí?", "chat_history": [], "task_constraint": None, "metadata_filters": None},
        "ground_truth": {
            "expected_route": "rag_search", "ground_truth_standalone_query": "Lệ phí?",
            "ground_truth_sub_queries": [], "sub_query_context_mapping": {},
            "ground_truth_context_ids": ["chunk-1"], "ground_truth_contexts": ["Miễn phí"],
            "distractor_injection": {
                "distractor_context_ids": [], "distractor_contexts": [],
                "conflict_type": "none", "injected_noise_ratio": 0,
            },
            "expected_answer": "Miễn phí", "key_facts_required": ["Miễn phí"],
            "expected_citations": [{"claim": "Miễn phí", "source_id": "chunk-1"}],
            "expected_format": "markdown_text", "negative_constraints": [],
        },
    }


class GoldenSchemaTests(unittest.TestCase):
    def setUp(self):
        self.validator = Draft202012Validator(SCHEMA)

    def test_valid_schema_and_case(self):
        Draft202012Validator.check_schema(SCHEMA)
        self.validator.validate(case())

    def test_answerability_both_directions(self):
        for unanswerable in (False, True):
            valid = case()
            valid["taxonomy"]["is_unanswerable"] = unanswerable
            fields = ("ground_truth_context_ids", "ground_truth_contexts", "expected_citations")
            if unanswerable:
                valid["evaluation_plan"].update(expected_action="abstain", fact_evidence=[])
                for key in fields:
                    valid["ground_truth"][key] = []
            self.validator.validate(valid)
            for key in fields:
                invalid = deepcopy(valid)
                invalid["ground_truth"][key] = case()["ground_truth"][key] if unanswerable else []
                with self.subTest(flag=unanswerable, field=key), self.assertRaises(ValidationError):
                    self.validator.validate(invalid)

    def test_followup_requires_history(self):
        data = case()
        data["taxonomy"]["turn_type"] = "follow_up"
        with self.assertRaises(ValidationError):
            self.validator.validate(data)
        data["input"]["chat_history"] = [{"role": "user", "content": "Đăng ký kết hôn"}]
        self.validator.validate(data)

    def test_multiintent_requires_two_distinct_queries(self):
        data = case()
        data["taxonomy"]["complexity_type"] = "multi_intent"
        for queries in ([], ["Hồ sơ?"], ["Hồ sơ?", "Hồ sơ?"]):
            data["ground_truth"]["ground_truth_sub_queries"] = queries
            with self.assertRaises(ValidationError):
                self.validator.validate(data)
        data["ground_truth"]["ground_truth_sub_queries"] = ["Hồ sơ?", "Lệ phí?"]
        data["evaluation_plan"]["sub_query_targets"] = [
            {"sub_query_id": "s1", "query": "Hồ sơ?", "relevant_context_ids": ["chunk-1"]},
            {"sub_query_id": "s2", "query": "Lệ phí?", "relevant_context_ids": ["chunk-1"]},
        ]
        self.validator.validate(data)

    def test_noise_consistency(self):
        data = case()
        noise = data["ground_truth"]["distractor_injection"]
        noise["injected_noise_ratio"] = 0.2
        with self.assertRaises(ValidationError):
            self.validator.validate(data)
        noise.update(distractor_context_ids=["other"], distractor_contexts=["Other"], conflict_type="other_procedure")
        data["evaluation_plan"]["robustness_pair"] = {
            "pair_id": "pair-fixture", "condition": "noisy", "counterpart_test_id": "clean-fixture"}
        self.validator.validate(data)
        noise["injected_noise_ratio"] = 0
        with self.assertRaises(ValidationError):
            self.validator.validate(data)
        noise.update(distractor_context_ids=[], distractor_contexts=[])
        with self.assertRaises(ValidationError):
            self.validator.validate(data)

    def test_enum_typos_are_rejected(self):
        for group, key, value in (
            ("taxonomy", "domain", "Đất Đai"),
            ("ground_truth", "expected_route", "typo"),
            ("ground_truth", "expected_format", "typo"),
        ):
            data = case()
            data[group][key] = value
            with self.subTest(field=key), self.assertRaises(ValidationError):
                self.validator.validate(data)
