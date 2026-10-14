from __future__ import annotations

import threading

_LOCK = threading.Lock()
_CACHE = {}


def load_model(base_model: str, adapter_path: str | None = None, quantized: bool = True):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    quantization = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                     bnb_4bit_use_double_quant=True,
                                     bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16) if quantized else None
    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(base_model, quantization_config=quantization,
                                                 device_map="auto", trust_remote_code=False)
    if adapter_path:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, adapter_path, is_trainable=False)
    model.eval()
    return model, tokenizer


def local_transformers_answer(messages, settings):
    import time
    import torch
    key = (settings["model"], settings.get("adapter_path"), bool(settings.get("load_in_4bit", True)))
    with _LOCK:
        if key not in _CACHE:
            if _CACHE and not settings.get("allow_multiple_models", False):
                _CACHE.clear()
                if torch.cuda.is_available(): torch.cuda.empty_cache()
            _CACHE[key] = load_model(*key[:2], quantized=key[2])
        model, tokenizer = _CACHE[key]
        encoded = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True, return_tensors="pt").to(model.device)
        started = time.perf_counter()
        with torch.inference_mode():
            output = model.generate(encoded, max_new_tokens=settings["num_predict"], temperature=settings.get("temperature", 0.0),
                                    do_sample=settings.get("temperature", 0.0) > 0)
        answer = tokenizer.decode(output[0, encoded.shape[-1]:], skip_special_tokens=True).strip()
        return answer, {"provider": "local_transformers", "adapter_path": settings.get("adapter_path")}, time.perf_counter() - started
