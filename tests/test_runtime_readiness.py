import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import typer

from vigovbot.artifacts import CORPUS_FILES, CORPUS_MANIFEST, embedding_identity, make_manifest
from vigovbot.cli.main import web
from vigovbot.runtime_readiness import PHOBERT_FILES, check_web_readiness


class WebReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir="tmp")
        self.root = Path(self.temporary.name)
        self.corpus = self.root / "vector"
        self.corpus.mkdir()
        files = []
        for name in CORPUS_FILES:
            path = self.corpus / name
            path.write_bytes(b"artifact")
            files.append(path)
        manifest = make_manifest("corpus", embedding_identity("a" * 40), 1, files)
        (self.corpus / CORPUS_MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")
        self.phobert = self.root / "phobert"
        for name in PHOBERT_FILES:
            path = self.phobert / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"model")
        self.config_path = self.root / "inference.yaml"
        self.config_path.write_text("data: {}", encoding="utf-8")

    def tearDown(self):
        self.temporary.cleanup()

    def config(self):
        return SimpleNamespace(
            data=SimpleNamespace(unified_source=self.corpus, cache_dir=self.root / "cache"),
            conversation=SimpleNamespace(
                routing_enabled=True,
                routing_backend="phobert",
                routing_phobert_path=self.phobert,
            ),
            embedding=SimpleNamespace(device="cpu"),
            llm=SimpleNamespace(model="qwen2.5:7b", ollama_url="http://localhost:11434"),
            web=SimpleNamespace(models=[]),
        )

    def run_check(self, config=None, *, probe_services=False):
        with (
            patch("vigovbot.runtime_readiness.load_config", return_value=config or self.config()),
            patch("vigovbot.runtime_readiness.importlib.util.find_spec", return_value=object()),
            patch("vigovbot.runtime_readiness._check_port", return_value=(True, "available")),
        ):
            report = check_web_readiness(self.config_path, probe_services=probe_services)
        return report

    def test_required_artifacts_pass_and_skipped_service_is_warning(self):
        report = self.run_check()
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["required_failures"], 0)
        self.assertEqual(report["warnings"], 1)

    def test_missing_vector_corpus_blocks_web(self):
        config = self.config()
        config.data.unified_source = self.root / "missing"
        report = self.run_check(config)
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("vector_corpus", {
            item["name"] for item in report["checks"] if item["status"] == "FAIL"
        })

    def test_missing_optional_models_do_not_block_web(self):
        warning = {"name": "ollama_models", "status": "WARN", "required": False, "detail": "missing"}
        with patch("vigovbot.runtime_readiness._ollama_check", return_value=[warning]):
            report = self.run_check(probe_services=True)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["warnings"], 1)

    def test_web_starts_with_optional_warnings_but_blocks_required_failure(self):
        with (
            patch("vigovbot.cli.main._config", return_value=self.config_path),
            patch("vigovbot.cli.main._web_readiness", return_value={"status": "PASS", "warnings": 2}),
            patch("vigovbot.cli.main._run_legacy") as run,
        ):
            web(self.config_path, "127.0.0.1", 8000)
        run.assert_called_once()

        with (
            patch("vigovbot.cli.main._config", return_value=self.config_path),
            patch("vigovbot.cli.main._web_readiness", return_value={"status": "FAIL", "warnings": 0}),
            patch("vigovbot.cli.main._run_legacy") as run,
            self.assertRaises(typer.Exit),
        ):
            web(self.config_path, "127.0.0.1", 8000)
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
