import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from tests.test_evaluation_v2 import golden, write_jsonl


class CompleteCaptureTests(unittest.TestCase):
    def test_extended_offline_scores_from_cached_answers(self):
        import sys
        import numpy as np
        from types import SimpleNamespace
        from vigovbot.evaluation.offline_v2 import score_offline_v2
        class Encoder:
            def encode(self, texts, **kwargs):
                return np.array([[1.0, 0.0] for _ in texts])
            def __getitem__(self, index):
                return SimpleNamespace(auto_model=SimpleNamespace(config=SimpleNamespace(_commit_hash="fixture")))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_jsonl(root / "test_golden.jsonl", [golden()])
            write_jsonl(root / "p.jsonl", [{"id": "TC_1", "answer": "fixture"}])
            with patch.dict(sys.modules, {"sentence_transformers": SimpleNamespace(SentenceTransformer=lambda *a, **k: Encoder())}), patch("vigovbot.evaluation.offline_v2.meteor_vi", return_value=0.75):
                report = score_offline_v2(dataset=root, split="test", predictions=root / "p.jsonl",
                                          architecture="base", output=root / "scores.json", extended=True)
            self.assertEqual(report["metrics"]["lexical"]["meteor"], 0.75)
            self.assertEqual(report["metrics"]["lexical"]["embedding_cosine_similarity"], 1.0)
            self.assertIn("chrf_pp", report["metrics"]["lexical"])

    def test_preflight_missing_gpu_prevents_inference(self):
        from vigovbot.evaluation.complete import complete
        response = Mock()
        from vigovbot.evaluation.complete import REQUIRED_WEB_CAPABILITIES
        response.json.side_effect = [{
            "evaluation_complete_version": 2,
            "evaluation_complete_capabilities": {name: True for name in REQUIRED_WEB_CAPABILITIES},
        }, {"status": "unavailable"}]
        with tempfile.TemporaryDirectory() as tmp, patch("requests.get", return_value=response), patch("importlib.util.find_spec", return_value=True), patch("vigovbot.evaluation.complete.run_v2") as run:
            with self.assertRaisesRegex(ValueError, "GPU sampler"):
                complete(dataset=Path(tmp), split="test", architecture="base", output=Path(tmp), model_id="m",
                         judge_model="j", endpoint="http://localhost:8001/api/chat", judge_endpoint="http://localhost:11434",
                         bert_model="b", bert_device="cpu", bert_batch_size=1)
            run.assert_not_called()

    def test_preflight_missing_trace_capability_prevents_inference(self):
        from vigovbot.evaluation.complete import complete
        response = Mock()
        response.json.return_value = {
            "evaluation_complete_version": 2,
            "evaluation_complete_capabilities": {"automatic_complete_trace": True},
        }
        with tempfile.TemporaryDirectory() as tmp, patch("requests.get", return_value=response), patch("vigovbot.evaluation.complete.run_v2") as run:
            with self.assertRaisesRegex(ValueError, "provider_call_token_usage"):
                complete(dataset=Path(tmp), split="test", architecture="base", output=Path(tmp), model_id="m",
                         judge_model="j", endpoint="http://localhost:8001/api/chat", judge_endpoint="http://localhost:11434",
                         bert_model="b", bert_device="cpu", bert_batch_size=1)
            run.assert_not_called()

    def test_gpu_device_units_and_scope(self):
        from vigovbot.server.gpu_metrics import GPUSampler
        with patch("vigovbot.server.gpu_metrics.subprocess.run", return_value=Mock(returncode=0, stdout="GPU-a, 2048, 75\n")):
            sampler = GPUSampler()
            sampler.collect()
        result = sampler.report()
        self.assertEqual(result["peak_device_memory_used_gib"], 2)
        self.assertEqual(result["mean_device_utilization_percent"], 75)
        self.assertIn("device-wide", result["scope"])

    def test_noise_replays_prompt_and_resume_skips_generation(self):
        from vigovbot.evaluation.noise import run_noise
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            g = golden()
            g["ground_truth"]["distractor_injection"] = {"distractor_contexts": ["irrelevant distractor"]}
            write_jsonl(root / "test_golden.jsonl", [g])
            original = [{"role": "user", "content": "fixed clean prompt"}]
            write_jsonl(root / "clean.jsonl", [{"id": "TC_1", "answer": "clean", "context_used": [{"chunk_id": "c"}],
                                               "provider_calls": [{"messages": original}]}])
            response = {"results": [{"answer": "noisy", "evaluation_trace": {}}]}
            with patch("vigovbot.evaluation.noise._post_json", return_value=response) as post:
                args = dict(dataset=root, split="test", predictions=root / "clean.jsonl", output=root / "noise.jsonl", endpoint="http://fixture", model_id="m")
                run_noise(**args)
                sent = post.call_args.args[1]["evaluation_replay"]["messages"]
                self.assertTrue(sent[-1]["content"].startswith("fixed clean prompt"))
                self.assertIn("irrelevant distractor", sent[-1]["content"])
                self.assertNotIn(g["ground_truth"]["expected_answer"], sent[-1]["content"])
                run_noise(**args)
                self.assertEqual(post.call_count, 1)
            row = json.loads((root / "noise.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(row["noise_experiment"]["clean_answer"], "clean")

    def test_noise_score_is_offline_and_hash_bound(self):
        from vigovbot.evaluation.noise import score_noise
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_jsonl(root / "clean.jsonl", [{"id": "TC_1", "scores": {"semantic_correctness": 1}}])
            write_jsonl(root / "noise.jsonl", [{"id": "TC_1", "scores": {"semantic_correctness": 1}}])
            report = score_noise(clean_judgments=root / "clean.jsonl", noise_judgments=root / "noise.jsonl",
                                 output=root / "score.json")
            self.assertEqual(report["metrics"]["noise_robustness_pass_rate"], 1)
            self.assertIn("noise_judgments_sha256", report["provenance"])

    def test_failed_prediction_retries_only_failed_case(self):
        from vigovbot.evaluation.v2 import run_v2
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_jsonl(root / "test_golden.jsonl", [golden("TC_1"), golden("TC_2")])
            send = Mock(side_effect=[{"results": [{"model_id": "qwen-base", "answer": "ok"}]}, RuntimeError("offline")])
            args = dict(dataset=root, split="test", architecture="base", output=root / "predictions.jsonl")
            run_v2(**args, post_json=send)
            send = Mock(return_value={"results": [{"model_id": "qwen-base", "answer": "recovered"}]})
            run_v2(**args, post_json=send, resume=True)
            self.assertEqual(send.call_count, 1)
            self.assertEqual(len((root / "predictions.jsonl").read_text(encoding="utf-8").splitlines()), 2)
            self.assertEqual(len(list(root.glob("*.failed-attempt-*"))), 1)
