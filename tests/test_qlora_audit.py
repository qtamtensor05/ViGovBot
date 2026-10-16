import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from vigovbot.training.checkpoints import validate_resume_checkpoint
from vigovbot.training.early_stopping import EarlyStoppingState, select_best_checkpoint
from vigovbot.training.evaluate import _evaluate_model
from vigovbot.training.masking import IGNORE_INDEX, encode_assistant_only
from vigovbot.training.metrics import aggregate_generation_metrics, generation_metrics, perplexity
from vigovbot.training.parameters import validate_lora_trainability
from vigovbot.training.train import _precision


class OfficialTemplateTests(unittest.TestCase):
    def test_qwen_multiturn_masks_headers_and_labels_eos(self):
        try:
            from transformers import AutoTokenizer
            tokenizer = AutoTokenizer.from_pretrained(
                "Qwen/Qwen2.5-7B-Instruct", trust_remote_code=False, local_files_only=True
            )
        except Exception as exc:
            self.skipTest(f"Official tokenizer is not in the local cache: {exc}")
        messages = [
            {"role": "user", "content": "Câu một"},
            {"role": "assistant", "content": "Trả lời một"},
            {"role": "user", "content": "Câu hai"},
            {"role": "assistant", "content": "Trả lời hai"},
        ]
        encoded = encode_assistant_only(tokenizer, messages, 2048)
        tokens = tokenizer.convert_ids_to_tokens(encoded["input_ids"])
        supervised = [index for index, label in enumerate(encoded["labels"]) if label != IGNORE_INDEX]
        for index, token in enumerate(tokens):
            if token in {"assistant", "<|im_start|>"}:
                self.assertEqual(encoded["labels"][index], IGNORE_INDEX)
        eos_positions = [index for index, token in enumerate(encoded["input_ids"])
                         if token == tokenizer.eos_token_id]
        self.assertEqual(sum(encoded["labels"][index] != IGNORE_INDEX for index in eos_positions), 2)
        self.assertTrue(supervised)

    def test_overlength_multiturn_is_rejected_not_truncated(self):
        from tests.test_qlora_local import FakeTokenizer
        messages = [
            {"role": "user", "content": "u"}, {"role": "assistant", "content": "a"},
            {"role": "user", "content": "u2"}, {"role": "assistant", "content": "final answer"},
        ]
        with self.assertRaisesRegex(ValueError, "refusing to truncate"):
            encode_assistant_only(FakeTokenizer(), messages, 8)


