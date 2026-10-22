import unittest

from vigovbot.evaluation.ollama_judge import METRICS, validate


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
