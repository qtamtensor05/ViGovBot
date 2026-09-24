"""Vérification cấu hình/CLI và orchestration độc lập với Colab/model weights."""
import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import faiss
import numpy as np

from src.rag.config import load_config, RAGConfig
from src.rag.pipeline import execute, source_fingerprint


class ConfigTests(unittest.TestCase):
    def test_relative_paths_resolve_against_yaml(self):
        with tempfile.TemporaryDirectory() as work:
            path = Path(work) / "rag.yaml"
            path.write_text("data:\n  unified_source: unified.zip\n  dataset_path: qa_test/dataset.jsonl\n", encoding="utf-8")
            config = load_config(path)
            self.assertEqual(config.data.unified_source, Path(work).resolve() / "unified.zip")
            self.assertEqual(config.data.dataset_path, Path(work).resolve() / "qa_test/dataset.jsonl")
            self.assertEqual(config.inference_settings()["top_k"], 5)

    def test_config_rejects_typos_and_invalid_budget(self):
        data = {"unified_source": "unified.zip", "dataset_path": "qa.jsonl"}
        for overrides in ({"retrieval": {"top_k": 0}}, {"llm": {"num_ctx": 500, "num_predict": 512}},
                          {"evaluation": {"max_cases": 0}}, {"unknown": True}):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                RAGConfig.model_validate({"data": data, **overrides})

    def test_cli_routes_without_pdf_dependencies(self):
        from src.rag.__main__ import main
        with patch("src.rag.__main__.load_config", return_value="test"), patch(
                "src.rag.pipeline.execute", return_value={"ok": True}) as execute_mock:
            self.assertEqual(main(["--config", "test.yaml", "prepare"]), 0)
        execute_mock.assert_called_once_with("test", "prepare")

    def test_pipeline_smoke_evaluate_resume_and_report(self):
        with tempfile.TemporaryDirectory() as work:
            root = Path(work)
            corpus = root / "unified"
            corpus.mkdir()
            v = np.zeros((1, 1024), dtype=np.float32)
            v[0, 0] = 1
            index = faiss.IndexFlatIP(1024)
            index.add(v)
            faiss.write_index(index, str(corpus / "tthc_unified.index"))
            records = [{"chunk_id": "c1", "source_code": "1", "source_file": "1.pdf", "procedure_name": "Thủ tục",
                        "section_type": "fees", "context_prefix": "", "text_content": "Phí 0 đồng"}]
            (corpus / "tthc_unified_metadata.json").write_text(json.dumps(records), encoding="utf-8")
            dataset = root / "dataset.jsonl"
            case = {"id": "q1", "question": {"text": "Phí?", "type": "fees", "difficulty": "easy"},
                    "ground_truth": {"answer": "0 đồng"}, "rag_context": [{"text": "secret"}]}
            dataset.write_text(json.dumps(case) + "\n", encoding="utf-8")
            config = RAGConfig.model_validate({"data": {"unified_source": corpus, "dataset_path": dataset,
                                                       "cache_dir": root / "cache", "output_dir": root / "out"}})
            class Encoder:
                def encode(self, *args, **kwargs): return v.copy()
            class Tokenizer:
                def encode(self, text, **kwargs): return list(map(ord, text))
                def decode(self, ids): return "".join(map(chr, ids))
                def apply_chat_template(self, messages, **kwargs): return self.encode(str(messages))
            transformers = types.SimpleNamespace(AutoTokenizer=types.SimpleNamespace(from_pretrained=lambda *a, **kw: Tokenizer()))
            torch = types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: False))
            with patch.dict("sys.modules", {"transformers": transformers, "torch": torch}), patch(
                    "src.rag.pipeline.load_encoder", return_value=Encoder()), patch(
                    "src.rag.pipeline.check_model", return_value={"digest": "abc"}), patch(
                    "src.rag.pipeline.unload_model"), patch(
                    "src.rag.pipeline.ollama_answer", return_value=("0 đồng", {}, 0.1)) as chat:
                self.assertEqual(execute(config, "prepare")["count"], 1)
                self.assertEqual(execute(config, "smoke")["smoke_cases"], 1)
                result = execute(config, "evaluate")
                self.assertEqual(result, {"completed": 1, "requested": 1})
                n = chat.call_count
                execute(config, "evaluate")
                self.assertEqual(chat.call_count, n)
                prompts = chat.call_args.args[0]
                self.assertNotIn("secret", str(prompts))
            with patch("src.evaluation.report.compute_bertscore", return_value=([1.0], [1.0], [1.0])):
                summary = execute(config, "report")
            self.assertEqual(summary["n_cases"], 1)
            self.assertTrue((root / "out/metrics.png").exists())
            self.assertEqual(len(source_fingerprint()), 64)
            config.retrieval.top_k = 2
            with self.assertRaisesRegex(ValueError, "không khớp"):
                execute(config, "report")


if __name__ == "__main__":
    unittest.main()