class ResumeAndStoppingTests(unittest.TestCase):
    def _checkpoint(self, root: Path):
        checkpoint = root / "checkpoints" / "checkpoint-20"
        checkpoint.mkdir(parents=True)
        for name in ("optimizer.pt", "scheduler.pt", "rng_state.pth", "adapter_model.safetensors"):
            (checkpoint / name).write_bytes(b"fixture")
        (checkpoint / "trainer_state.json").write_text(
            json.dumps({"global_step": 20, "stateful_callbacks": {"EarlyStoppingCallback": {"patience_counter": 1}}}),
            encoding="utf-8",
        )
        return checkpoint

    def test_resume_rejects_config_or_dataset_drift(self):
        import yaml
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory) / "run"
            checkpoint = self._checkpoint(run)
            config = {"model": {"name": "base"}}
            (run / "config.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
            (run / "environment.json").write_text(json.dumps({"dataset_hashes": {"train": "abc"}}), encoding="utf-8")
            self.assertEqual(validate_resume_checkpoint(checkpoint, config, {"train": "abc"}), checkpoint.resolve())
            with self.assertRaisesRegex(ValueError, "config differs"):
                validate_resume_checkpoint(checkpoint, {"model": {"name": "other"}}, {"train": "abc"})
            with self.assertRaisesRegex(ValueError, "Dataset hashes"):
                validate_resume_checkpoint(checkpoint, config, {"train": "changed"})

    def test_early_stopping_threshold_patience_and_best_tie(self):
        state = EarlyStoppingState(patience=2, threshold=0.01)
        self.assertFalse(state.update(1.0, 10))
        self.assertFalse(state.update(0.99, 20))  # exactly threshold is not sufficient
        self.assertTrue(state.update(0.991, 30))
        self.assertEqual((state.best_loss, state.best_step, state.stopped_step), (1.0, 10, 30))
        self.assertEqual(select_best_checkpoint([
            {"step": 10, "eval_loss": 1.0}, {"step": 20, "eval_loss": 0.9}, {"step": 30, "eval_loss": 0.9}
        ]), (20, 0.9))

    def test_transformers_early_stopping_callback_state_transition(self):
        try:
            from transformers import EarlyStoppingCallback, TrainerControl, TrainerState
        except ImportError:
            self.skipTest("Transformers is unavailable")
        callback = EarlyStoppingCallback(early_stopping_patience=2, early_stopping_threshold=0.01)
        args = SimpleNamespace(metric_for_best_model="eval_loss", greater_is_better=False)
        state = TrainerState(global_step=10, best_metric=1.0)
        control = TrainerControl()
        callback.on_evaluate(args, state, control, metrics={"eval_loss": 0.995})
        self.assertFalse(control.should_training_stop)
        callback.on_evaluate(args, state, control, metrics={"eval_loss": 0.994})
        self.assertTrue(control.should_training_stop)


class MetricAndAccountingTests(unittest.TestCase):
    def test_metric_formulas_and_corpus_aggregation(self):
        perfect = generation_metrics("xin chào", "xin chào")
        self.assertEqual(perfect["exact_match"], 1.0)
        self.assertEqual(perfect["token_f1"], 1.0)
        self.assertEqual(perfect["rouge_l"], 1.0)
        self.assertAlmostEqual(perplexity(1.0), 2.718281828459045)
        rows = [
            {"prediction": "a b", "reference": "a b", "metrics": generation_metrics("a b", "a b")},
            {"prediction": "x", "reference": "y", "metrics": generation_metrics("x", "y")},
        ]
        aggregate = aggregate_generation_metrics(rows)
        self.assertEqual(aggregate["exact_match"], 0.5)
        self.assertIn("bleu", aggregate)
        self.assertIn("chrf", aggregate)

    def test_only_lora_parameters_may_be_trainable(self):
        class Parameter:
            def __init__(self, trainable): self.requires_grad = trainable
        class Model:
            def __init__(self, bad=False): self.bad = bad
            def named_parameters(self):
                values = [("base.weight", Parameter(self.bad)), ("layer.lora_A.weight", Parameter(True))]
                return values
        self.assertEqual(validate_lora_trainability(Model()), ["layer.lora_A.weight"])
        with self.assertRaisesRegex(ValueError, "Non-LoRA"):
            validate_lora_trainability(Model(bad=True))

    def test_precision_selection_is_explicit(self):
        class Cuda:
            @staticmethod
            def is_available(): return True
            @staticmethod
            def is_bf16_supported(): return False
        torch = SimpleNamespace(cuda=Cuda(), bfloat16="bf16", float16="fp16", float32="fp32")
        config = {"quantization": {"bnb_4bit_compute_dtype": "bfloat16"}}
        self.assertEqual(_precision(torch, config), ("fp16", False, True))


class EvaluationIsolationTests(unittest.TestCase):
    def test_generation_prompt_excludes_current_reference_and_loss_is_token_weighted(self):
        try:
            import torch
        except ImportError:
            self.skipTest("PyTorch is unavailable")

        class Tokenizer:
            pad_token_id = 0
            eos_token_id = 2
            def __init__(self): self.generation_messages = []
            def apply_chat_template(self, messages, tokenize=True, add_generation_prompt=False,
                                    return_tensors=None, return_dict=False):
                ids = []
                for message in messages:
                    ids.extend([10 if message["role"] == "user" else 20])
                    ids.extend([30] * len(message["content"].split()))
                    ids.append(2)
                if add_generation_prompt:
                    self.generation_messages.append(messages)
                    ids.append(20)
                if return_tensors:
                    tensor = torch.tensor([ids])
                    return {"input_ids": tensor, "attention_mask": torch.ones_like(tensor)} if return_dict else tensor
                return ids
            def decode(self, values, skip_special_tokens=True): return "generated"

        class Model:
            device = torch.device("cpu")
            def __init__(self): self.calls = 0
            def __call__(self, **kwargs):
                self.calls += 1
                return SimpleNamespace(loss=torch.tensor(float(self.calls)))
            def generate(self, input_ids, attention_mask, **kwargs):
                return torch.cat([input_ids, torch.tensor([[99]])], dim=1)

        records = [
            {"id": "one", "messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "short"}]},
            {"id": "two", "messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "long answer here"}]},
        ]
        tokenizer, model = Tokenizer(), Model()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "predictions.jsonl"
            result = _evaluate_model(model, tokenizer, records,
                                     {"max_seq_length": 100, "max_new_tokens": 2, "temperature": 0.0},
                                     output)
            rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(rows[0]["question"], "q")
            self.assertEqual(rows[0]["generated_answer"], "generated")
            self.assertIn("metrics", rows[0])
        self.assertTrue(all(messages[-1]["role"] == "user" for messages in tokenizer.generation_messages))
        self.assertTrue(all("short" not in json.dumps(messages) and "long answer" not in json.dumps(messages)
                            for messages in tokenizer.generation_messages))
        # Target spans have 2 and 4 tokens (content plus EOS), so weighted loss=(1*2+2*4)/6.
        self.assertAlmostEqual(result["teacher_forced_token_loss"], 10 / 6)


if __name__ == "__main__":
    unittest.main()
