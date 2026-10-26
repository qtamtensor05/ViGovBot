import unittest
from unittest.mock import Mock, patch

from vigovbot.retrieval.reranker import rerank_hits


class RerankerTests(unittest.TestCase):
    def test_scores_candidates_and_keeps_top_k_with_provenance(self):
        hits = [
            {"chunk_id": "a", "score": 0.9, "text_content": "A"},
            {"chunk_id": "b", "score": 0.8, "text_content": "B"},
            {"chunk_id": "c", "score": 0.7, "text_content": "C"},
            {"chunk_id": "d", "score": 0.6, "text_content": "D"},
        ]
        model = Mock()
        model.score.return_value = [0.1, 0.9, 0.8, 0.2]
        settings = {
            "top_k": 3,
            "reranker": {
                "enabled": True,
                "model": "mini",
                "device": "cpu",
                "batch_size": 20,
                "max_length": 512,
            },
        }
        with patch("vigovbot.retrieval.reranker.load_reranker", return_value=model):
            ranked = rerank_hits("Câu hỏi", hits, settings)
        self.assertEqual([item["chunk_id"] for item in ranked], ["b", "c", "d"])
        self.assertEqual([item["faiss_rank"] for item in ranked], [2, 3, 4])
        self.assertEqual([item["rerank_rank"] for item in ranked], [1, 2, 3])
        model.score.assert_called_once_with([
            ("Câu hỏi", "A"), ("Câu hỏi", "B"), ("Câu hỏi", "C"), ("Câu hỏi", "D"),
        ])

    def test_disabled_reranker_only_cuts_to_final_depth(self):
        hits = [{"chunk_id": str(i)} for i in range(5)]
        self.assertEqual(
            rerank_hits("q", hits, {"top_k": 3, "reranker": {"enabled": False}}),
            hits[:3],
        )

    def test_explicit_section_intent_is_preserved_before_cross_encoder_score(self):
        hits = [
            {"chunk_id": "steps", "score": 0.9, "section_type": "procedure_step", "text_content": "Các bước"},
            {"chunk_id": "identity", "score": 0.5, "section_type": "metadata_identity",
             "text_content": "Số quyết định: 3826/QĐ-UBND"},
        ]
        model = Mock()
        model.score.return_value = [0.99, 0.01]
        settings = {
            "top_k": 1,
            "reranker": {"enabled": True, "model": "mini", "device": "cpu",
                           "batch_size": 20, "max_length": 512},
        }
        with patch("vigovbot.retrieval.reranker.load_reranker", return_value=model):
            ranked = rerank_hits("Số quyết định của thủ tục là gì?", hits, settings)
        self.assertEqual(ranked[0]["chunk_id"], "identity")


if __name__ == "__main__":
    unittest.main()
