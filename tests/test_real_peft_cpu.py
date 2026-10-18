"""Offline CPU integration with real Transformers/PEFT; not a QLoRA GPU test."""
from tests.dependencies import skip_missing_dependency  # noqa: F401


import tempfile
import unittest


class RealPeftCpuTests(unittest.TestCase):
    def test_real_tokenizer_lora_backward_save_reload(self):
        try:
            import torch
            from tokenizers import Tokenizer
            from tokenizers.models import WordLevel
            from tokenizers.pre_tokenizers import Whitespace
            from transformers import GPT2Config, GPT2LMHeadModel, PreTrainedTokenizerFast
            from peft import LoraConfig, PeftModel, get_peft_model
        except ImportError as exc:
            self.skipTest(f"Optional real CPU integration dependencies missing: {exc}")
        from vigovbot.training.masking import encode_assistant_only, padding_collator
        from vigovbot.training.parameters import validate_lora_trainability

        torch.manual_seed(42)
        vocab = {word: i for i, word in enumerate(["[UNK]", "[PAD]", "[EOS]", "user", "assistant", "hello", "answer"])}
        backend = Tokenizer(WordLevel(vocab, unk_token="[UNK]"))
        backend.pre_tokenizer = Whitespace()
        tokenizer = PreTrainedTokenizerFast(tokenizer_object=backend, unk_token="[UNK]", pad_token="[PAD]", eos_token="[EOS]")
        tokenizer.chat_template = "{% for m in messages %}{{ m['role'] + ' ' + m['content'] + ' ' + eos_token + ' ' }}{% endfor %}{% if add_generation_prompt %}{{ 'assistant ' }}{% endif %}"
        messages = [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "answer"}]
        feature = encode_assistant_only(tokenizer, messages, 64)
        self.assertEqual(tokenizer.decode([i for i in feature["labels"] if i != -100]), "answer [EOS]", "Only assistant answer/EOS should be supervised")
        config = GPT2Config(vocab_size=len(vocab), n_positions=64, n_embd=16, n_layer=1, n_head=2,
                            pad_token_id=1, eos_token_id=2, resid_pdrop=0, embd_pdrop=0, attn_pdrop=0)
        base = GPT2LMHeadModel(config)
        original_base = {key: value.detach().clone() for key, value in base.state_dict().items()}
        model = get_peft_model(base, LoraConfig(r=2, lora_alpha=4, target_modules=["c_attn"],
                                               fan_in_fan_out=True, task_type="CAUSAL_LM"))
        self.assertTrue(validate_lora_trainability(model), "LoRA must expose trainable adapter parameters")
        batch = padding_collator(tokenizer)([feature])
        loss = model(**batch).loss
        self.assertTrue(torch.isfinite(loss), "Real forward loss must be finite")
        loss.backward()
        self.assertTrue(any(p.grad is not None and p.grad.abs().sum() > 0 for n, p in model.named_parameters() if "lora_" in n), "Backward must reach LoRA weights")
        optimizer = torch.optim.SGD([p for p in model.parameters() if p.requires_grad], lr=0.1)
        optimizer.step()
        model.eval()
        with torch.no_grad():
            expected = model(input_ids=batch["input_ids"]).logits
        with tempfile.TemporaryDirectory() as work:
            model.save_pretrained(work)
            tokenizer.save_pretrained(work)
            fresh_base = GPT2LMHeadModel(config)
            fresh_base.load_state_dict(original_base)
            restored = PeftModel.from_pretrained(fresh_base, work).eval()
            restored_tokenizer = PreTrainedTokenizerFast.from_pretrained(work, local_files_only=True)
            self.assertEqual(restored_tokenizer.apply_chat_template(messages), feature["input_ids"], "Tokenizer serialization must preserve chat token IDs")
            with torch.no_grad():
                actual = restored(input_ids=batch["input_ids"]).logits
            torch.testing.assert_close(actual, expected, rtol=1e-5, atol=1e-6, msg="Reloaded adapter logits must match trained adapter")
