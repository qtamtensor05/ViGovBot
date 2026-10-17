import copy
import unittest
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError
from vigovbot.training.config import load_config, validate_config


class TrainingSchemaTests(unittest.TestCase):
    def test_all_repository_profiles_validate(self):
        for path in Path("configs/training").rglob("*.yaml"):
            with self.subTest(path=str(path)):
                self.assertIsInstance(load_config(path), dict)

    def test_experimental_models_need_explicit_opt_in(self):
        with patch.dict("os.environ", {}, clear=True):
            for name in ("Qwen/Qwen2.5-1.5B-Instruct", "Qwen/Qwen2.5-14B-Instruct", "custom/PhoGPT", "custom/Llama-3"):
                with self.subTest(model=name):
                    with self.assertRaisesRegex(ValidationError, "experimental"):
                        load_config("configs/training/base.yaml", [f"model.name={name}"])
                    config = load_config("configs/training/base.yaml", [f"model.name={name}", "model.experimental=true"])
                    self.assertEqual(config["model"]["name"], name)

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
