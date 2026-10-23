import unittest

from vigovbot.evaluation.ollama_judge import METRICS, normalize_missing_claim_evidence, validate, validate_claims


class JudgeValidationTests(unittest.TestCase):
    def test_accepts_explicit_unknown(self):
        value = {"scores": dict.fromkeys(METRICS), "reason": "Missing evidence"}
        self.assertIs(validate(value), value)

    def test_rejects_invalid_scores(self):
        for bad in (True, 0.5, "1", 2):
            value = {"scores": dict.fromkeys(METRICS, 1), "reason": "Evidence reviewed"}
            value["scores"][METRICS[0]] = bad
            with self.assertRaises(ValueError):
                validate(value)

    def test_rejects_incomplete_judgment(self):
        with self.assertRaises(ValueError):
            validate({"scores": {}, "reason": "Missing scores"})

    def test_missing_supported_source_is_conservatively_unknown(self):
        value = {
            "scores": dict.fromkeys(METRICS, 1),
            "reason": "Judge omitted the evidence ID",
            "claims": [{"text": "Đất đai", "source_ids": [], "verdict": "supported"}],
        }
        normalize_missing_claim_evidence(value, "Lĩnh vực là Đất đai.")
        validate_claims(value["claims"], "Lĩnh vực là Đất đai.")
        self.assertEqual(value["claims"][0]["verdict"], "unknown")
        self.assertIsNone(value["scores"]["source_groundedness"])
        self.assertIsNone(value["scores"]["retrieved_context_faithfulness"])

    def test_invalid_claim_span_suppresses_claim_metrics(self):
        value = {
            "scores": dict.fromkeys(METRICS, 1),
            "reason": "Judge paraphrased the answer",
            "claims": [{"text": "Không phải exact span", "source_ids": ["ctx-1"],
                        "verdict": "supported"}],
        }
        normalize_missing_claim_evidence(value, "Lĩnh vực là Đất đai.")
        validate_claims(value["claims"], "Lĩnh vực là Đất đai.")
        self.assertEqual(value["claims"], [])
        self.assertIsNone(value["scores"]["source_groundedness"])
        self.assertIsNone(value["scores"]["retrieved_context_faithfulness"])

    def test_unknown_claim_source_suppresses_claim_metrics(self):
        value = {
            "scores": dict.fromkeys(METRICS, 1),
            "reason": "Judge invented an evidence ID",
            "claims": [{"text": "Đất đai", "source_ids": ["invented"],
                        "verdict": "supported"}],
        }
        normalize_missing_claim_evidence(value, "Lĩnh vực là Đất đai.", {"ctx-1"})
        self.assertEqual(value["claims"], [])
        self.assertIsNone(value["scores"]["source_groundedness"])
