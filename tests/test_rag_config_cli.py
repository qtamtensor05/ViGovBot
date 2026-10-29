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
    from vigovbot.rag.pipeline import source_fingerprint
except ModuleNotFoundError as exc:
    skip_missing_dependency(exc)


class ConfigTests(unittest.TestCase):
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
                    previous = source_fingerprint()
                    self.assertNotEqual(current, previous, name)

    def test_inference_ollama_urls_share_yaml_anchor(self):
        import yaml
        for name in ("inference.yaml", "inference-docker.yaml", "inference-docker-ollama.yaml"):
            config = yaml.safe_load((Path("configs/rag") / name).read_text(encoding="utf-8"))
            for model in config["web"]["models"]:
                if model["provider"] == "ollama":
                    self.assertEqual(model["base_url"], config["llm"]["ollama_url"])

    def test_inference_profiles_send_top_five_directly_to_llm(self):
        for name in ("inference.yaml", "inference-docker.yaml", "inference-docker-ollama.yaml"):
            config = load_config(Path("configs/rag") / name)
            settings = config.inference_settings()
            self.assertEqual(settings["top_k"], 5)
            self.assertNotIn("candidate_top_k", settings)
            self.assertNotIn("reranker", settings)

    def test_ollama_docker_profile_excludes_local_transformers(self):
        config = load_config(Path("configs/rag/inference-docker-ollama.yaml"))
        self.assertEqual([model.id for model in config.web.models], ["qwen-base", "qwen-rag"])
        self.assertTrue(all(model.provider == "ollama" for model in config.web.models))
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
            self.assertTrue(config.conversation.routing_model_path.is_absolute())

    def test_qlora_adapter_environment_override_and_yaml_fallback(self):
        root = Path(__file__).resolve().parents[1]
        with patch.dict(os.environ, {}, clear=True):
            config = load_config(root / "configs/rag/inference.yaml")
            adapters = [m for m in config.web.models if m.adapter_path is not None]
            self.assertEqual(len(adapters), 2)
            self.assertTrue(all(m.adapter_path == root / "outputs/qlora/best_adapter" for m in adapters))
        with patch.dict(os.environ, {"QLORA_ADAPTER_PATH": "custom-adapter"}):
            config = load_config(root / "configs/rag/inference.yaml")
            adapters = [m for m in config.web.models if m.adapter_path is not None]
            self.assertTrue(all(m.adapter_path == Path("custom-adapter").resolve() for m in adapters))

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
