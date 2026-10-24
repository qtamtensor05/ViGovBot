import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from vigovbot.evaluation.io import read_jsonl
from vigovbot.evaluation.retrieval_benchmark import rerank_retrieval, run_retrieval, score_retrieval


class RetrievalBenchmarkTests(unittest.TestCase):
    def _dataset(self, root):
        dataset = root / "dataset"
        dataset.mkdir()
        (dataset / "views.json").write_text('["q1"]', encoding="utf-8")
        (dataset / "runner_queries.jsonl").write_text(
            json.dumps({"id": "q1", "question": "Hồ sơ gồm gì?", "split": "test"}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        case = {
            "id": "q1", "split": "test", "evidence": [{"unit_id": "u1"}],
        }
        (dataset / "cases.jsonl").write_text(json.dumps(case) + "\n", encoding="utf-8")
        (dataset / "knowledge_units.jsonl").write_text(
            json.dumps({"unit_id": "u1", "source_sha256": "source"}) + "\n", encoding="utf-8"
        )
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
                dataset=dataset, view="views.json", split="test", config_path=config,
                output=output, top_k=20,
            )
            rows = list(read_jsonl(output))
        retriever.search.assert_called_once_with("Hồ sơ gồm gì?", 20)
        self.assertEqual(rows[0]["retrieved_chunk_ids"], ["c1"])
        self.assertEqual(rows[0]["context_used"][0]["included_text"], "Hồ sơ A")
        self.assertFalse(report["inference_performed"])
        self.assertEqual(report["llm_calls"], 0)

    def test_score_uses_cached_rankings_and_multiple_k(self):
        with tempfile.TemporaryDirectory() as work:
            root = Path(work)
            dataset = self._dataset(root)
            predictions = root / "retrieval.jsonl"
            predictions.write_text(json.dumps({
                "id": "q1", "retrieved_chunk_ids": ["c1"],
                "context_used": [{"chunk_id": "c1", "included_text": "Hồ sơ A"}],
            }, ensure_ascii=False) + "\n", encoding="utf-8")
            import hashlib
            mapping = root / "mapping.json"
            mapping.write_text(json.dumps({
                "schema_version": 1,
                "review_kind": "human",
                "chunks": {"c1": {
                    "status": "reviewed", "reviewer": "reviewer", "reviewer_kind": "human",
                    "reason": "same evidence", "source_sha256": "source",
                    "chunk_sha256": hashlib.sha256("Hồ sơ A".encode("utf-8")).hexdigest(),
                    "unit_ids": ["u1"],
                }},
            }), encoding="utf-8")
            output = root / "scores.json"
            report = score_retrieval(
                dataset=dataset, view="views.json", split="test", predictions=predictions,
                unit_map=mapping, output=output, ks=[1, 3, 5],
            )
        self.assertEqual(report["retrieval_evaluation"]["1"]["end_to_end_all_eligible"]
                         ["judged_hit_rate_at_k"]["mean"], 1)
        self.assertEqual(report["ks"], [1, 3, 5])

    def test_golden_file_scores_context_ids_without_mapping(self):
        with tempfile.TemporaryDirectory() as work:
            root = Path(work)
            golden = root / "test_golden.jsonl"
            golden.write_text(json.dumps({
                "test_id": "TC_1",
                "input": {"question": "Câu hỏi gốc"},
                "ground_truth": {"ground_truth_standalone_query": "Không được dùng",
                                 "ground_truth_context_ids": ["c2"]},
            }, ensure_ascii=False) + "\n", encoding="utf-8")
            predictions = root / "retrieval.jsonl"
            predictions.write_text(json.dumps({
                "id": "TC_1", "question": "Câu hỏi gốc", "retrieved_chunk_ids": ["c1", "c2"],
                "context_used": [],
            }, ensure_ascii=False) + "\n", encoding="utf-8")
            output = root / "scores.json"
            report = score_retrieval(
                dataset=golden, view=None, split="test", predictions=predictions,
                unit_map=None, output=output, ks=[1, 2],
            )
        self.assertEqual(report["relevance_contract"], "golden_context_ids")
        self.assertEqual(report["retrieval_evaluation"]["1"]["end_to_end_all_eligible"]
                         ["judged_hit_rate_at_k"]["mean"], 0)
        self.assertEqual(report["retrieval_evaluation"]["2"]["end_to_end_all_eligible"]
                         ["judged_hit_rate_at_k"]["mean"], 1)

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
