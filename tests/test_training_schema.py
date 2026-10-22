from tests.dependencies import skip_missing_dependency

import copy
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from pydantic import ValidationError
    from vigovbot.training.schema import TrainingConfig
    from vigovbot.training.config import load_config, validate_config
except ModuleNotFoundError as exc:
    skip_missing_dependency(exc)


class TrainingSchemaTests(unittest.TestCase):
    def test_all_repository_profiles_validate(self):
        for path in Path("configs/training").rglob("*.yaml"):
            with self.subTest(path=str(path)):
                self.assertIsInstance(load_config(path), TrainingConfig)

    def test_v100_throughput_profile_keeps_effective_batch(self):
        config = load_config("configs/training/environments/v100_32gb_golden_sft.yaml")
        self.assertEqual(config.training.per_device_train_batch_size * config.training.gradient_accumulation_steps, 8)
        self.assertEqual(config.training.per_device_eval_batch_size, 4)
        self.assertFalse(config.training.gradient_checkpointing)
        self.assertEqual(config.training.dataloader_num_workers, 4)
        self.assertTrue(config.training.dataloader_pin_memory)
        self.assertTrue(config.training.dataloader_persistent_workers)

    def test_experimental_models_need_explicit_opt_in(self):
        with patch.dict("os.environ", {}, clear=True):
            for name in ("Qwen/Qwen2.5-1.5B-Instruct", "Qwen/Qwen2.5-14B-Instruct", "custom/PhoGPT", "custom/Llama-3"):
                with self.subTest(model=name):
                    with self.assertRaisesRegex(ValidationError, "experimental"):
                        load_config("configs/training/base.yaml", [f"model.name={name}"])
                    config = load_config("configs/training/base.yaml", [f"model.name={name}", "model.experimental=true"])
                    self.assertEqual(config.model.name, name)

    def test_validation_does_not_mutate_snapshot(self):
        config = load_config("configs/training/base.yaml")
        before = copy.deepcopy(config)
        validate_config(config)
        self.assertEqual(config, before, "Schema validation must not insert defaults into checkpoint configuration")

    def test_unknown_keys_types_and_cadence_rejected(self):
        for expression in ("training.learing_rate=0.1", "model.max_seq_length=true", "training.eval_steps=0",
                           "training.save_steps=3", "quantization.load_in_4bit=false", "model.trust_remote_code=true",
                           "lora.target_modules=[q_proj,q_proj]", "execution.max_steps=0"):
            with self.subTest(override=expression), self.assertRaises(ValidationError):
                load_config("configs/training/base.yaml", [expression])

    def test_persistent_workers_require_worker_processes(self):
        with self.assertRaisesRegex(ValidationError, "Persistent dataloader workers"):
            load_config("configs/training/base.yaml", ["training.dataloader_persistent_workers=true"])

    def test_snapshot_preserves_omitted_defaults_and_private_paths(self):
        import tempfile
        import yaml
        from vigovbot.training.artifacts import snapshot_config
        config = load_config("configs/training/base.yaml")
        self.assertNotIn("experimental", config.snapshot()["model"])
        self.assertFalse(config.model.experimental)
        self.assertTrue(Path(config.project_root).is_absolute())
        with tempfile.TemporaryDirectory() as work:
            snapshot_config(config, Path(work))
            snapshot = yaml.safe_load((Path(work) / "config.yaml").read_text(encoding="utf-8"))
            self.assertEqual(snapshot, config.snapshot())
            self.assertNotIn("_project_root", snapshot)
            self.assertEqual(load_config(Path(work) / "config.yaml").snapshot(), snapshot)
