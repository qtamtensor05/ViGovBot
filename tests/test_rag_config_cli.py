"""Vérification cấu hình/CLI và orchestration độc lập với Colab/model weights."""
from tests.dependencies import skip_missing_dependency



import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    import faiss  # noqa: F401
except ModuleNotFoundError as exc:
    skip_missing_dependency(exc)

try:
    from vigovbot.rag.config import load_config, RAGConfig
    from vigovbot.rag.pipeline import _fingerprint_source_files, source_fingerprint
except ModuleNotFoundError as exc:
    skip_missing_dependency(exc)


class ConfigTests(unittest.TestCase):
    def test_fingerprint_reuses_contents_while_source_tree_is_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entry = root / "rag" / "pipeline.py"
            entry.parent.mkdir()
            entry.write_text("# pipeline", encoding="utf-8")
            with patch("vigovbot.rag.pipeline.__file__", str(entry)):
                before = _fingerprint_source_files.cache_info()
                self.assertEqual(source_fingerprint(), source_fingerprint())
                after = _fingerprint_source_files.cache_info()
                self.assertEqual(after.misses, before.misses + 1)
                self.assertEqual(after.hits, before.hits + 1)

    def test_fingerprint_covers_new_helpers_and_nested_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "rag").mkdir()
            entry = root / "rag" / "pipeline.py"
            entry.write_text("# pipeline", encoding="utf-8")
            with patch("vigovbot.rag.pipeline.__file__", str(entry)):
                previous = source_fingerprint()
                for name in ("utils/text.py", "utils/jsonl.py", "console.py", "chunking/nested/tables.py"):
                    path = root / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("# added", encoding="utf-8")
                    current = source_fingerprint()
                    self.assertNotEqual(previous, current, name)
                    self.assertEqual(current, source_fingerprint())
                    path.write_text("# modified", encoding="utf-8")
                    os.utime(path, ns=(path.stat().st_atime_ns, path.stat().st_mtime_ns + 1))
                    previous = source_fingerprint()
                    self.assertNotEqual(current, previous, name)

    def test_inference_ollama_urls_share_yaml_anchor(self):
        import yaml
        for name in ("inference.yaml", "inference-docker.yaml", "inference-docker-ollama.yaml"):
            config = yaml.safe_load((Path("configs/rag") / name).read_text(encoding="utf-8"))
            for model in config["web"]["models"]:
                if model["provider"] == "ollama":
                    self.assertEqual(model["base_url"], config["llm"]["ollama_url"])

    def test_inference_profiles_send_configured_top_k_directly_to_llm(self):
        expected = {"inference.yaml": 15, "inference-docker.yaml": 5,
                    "inference-docker-ollama.yaml": 15}
        for name, top_k in expected.items():
            config = load_config(Path("configs/rag") / name)
            settings = config.inference_settings()
            self.assertEqual(settings["top_k"], top_k)
            self.assertNotIn("candidate_top_k", settings)
            self.assertNotIn("reranker", settings)

    def test_ollama_docker_profile_excludes_local_transformers(self):
        config = load_config(Path("configs/rag/inference-docker-ollama.yaml"))
        self.assertEqual([model.id for model in config.web.models],
                         ["qwen-base", "qwen-rag", "qwen-qlora", "qwen-rag-qlora"])
        self.assertTrue(all(model.provider == "ollama" for model in config.web.models))
        merged = [model for model in config.web.models if "qlora" in model.id]
        self.assertEqual({model.model for model in merged}, {"qwen-qlora-rag-sft:latest"})
        self.assertEqual({model.mode for model in merged}, {"qlora", "rag"})
        lock = Path("locks/ollama-web-linux-py312.txt").read_text(encoding="utf-8")
        self.assertIn("torch==2.9.1+cpu", lock)
        self.assertNotIn("nvidia-", lock)
        self.assertNotIn("bitsandbytes", lock)

    def test_relative_paths_resolve_against_yaml(self):
        with tempfile.TemporaryDirectory() as work:
            path = Path(work) / "rag.yaml"
            path.write_text(
                "data:\n  unified_source: unified.zip\n  cache_dir: cache\n", encoding="utf-8"
            )
            config = load_config(path)
            self.assertEqual(config.data.unified_source, Path(work).resolve() / "unified.zip")
            self.assertEqual(config.data.cache_dir, Path(work).resolve() / "cache")
            self.assertEqual(config.inference_settings()["top_k"], 5)
            self.assertTrue(config.inference_settings()["routing_enabled"])
            self.assertEqual(config.inference_settings()["routing_backend"], "phobert")

    def test_merged_qlora_can_use_ollama_without_adapter(self):
        config = load_config(Path("configs/rag/inference.yaml"))
        qlora = next(model for model in config.web.models if model.id == "qwen-qlora")
        self.assertEqual((qlora.provider, qlora.model, qlora.mode),
                         ("ollama", "qwen-qlora-rag-sft:latest", "qlora"))
        self.assertIsNone(qlora.adapter_path)
        with self.assertRaises(ValueError):
            RAGConfig.model_validate({"data": {"unified_source": "unified.zip"}, "web": {"models": [{
                "id": "bad", "label": "Bad", "provider": "ollama", "model": "merged",
                "base_url": "http://localhost", "mode": "qlora", "adapter_path": "adapter",
            }]}})

    def test_rag_sft_evaluation_profile_is_isolated(self):
        config = load_config(Path("configs/rag/evaluation-qlora-rag-sft.yaml"))
        merged = [model for model in config.web.models if "qlora" in model.id]
        self.assertEqual({model.model for model in merged}, {"qwen-qlora-rag-sft:latest"})
        self.assertEqual({model.id for model in merged}, {"qwen-qlora", "qwen-rag-qlora"})
        self.assertEqual(config.inference_settings()["top_k"], 15)

    def test_config_rejects_typos_and_invalid_budget(self):
        data = {"unified_source": "unified.zip", "dataset_path": "qa.jsonl"}
        for overrides in (
            {"retrieval": {"top_k": 0}},
            {"retrieval": {"top_k": 3, "candidate_top_k": 2}},
            {"llm": {"num_ctx": 500, "num_predict": 512}},
            {"evaluation": {"max_cases": 0}},
            {"web": {"models": [{"id": "x", "label": "X", "provider": "ollama", "model": "qwen",
                                  "base_url": "http://localhost", "mode": "unknown"}]}},
            {"unknown": True},
        ):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                RAGConfig.model_validate({"data": data, **overrides})

    def test_cli_routes_without_pdf_dependencies(self):
        from vigovbot.rag.__main__ import main

        with (
            patch("vigovbot.rag.__main__.load_config", return_value="test"),
            patch("vigovbot.rag.pipeline.execute", return_value={"ok": True}) as execute_mock,
        ):
            self.assertEqual(main(["--config", "test.yaml", "prepare"]), 0)
        execute_mock.assert_called_once_with("test", "prepare")

if __name__ == "__main__":
    unittest.main()
