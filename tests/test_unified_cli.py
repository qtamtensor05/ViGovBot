import os
import tempfile
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
        for command in ("doctor", "web", "ask", "data", "rag", "gpu", "train", "dashboard", "eval", "report"):
            self.assertIn(command, result.output)
        data_help = self.runner.invoke(app, ["data", "--help"])
        for command in ("check", "stats", "ingest", "embed"):
            self.assertIn(command, data_help.output)
        rag_help = self.runner.invoke(app, ["rag", "--help"])
        for command in ("prepare", "smoke", "evaluate", "report", "run"):
            self.assertIn(command, rag_help.output)
        for command in (["web", "--help"], ["ask", "--help"], ["data", "ingest", "--help"],
                        ["data", "embed", "--help"]):
            command_help = self.runner.invoke(app, command)
            self.assertEqual(command_help.exit_code, 0, command_help.output)
        train_help = self.runner.invoke(app, ["train", "--help"])
        for command in ("smoke", "start", "status", "logs", "stop", "resume"):
            self.assertIn(command, train_help.output)

    def test_doctor_and_data_stats_are_lightweight(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = {name: Path(folder) / f"{name}.jsonl" for name in ("train", "validation", "test")}
            for path in paths.values():
                path.write_text('{"messages": []}\n', encoding="utf-8")
            with patch.dict(os.environ, {"VIGOVBOT_PROJECT_ROOT": str(ROOT)}), \
                    patch("vigovbot.training.data.dataset_paths", return_value=paths):
                doctor = self.runner.invoke(app, ["doctor"])
                stats = self.runner.invoke(app, ["data", "stats", "--config", "configs/training/base.yaml"])
        self.assertEqual(doctor.exit_code, 0, doctor.output)
        self.assertIn('"status": "PASS"', doctor.output)
        self.assertEqual(stats.exit_code, 0, stats.output)
        self.assertIn('"train"', stats.output)
        self.assertIn('"records": 1', stats.output)

    def test_legacy_dispatch_remains_available(self):
        with patch("vigovbot.cli.main._legacy", return_value=7) as legacy:
            self.assertEqual(main(["rag", "--help"]), 7)
        legacy.assert_called_once_with(["rag", "--help"])

    def test_short_application_commands_delegate_to_existing_services(self):
        with patch("vigovbot.cli.main._legacy", return_value=0) as legacy:
            result = self.runner.invoke(app, ["ask", "Hồ sơ gồm những gì?"])
        self.assertEqual(result.exit_code, 0, result.output)
        args = legacy.call_args.args[0]
        self.assertEqual(args[0], "rag")
        self.assertIn("ask", args)
        self.assertIn("Hồ sơ gồm những gì?", args)

        with patch("vigovbot.cli.main._legacy", return_value=0) as legacy:
            result = self.runner.invoke(app, ["rag", "evaluate"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(legacy.call_args.args[0][0], "rag")
        self.assertIn("evaluate", legacy.call_args.args[0])

    def test_short_data_commands_delegate_with_project_rooted_paths(self):
        with patch("vigovbot.cli.main._legacy", return_value=0) as legacy:
            ingest = self.runner.invoke(app, ["data", "ingest", "--workers", "2"])
            embed = self.runner.invoke(app, ["data", "embed"])
        self.assertEqual(ingest.exit_code, 0, ingest.output)
        self.assertEqual(embed.exit_code, 0, embed.output)
        ingest_args = legacy.call_args_list[0].args[0]
        embed_args = legacy.call_args_list[1].args[0]
        self.assertEqual(ingest_args[0], "ingest")
        self.assertIn(str((ROOT / "configs" / "ingestion" / "pipeline.yaml").resolve()), ingest_args)
        self.assertEqual(embed_args[0], "embed")
        self.assertIn(str((ROOT / "outputs" / "metadata").resolve()), embed_args)

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
