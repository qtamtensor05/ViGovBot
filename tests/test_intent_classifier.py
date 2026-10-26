"""Offline tests for FastText artifact validation and hybrid routing behavior."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from tests.tokenizer_fixtures import CharacterTokenizer

from vigovbot.rag.intent_classifier import (
    ClassifierArtifactError, FastTextIntentClassifier, IntentPrediction,
    classifier_text, load_metadata, read_dataset,
        VALID_LABELS,
)

try:
    from vigovbot.rag.pipeline import answer_question
except ModuleNotFoundError:
    answer_question = None


class ArtifactTests(unittest.TestCase):
    def artifact(self, root):
        model = root / "intent-router.bin"
        model.write_bytes(b"model")
        metadata = root / "intent-router.metadata.json"
        metadata.write_text(json.dumps({
            "schema_version": 1,
            "model_sha256": hashlib.sha256(b"model").hexdigest(),
            "dataset_sha256": "d" * 64,
            "labels": sorted(VALID_LABELS),
            "thresholds": {"in_scope.new_question": .92, "out_of_scope.new_question": .98},
        }), encoding="utf-8")
        return model, metadata

    def test_metadata_requires_matching_model_hash_and_taxonomy(self):
        with tempfile.TemporaryDirectory() as directory:
            model, metadata = self.artifact(Path(directory))
            self.assertEqual(load_metadata(metadata, model)["schema_version"], 1)
            model.write_bytes(b"changed")
            with self.assertRaisesRegex(ClassifierArtifactError, "SHA-256"):
                load_metadata(metadata, model)

    def test_classifier_prediction_applies_per_label_threshold(self):
        with tempfile.TemporaryDirectory() as directory:
            model, metadata = self.artifact(Path(directory))
            fake_model = SimpleNamespace(predict=Mock(
                return_value=(["__label__in_scope.new_question"], [.93])))
            fake_fasttext = SimpleNamespace(load_model=Mock(return_value=fake_model))
            with patch.dict("sys.modules", {"fasttext": fake_fasttext}):
                prediction = FastTextIntentClassifier(model, metadata).predict("Phí hộ chiếu?", [])
            self.assertTrue(prediction.accepted)
            self.assertEqual(prediction.scope, "in_scope")
            self.assertEqual(prediction.relation, "new_question")

    def test_dataset_rejects_group_leakage(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "routing.jsonl"
            rows = [
                {"id": "1", "split": "train", "group": "same", "question": "A", "history": [],
                 "scope": "in_scope", "relation": "new_question"},
                {"id": "2", "split": "test", "group": "same", "question": "B", "history": [],
                 "scope": "out_of_scope", "relation": "new_question"},
            ]
            path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "leakage"):
                read_dataset(path)

    def test_real_fasttext_can_train_save_load_and_predict(self):
        try:
            from vigovbot.rag.intent_classifier import train_artifact
            import fasttext  # noqa: F401
        except ImportError:
            self.skipTest("FastText is not installed")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = root / "routing.jsonl"
            rows = []
            examples = {
                "in_scope": ["Lệ phí hộ chiếu?", "Hồ sơ khai sinh?", "Thời hạn cấp căn cước?"],
                "out_of_scope": ["Viết bài thơ", "Nấu món phở", "Dự báo bóng đá"],
            }
            for split in ("train", "validation", "test"):
                for scope, questions in examples.items():
                    for index, question in enumerate(questions):
                        rows.append({"id": f"{split}-{scope}-{index}", "split": split,
                                     "group": f"{split}-{scope}-{index}", "question": question,
                                     "history": [], "scope": scope, "relation": "new_question"})
            for label in sorted(VALID_LABELS - {"in_scope.new_question", "out_of_scope.new_question"}):
                scope, relation = label.split(".")
                rows.append({"id": f"train-{label}", "split": "train", "group": f"train-{label}",
                             "question": f"Ví dụ {label}", "history": [{"role": "user", "content": "Hộ chiếu"}],
                             "scope": scope, "relation": relation})
            dataset.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8")
            model, metadata = train_artifact(dataset, root / "artifact", epoch=2)
            self.assertLess(model.stat().st_size, 20 * 1024 * 1024)
            loaded = FastTextIntentClassifier(model, metadata)
            self.assertIn(loaded.predict("Lệ phí hộ chiếu?", []).label,
                          {"in_scope.new_question", "out_of_scope.new_question"})

    def test_classifier_input_is_bounded_and_keeps_recent_history(self):
        history = [{"role": "user", "content": str(index) * 1500} for index in range(8)]
        text = classifier_text("  Còn lệ phí?  ", history)
        self.assertNotIn("0000", text)
        self.assertIn("7777", text)
        self.assertTrue(text.endswith("Còn lệ phí?"))


@unittest.skipIf(answer_question is None, "Optional RAG dependencies are not installed")
class HybridRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.settings = {
            "top_k": 5, "num_ctx": 8192, "num_predict": 512,
            "routing_num_ctx": 4096, "routing_num_predict": 128,
            "max_chunk_tokens": 1200, "routing_backend": "hybrid",
            "routing_model_path": "model.bin", "routing_metadata_path": "metadata.json",
        }
        self.retriever = Mock()
        self.retriever.search.return_value = [{
            "row_id": 1, "chunk_id": "c1", "score": .9, "source_file": "a.pdf",
            "source_code": "1", "section_type": "fees", "text_content": "Lệ phí 0 đồng",
        }]

    @staticmethod
    def classifier(label, confidence, accepted):
        model = Mock()
        threshold = .92 if label.startswith("in_scope") else .98
        model.predict.return_value = IntentPrediction(label, confidence, threshold, accepted, .001)
        return model

    def test_confident_new_question_skips_only_routing_llm_call(self):
        answer = json.dumps({"answer": "0 đồng", "action": "answer", "evidence_status": "sufficient"})
        with (
            patch("vigovbot.rag.intent_classifier.get_classifier",
                  return_value=self.classifier("in_scope.new_question", .99, True)),
            patch("vigovbot.rag.pipeline.ollama_answer", return_value=(answer, {}, .1)) as llm,
        ):
            result = answer_question("Lệ phí hộ chiếu?", self.retriever, CharacterTokenizer(), self.settings)
        self.assertEqual(llm.call_count, 1)
        self.assertEqual(result["routing_backend"], "fasttext")
        self.assertEqual(result["routing_attempts"], 0)
        self.assertEqual(result["classifier_confidence"], .99)
        self.retriever.search.assert_called_once_with("Lệ phí hộ chiếu?", 5)

    def test_uncertain_hybrid_prediction_falls_back_to_llm(self):
        route = json.dumps({"scope": "in_scope", "relation": "new_question",
                            "query": "Lệ phí?", "clarification": ""})
        answer = json.dumps({"answer": "0 đồng", "action": "answer", "evidence_status": "sufficient"})
        with (
            patch("vigovbot.rag.intent_classifier.get_classifier",
                  return_value=self.classifier("in_scope.follow_up", .70, False)),
            patch("vigovbot.rag.pipeline.ollama_answer", side_effect=[(route, {}, .1), (answer, {}, .1)]) as llm,
        ):
            result = answer_question("Lệ phí?", self.retriever, CharacterTokenizer(), self.settings)
        self.assertEqual(llm.call_count, 2)
        self.assertEqual(result["routing_backend"], "hybrid")
        self.assertEqual(result["routing_attempts"], 1)
        self.assertEqual(result["classifier_fallback_reason"], "classifier_not_confident")

    def test_missing_artifact_falls_back_to_llm(self):
        route = json.dumps({"scope": "out_of_scope", "relation": "new_question",
                            "query": "", "clarification": ""})
        with (
            patch("vigovbot.rag.intent_classifier.get_classifier",
                  side_effect=ClassifierArtifactError("missing")),
            patch("vigovbot.rag.pipeline.ollama_answer", return_value=(route, {}, .1)) as llm,
        ):
            result = answer_question("Viết thơ", self.retriever, CharacterTokenizer(), self.settings)
        self.assertEqual(llm.call_count, 1)
        self.assertEqual(result["routing_backend"], "hybrid")
        self.assertEqual(result["raw_routing"]["classifier"]["fallback_reason"], "classifier_unavailable")
        self.assertEqual(result["classifier_fallback_reason"], "classifier_unavailable")


if __name__ == "__main__":
    unittest.main()
