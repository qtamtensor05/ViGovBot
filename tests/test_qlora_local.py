import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from training.checkpoints import checkpoint_run_dir, validate_resume_checkpoint
from training.config import load_config
from training.data import analyze_splits, read_jsonl, validate_conversation
from training.early_stopping import EarlyStoppingState, select_best_checkpoint
from training.masking import IGNORE_INDEX, encode_assistant_only
from training.metrics import generation_metrics, normalize_vietnamese, perplexity
from training.parameters import count_parameters


class FakeTokenizer:
    """Deterministic fixture tokenizer; not evidence of Qwen tokenizer compatibility."""
    pad_token_id = 0
    eos_token_id = 2
    def apply_chat_template(self, messages, tokenize=True, add_generation_prompt=False, **kwargs):
        values = []
        for message in messages:
            values.extend([10 if message["role"] == "user" else 20])
            values.extend(range(30, 30 + len(message["content"].split())))
            values.append(2)
        if add_generation_prompt: values.append(20)
        return values


def record(identifier, question="Phí bao nhiêu?", answer="Lệ phí 10.000 đồng."):
    return {"id": identifier, "messages": [{"role": "user", "content": question},
                                               {"role": "assistant", "content": answer}]}


class DataTests(unittest.TestCase):
    def test_jsonl_and_multiturn_validation(self):
        item = {"id": "x", "messages": [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"},
                                               {"role": "user", "content": "c"}, {"role": "assistant", "content": "d"}]}
        validate_conversation(item)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.jsonl"
            path.write_text(json.dumps(item, ensure_ascii=False) + "\n", encoding="utf-8")
            self.assertEqual(read_jsonl(path)[0]["id"], "x")

    def test_split_isolation_and_overlap_categories(self):
        report = analyze_splits({"train": [record("a")], "validation": [record("b")], "test": [record("c", "Khác", "Khác")]})
        self.assertEqual(len(report["overlaps"]["train__validation"]["conversation_exact"]), 1)
        with self.assertRaisesRegex(ValueError, "appears in both"):
            analyze_splits({"train": [record("same")], "test": [record("same", "x", "y")]})


class MaskingTests(unittest.TestCase):
    def test_assistant_only_multiturn_mask(self):
        messages = [{"role": "user", "content": "mot hai"}, {"role": "assistant", "content": "ba bon"},
                    {"role": "user", "content": "nam"}, {"role": "assistant", "content": "sau"}]
        encoded = encode_assistant_only(FakeTokenizer(), messages, 100)
        self.assertEqual(len(encoded["labels"]), len(encoded["input_ids"]))
        self.assertTrue(any(value == IGNORE_INDEX for value in encoded["labels"]))
        self.assertTrue(any(value != IGNORE_INDEX for value in encoded["labels"]))
        # Fake template: assistant header is one token and must remain masked;
        # assistant content and EOS are supervised.
        self.assertEqual(encoded["labels"][4], IGNORE_INDEX)
        self.assertNotEqual(encoded["labels"][5], IGNORE_INDEX)
        self.assertEqual(encoded["input_ids"][7], FakeTokenizer.eos_token_id)
        self.assertEqual(encoded["labels"][7], FakeTokenizer.eos_token_id)

    def test_truncation_cannot_remove_all_targets(self):
        with self.assertRaisesRegex(ValueError, "refusing to truncate"):
            encode_assistant_only(FakeTokenizer(), record("x")["messages"], 3)

    def test_transformers_mapping_chat_template_output(self):
        class MappingTokenizer(FakeTokenizer):
            def apply_chat_template(self, *args, **kwargs):
                return {"input_ids": [super().apply_chat_template(*args, **kwargs)], "attention_mask": [[1]]}
        encoded = encode_assistant_only(MappingTokenizer(), record("x")["messages"], 100)
        self.assertGreater(len(encoded["input_ids"]), 2)
        self.assertTrue(any(value != IGNORE_INDEX for value in encoded["labels"]))


class LogicTests(unittest.TestCase):
    def test_config_and_early_stopping(self):
        for path in ("configs/base.yaml", "configs/local.yaml", "configs/smoke.yaml", "configs/gpu.yaml"):
            config = load_config(path)
            self.assertEqual(config["model"]["name"], "Qwen/Qwen2.5-7B-Instruct")
        state = EarlyStoppingState(2, .01)
        self.assertFalse(state.update(1.0, 1)); self.assertFalse(state.update(.995, 2)); self.assertTrue(state.update(.994, 3))
        self.assertEqual(select_best_checkpoint([{"step": 1, "eval_loss": 2}, {"step": 2, "eval_loss": 1}]), (2, 1.0))

    def test_metrics(self):
        values = generation_metrics("Lệ phí 10.000 đồng", "lệ phí 10.000 đồng!")
        self.assertEqual(values["normalized_exact_match"], 1.0)
        self.assertAlmostEqual(perplexity(0), 1)
        self.assertEqual(normalize_vietnamese("ĐỒNG"), "đồng")

    def test_parameter_counting(self):
        class Parameter:
            def __init__(self, n, trainable): self.n, self.requires_grad = n, trainable
            def numel(self): return self.n
        class Model:
            def parameters(self): return [Parameter(10, False), Parameter(2, True)]
        result = count_parameters(Model())
        self.assertEqual(result["trainable_lora_parameters"], 2)
        self.assertEqual(result["frozen_parameters"], 10)

    def test_corrupt_checkpoint_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "Corrupted"):
                validate_resume_checkpoint(directory)

    def test_complete_checkpoint_and_run_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory) / "run"
            checkpoint = run / "checkpoints" / "checkpoint-100"
            checkpoint.mkdir(parents=True)
            for name in ("optimizer.pt", "scheduler.pt", "rng_state.pth", "adapter_model.safetensors"):
                (checkpoint / name).write_bytes(b"fixture")
            (checkpoint / "trainer_state.json").write_text(
                json.dumps({"global_step": 100, "stateful_callbacks": {"EarlyStoppingCallback": {"patience_counter": 1}}}),
                encoding="utf-8",
            )
            self.assertEqual(validate_resume_checkpoint(checkpoint), checkpoint.resolve())
            self.assertEqual(checkpoint_run_dir(checkpoint), run.resolve())
            (checkpoint / "rng_state.pth").unlink()
            with self.assertRaisesRegex(ValueError, "rng_state"):
                validate_resume_checkpoint(checkpoint)

    def test_inference_adapter_loading_interface(self):
        from training.inference import load_model
        base = MagicMock()
        tokenizer = MagicMock()
        modules = {
            "torch": MagicMock(),
            "transformers": MagicMock(),
            "peft": MagicMock(),
        }
        modules["torch"].cuda.is_bf16_supported.return_value = False
        modules["torch"].cuda.is_available.return_value = True
        modules["transformers"].AutoTokenizer.from_pretrained.return_value = tokenizer
        modules["transformers"].AutoModelForCausalLM.from_pretrained.return_value = base
        modules["peft"].PeftConfig.from_pretrained.return_value.base_model_name_or_path = "Qwen/Qwen2.5-7B-Instruct"
        wrapped = modules["peft"].PeftModel.from_pretrained.return_value
        with patch.dict("sys.modules", modules):
            model, loaded_tokenizer = load_model("Qwen/Qwen2.5-7B-Instruct", "relative/adapter")
        modules["peft"].PeftModel.from_pretrained.assert_called_once_with(base, "relative/adapter", is_trainable=False)
        self.assertIs(model, wrapped)
        self.assertIs(loaded_tokenizer, tokenizer)


if __name__ == "__main__": unittest.main()
