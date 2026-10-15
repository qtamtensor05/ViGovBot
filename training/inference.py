from __future__ import annotations

import threading

_LOCK = threading.RLock()
_CACHE = {}


def release_local_transformers_models():
    """Release cached local models before handing a constrained GPU to another backend."""
    import gc
    import torch

    with _LOCK:
        _CACHE.clear()
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


def load_model(base_model: str, adapter_path: str | None = None, quantized: bool = True):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    if quantized and not torch.cuda.is_available():
        raise RuntimeError("4-bit baseline/PEFT inference requires CUDA; pass quantized=False only for explicit CPU tests")
    quantization = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                     bnb_4bit_use_double_quant=True,
                                     bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16) if quantized else None
    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(base_model, quantization_config=quantization,
                                                 device_map="auto", trust_remote_code=False)
    if adapter_path:
        from peft import PeftConfig, PeftModel
        adapter_config = PeftConfig.from_pretrained(adapter_path)
        configured_base = getattr(adapter_config, "base_model_name_or_path", None)
        if configured_base and configured_base != base_model:
            raise ValueError(f"Adapter expects base model {configured_base}, not {base_model}")
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
                release_local_transformers_models()
            _CACHE[key] = load_model(*key[:2], quantized=key[2])
        model, tokenizer = _CACHE[key]
        encoded = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True,
                                                return_tensors="pt", return_dict=True)
        if hasattr(encoded, "keys"):
            model_inputs = {name: value.to(model.device) for name, value in encoded.items()}
            prompt_length = model_inputs["input_ids"].shape[-1]
        else:
            model_inputs = {"input_ids": encoded.to(model.device)}
            prompt_length = model_inputs["input_ids"].shape[-1]
        started = time.perf_counter()
        with torch.inference_mode():
            output = model.generate(**model_inputs, max_new_tokens=settings["num_predict"], temperature=settings.get("temperature", 0.0),
                                    do_sample=settings.get("temperature", 0.0) > 0)
        answer = tokenizer.decode(output[0, prompt_length:], skip_special_tokens=True).strip()
        return answer, {"provider": "local_transformers", "adapter_path": settings.get("adapter_path")}, time.perf_counter() - started


def local_transformers_batch_answer(messages_batch, settings):
    """Greedy batched generation for independent conversations, preserving order."""
    import time
    import torch
    key = (settings["model"], settings.get("adapter_path"), bool(settings.get("load_in_4bit", True)))
    with _LOCK:
        if key not in _CACHE:
            if _CACHE and not settings.get("allow_multiple_models", False):
                release_local_transformers_models()
            _CACHE[key] = load_model(*key[:2], quantized=key[2])
        model, tokenizer = _CACHE[key]
    tokenizer.pad_token = tokenizer.pad_token or tokenizer.eos_token
    tokenizer.padding_side = "left"
    encoded = tokenizer.apply_chat_template(
        messages_batch, tokenize=True, add_generation_prompt=True,
        padding=True, return_tensors="pt", return_dict=True,
    )
    model_inputs = {name: value.to(model.device) for name, value in encoded.items()}
    prompt_width = model_inputs["input_ids"].shape[-1]
    started = time.perf_counter()
    with torch.inference_mode():
        output = model.generate(
            **model_inputs, max_new_tokens=settings["num_predict"],
            temperature=settings.get("temperature", 0.0),
            do_sample=settings.get("temperature", 0.0) > 0,
        )
    answers = tokenizer.batch_decode(output[:, prompt_width:], skip_special_tokens=True)
    elapsed = time.perf_counter() - started
    return [answer.strip() for answer in answers], {
        "provider": "local_transformers", "adapter_path": settings.get("adapter_path"),
        "batch_size": len(messages_batch),
    }, elapsed
