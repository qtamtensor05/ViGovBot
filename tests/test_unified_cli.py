import os
import unittest
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from training.config import load_config
from vigovbot.cli.main import app, main
from vigovbot.configuration import load_configuration
from vigovbot.rag.config import load_config as load_rag_config


ROOT = Path(__file__).resolve().parents[1]


class UnifiedCliTests(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

    def test_required_command_tree_is_visible(self):
        result = self.runner.invoke(app, ["--help"])
        self.assertEqual(result.exit_code, 0, result.output)
        for command in ("doctor", "data", "gpu", "train", "dashboard", "eval", "report"):
            self.assertIn(command, result.output)
        train_help = self.runner.invoke(app, ["train", "--help"])
        for command in ("smoke", "start", "status", "logs", "stop", "resume"):
            self.assertIn(command, train_help.output)

    def test_doctor_and_data_stats_are_lightweight(self):
        with patch.dict(os.environ, {"VIGOVBOT_PROJECT_ROOT": str(ROOT)}):
            doctor = self.runner.invoke(app, ["doctor"])
            stats = self.runner.invoke(app, ["data", "stats", "--config", "configs/training/base.yaml"])
        self.assertEqual(doctor.exit_code, 0, doctor.output)
        self.assertIn('"status": "PASS"', doctor.output)
        self.assertEqual(stats.exit_code, 0, stats.output)
        self.assertIn('"train"', stats.output)

    def test_legacy_dispatch_remains_available(self):
        with patch("vigovbot.cli.main._legacy", return_value=7) as legacy:
            self.assertEqual(main(["rag", "--help"]), 7)
        legacy.assert_called_once_with(["rag", "--help"])

    def test_cli_override_wins_over_environment(self):
        key = "VIGOVBOT_QLORA__TRAINING__LEARNING_RATE"
        with patch.dict(os.environ, {key: "0.1"}):
            config = load_config(ROOT / "configs" / "training" / "base.yaml", ["training.learning_rate=0.0003"])
        self.assertEqual(config["training"]["learning_rate"], 0.0003)

    def test_canonical_config_layers_load(self):
        smoke = load_config(ROOT / "configs" / "training" / "experiments" / "smoke.yaml")
        self.assertEqual(smoke["execution"]["max_steps"], 4)
        self.assertEqual(smoke["quantization"]["bnb_4bit_quant_type"], "nf4")

    def test_configs_are_grouped_and_resolve_project_paths(self):
        pipeline, _, _ = load_configuration(ROOT / "configs" / "ingestion" / "pipeline.yaml")
        rag = load_rag_config(ROOT / "configs" / "rag" / "inference.yaml")
        self.assertEqual(pipeline.input, (ROOT / "Data" / "pdf").resolve())
        self.assertEqual(rag.data.unified_source, (ROOT / "Data" / "vector" / "unified").resolve())
        for old_path in (
            "config.yaml",
            "rag_config.yaml",
            "configs/base.yaml",
            "configs/pipeline.yaml",
            "configs/inference.yaml",
            "configs/rag.yaml",
        ):
            self.assertFalse((ROOT / old_path).exists(), old_path)


if __name__ == "__main__":
    unittest.main()
