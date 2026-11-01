import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from tests.test_evaluation_v3 import base_api_result, golden, prediction, write_jsonl


class CompleteCaptureTests(unittest.TestCase):
    def test_extended_offline_scores_from_cached_answers(self):
        import sys
        import numpy as np
        from types import SimpleNamespace
        from vigovbot.evaluation.scoring import score_supplemental
        class Encoder:
            def encode(self, texts, **kwargs):
                return np.array([[1.0, 0.0] for _ in texts])
            def __getitem__(self, index):
                return SimpleNamespace(auto_model=SimpleNamespace(config=SimpleNamespace(_commit_hash="fixture")))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_jsonl(root / "test_golden.jsonl", [golden()])
            write_jsonl(root / "p.jsonl", [prediction(golden(), "base")])
            with patch.dict(sys.modules, {"sentence_transformers": SimpleNamespace(SentenceTransformer=lambda *a, **k: Encoder())}), patch("vigovbot.evaluation.scoring.meteor_vi", return_value=0.75):
                report = score_supplemental(dataset=root, split="test", predictions=root / "p.jsonl",
                                          architecture="base", output=root / "scores.json", extended=True)
            self.assertEqual(report["metrics"]["lexical"]["meteor"], 0.75)
            self.assertEqual(report["metrics"]["lexical"]["embedding_cosine_similarity"], 1.0)
            self.assertIn("chrf_pp", report["metrics"]["lexical"])

    def test_gpu_device_units_and_scope(self):
        from vigovbot.server.gpu_metrics import GPUSampler
        with patch("vigovbot.server.gpu_metrics.subprocess.run", return_value=Mock(returncode=0, stdout="GPU-a, 2048, 75\n")):
            sampler = GPUSampler()
            sampler.collect()
        result = sampler.report()
        self.assertEqual(result["peak_device_memory_used_gib"], 2)
        self.assertEqual(result["mean_device_utilization_percent"], 75)
        self.assertIn("device-wide", result["scope"])

    def test_failed_prediction_retries_only_failed_case(self):
        from vigovbot.evaluation.records import capture_predictions
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_jsonl(root / "test_golden.jsonl", [golden("TC_1"), golden("TC_2")])
            send = Mock(side_effect=[{"results": [base_api_result("ok")]}, RuntimeError("offline")])
            args = dict(dataset=root, split="test", architecture="base", output=root / "predictions.jsonl")
            capture_predictions(**args, post_json=send)
            send = Mock(return_value={"results": [base_api_result("recovered")]})
            capture_predictions(**args, post_json=send, resume=True)
            self.assertEqual(send.call_count, 1)
            self.assertEqual(len((root / "predictions.jsonl").read_text(encoding="utf-8").splitlines()), 2)
            self.assertEqual(len(list(root.glob("*.failed-attempt-*"))), 1)
