import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from vigovbot.evaluation.io import read_jsonl
from vigovbot.evaluation.retrieval_benchmark import rerank_retrieval, run_retrieval
from tests.schema_fixtures import validator


class RetrievalBenchmarkTests(unittest.TestCase):
    def _dataset(self, root):
        from tests.test_evaluation_v3 import golden
        dataset = root / "dataset"
        dataset.mkdir()
        row = golden("q1")
        row["input"]["question"] = "Hồ sơ gồm gì?"
        row["ground_truth"]["ground_truth_context_ids"] = ["c1"]
        (dataset / "test_golden.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
        return dataset

    @patch("vigovbot.evaluation.retrieval_benchmark.load_config")
    @patch("vigovbot.evaluation.retrieval_benchmark.retrieval_session")
    def test_run_uses_retriever_only_and_writes_ranked_artifact(self, session, load_config):
        retriever = MagicMock()
        retriever.search.return_value = [{
            "row_id": 4, "score": 0.8, "chunk_id": "c1", "source_file": "pdf/1.pdf",
            "source_code": "1", "procedure_name": "P", "section_type": "required_documents",
            "text_content": "Hồ sơ A",
        }]
        session.return_value.__enter__.return_value = (retriever, {
            "cache_sha256": {"index": "index-hash", "database": "db-hash"},
            "embedding": {"model": "BAAI/bge-m3", "revision": "r"},
        })
        with tempfile.TemporaryDirectory() as work:
            root = Path(work)
            dataset = self._dataset(root)
            config = root / "config.yaml"
            config.write_text("config", encoding="utf-8")
            output = root / "retrieval.jsonl"
            report = run_retrieval(
                dataset=dataset, view=None, split="test", config_path=config,
                output=output, top_k=20,
            )
            rows = list(read_jsonl(output))
        retriever.search.assert_called_once_with("Hồ sơ gồm gì?", 20)
        validator("prediction").validate(rows[0])
        contexts = rows[0]["execution"]["retrieval"]["contexts"]
        self.assertEqual([item["context_id"] for item in contexts], ["c1"])
        self.assertEqual(contexts[0]["text"], "Hồ sơ A")
        self.assertFalse(report["inference_performed"])
        self.assertEqual(report["llm_calls"], 0)

    def test_rerank_reorders_cached_candidates_and_adds_total_time(self):
        with tempfile.TemporaryDirectory() as work:
            root = Path(work)
            predictions = root / "top20.jsonl"
            predictions.write_text(json.dumps({
                "id": "q1", "question": "q", "retrieved_chunk_ids": ["c1", "c2"],
                "retrieved_scores": [0.9, 0.8],
                "retrieved": [
                    {"chunk_id": "c1", "rank": 1, "score": 0.9},
                    {"chunk_id": "c2", "rank": 2, "score": 0.8},
                ],
                "context_used": [
                    {"chunk_id": "c1", "included_text": "wrong"},
                    {"chunk_id": "c2", "included_text": "right"},
                ],
            }) + "\n", encoding="utf-8")
            baseline = root / "top20.jsonl.run.json"
            baseline.write_text('{"wall_seconds": 2.5}', encoding="utf-8")
            output = root / "reranked.jsonl"

            def loader(*_args):
                return (lambda pairs: [0.1 if pair[1] == "wrong" else 0.9 for pair in pairs], {
                    "model": "fake", "model_load_seconds": 0.0,
                })

            report = rerank_retrieval(
                predictions=predictions, output=output, model_name="fake", device="cpu",
                batch_size=2, max_length=32, retrieval_run_manifest=baseline, scorer_loader=loader,
            )
            row = next(read_jsonl(output))
        self.assertEqual(row["retrieved_chunk_ids"], ["c2", "c1"])
        self.assertEqual(row["retrieved"][0]["faiss_rank"], 2)
        self.assertGreater(report["retrieval_plus_rerank_wall_seconds"], 2.5)
        self.assertEqual(report["llm_calls"], 0)


if __name__ == "__main__":
    unittest.main()
