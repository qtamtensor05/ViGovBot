import json
import tempfile
import unittest
from pathlib import Path

from tests.test_evaluation_v2 import golden, write_jsonl
from vigovbot.evaluation.records import build_record
from vigovbot.evaluation.extended import extend_record, load_reviews
from vigovbot.evaluation.ollama_judge import METRICS, judgment_payload
from vigovbot.evaluation.provenance import fingerprint
from vigovbot.evaluation.pairwise import pairwise


class ExtendedEvaluationTests(unittest.TestCase):
    def test_resume_does_not_regenerate_cached_answer(self):
        from vigovbot.evaluation.records import capture_predictions
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_jsonl(root / "test_golden.jsonl", [golden()])
            send = Mock(return_value={"results": [{"model_id": "qwen-base", "answer": "cached"}]})
            args = dict(dataset=root, split="test", architecture="base", output=root / "p.jsonl", post_json=send)
            capture_predictions(**args)
            capture_predictions(**args, resume=True)
            self.assertEqual(send.call_count, 1)
            with self.assertRaises(ValueError):
                capture_predictions(**args, resume=True, complete_trace=True)
    def test_subquery_coverage_and_review_scores(self):
        g = golden()
        g["ground_truth"].update(ground_truth_sub_queries=["Lệ phí?"], sub_query_context_mapping={"Lệ phí?": ["chunk-1"]})
        p = {"answer": "10.000 đồng", "actual_sub_queries": [{"query": "lệ phí", "sub_query_id": "sq_1"}], "sub_query_retrieval": {"sq_1": ["chunk-1"]}}
        record = build_record(g, p, split="test", run_id="r", architecture="rag_base", model_config={"model_name": "m"}, provenance={})
        extend_record(record, p)
        self.assertEqual(record["evaluation_results"]["query_processing_scores"]["sub_query_recall"], 1)
        self.assertEqual(record["evaluation_results"]["retrieval_scores"]["multi_intent_retrieval_coverage"], 1)

    def test_stream_records_first_content_and_provider_usage(self):
        from unittest.mock import Mock, patch
        from vigovbot.llm.llm_client import ollama_answer
        response = Mock()
        response.iter_lines.return_value = [
            b'{"message":{"content":"hello"},"done":false}',
            b'{"message":{"content":" world"},"done":true,"prompt_eval_count":7,"eval_count":2,"eval_duration":1000000000}',
        ]
        settings = dict(ollama_url="http://localhost:11434", model="fixture", temperature=0,
                        num_ctx=2048, num_predict=128, seed=42, keep_alive="0", timeout=5, measure_ttft=True)
        import sys
        from types import SimpleNamespace
        with patch.dict(sys.modules, {"requests": SimpleNamespace(post=Mock(return_value=response))}):
            answer, raw, duration = ollama_answer([], settings)
        self.assertEqual(answer, "hello world")
        self.assertEqual(raw["eval_count"], 2)
        self.assertGreaterEqual(duration, raw["ttft_seconds"])
        response.close.assert_called_once()

    def test_map_requires_declared_depth_and_deduplicates(self):
        g = golden()
        p = {"id": "TC_1", "answer": "ok", "retrieved_chunk_ids": ["noise", "chunk-1", "chunk-1"]}
        record = build_record(g, p, split="test", run_id="r", architecture="rag_base", model_config={"model_name": "m"}, provenance={})
        extend_record(record, p)
        self.assertIsNone(record["evaluation_results"]["retrieval_scores"]["map_at_10"])
        p["retrieval_top_k"] = 10
        extend_record(record, p)
        self.assertEqual(record["evaluation_results"]["retrieval_scores"]["map_at_10"], 0.5)
        import jsonschema
        schema = json.loads(Path("examples/evaluation_v2/evaluation_run_v2.schema.json").read_text(encoding="utf-8"))
        jsonschema.validate(record, schema)

    def test_stale_judgment_is_rejected(self):
        g, p = golden(), {"answer": "old"}
        review = {"id": "TC_1", "input_sha256": fingerprint(judgment_payload(g, p)),
                  "reviewer_kind": "human", "reviewer": "reviewer", "rubric_sha256": "v1",
                  "scores": dict.fromkeys(METRICS), "reason": "reviewed"}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "reviews.jsonl"
            write_jsonl(path, [review])
            p["answer"] = "changed"
            with self.assertRaises(ValueError):
                load_reviews(path, [g], {"TC_1": p})

    def test_pairwise_tie_and_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_jsonl(root / "test_golden.jsonl", [golden()])
            for name in ("a", "b"):
                write_jsonl(root / (name + ".jsonl"), [{"id": "TC_1", "answer": name}])
            args = dict(dataset=root, split="test", predictions=root / "a.jsonl", other=root / "b.jsonl")
            pairwise(**args, output=root / "packets.jsonl")
            packet = json.loads((root / "packets.jsonl").read_text(encoding="utf-8"))
            packet.update(winner="tie", reviewer="human", reason="equivalent")
            write_jsonl(root / "reviews.jsonl", [packet])
            result = pairwise(**args, judgments=root / "reviews.jsonl", output=root / "summary.json")
            self.assertEqual(result["left_tie_adjusted_rate"], 0.5)
