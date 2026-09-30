# Nạp tokenizer Qwen
# → Nạp Qwen2.5-7B ở dạng 4-bit
# → Gắn QLoRA Adapter
# → Sinh câu trả lời từ messages

from __future__ import annotations

import gc
import time

from pathlib import Path

import torch

from peft import PeftModel

from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
)


def load_peft_model(
    base_model_name: str,
    adapter_path: str | Path,
):
    """
    Nạp Qwen2.5-7B ở dạng 4-bit,
    sau đó gắn QLoRA Adapter.
    """

    if not torch.cuda.is_available():
        raise RuntimeError(
            "Không tìm thấy GPU CUDA. "
            "Trên Colab hãy chọn "
            "Runtime > Change runtime type > GPU."
        )

    adapter_path = Path(adapter_path)

    if not adapter_path.exists():
        raise FileNotFoundError(
            f"Không tìm thấy thư mục Adapter: "
            f"{adapter_path}"
        )

    adapter_config_path = (
        adapter_path / "adapter_config.json"
    )

    if not adapter_config_path.exists():
        raise FileNotFoundError(
            "Không tìm thấy adapter_config.json: "
            f"{adapter_config_path}"
        )

    adapter_weight_files = [
        adapter_path / "adapter_model.safetensors",
        adapter_path / "adapter_model.bin",
    ]

    if not any(
        path.exists()
        for path in adapter_weight_files
    ):
        raise FileNotFoundError(
            "Không tìm thấy trọng số Adapter. "
            "Cần có adapter_model.safetensors "
            "hoặc adapter_model.bin."
        )

    if torch.cuda.is_bf16_supported():
        compute_dtype = torch.bfloat16
    else:
        compute_dtype = torch.float16

    print("===== NẠP TOKENIZER =====")
    print("Base model:", base_model_name)
    print("Adapter:", adapter_path)
    print("Compute dtype:", compute_dtype)

    tokenizer = AutoTokenizer.from_pretrained(
        base_model_name,
        use_fast=True,
    )

    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token

    tokenizer.padding_side = "left"

    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=compute_dtype,
        bnb_4bit_use_double_quant=True,
    )

    print("\n===== NẠP BASE MODEL 4-BIT =====")

    base_model = (
        AutoModelForCausalLM.from_pretrained(
            base_model_name,
            quantization_config=quantization_config,
            device_map="auto",
            torch_dtype=compute_dtype,
            low_cpu_mem_usage=True,
        )
    )

    print("\n===== GẮN QLORA ADAPTER =====")

    model = PeftModel.from_pretrained(
        base_model,
        str(adapter_path),
        is_trainable=False,
    )

    model.eval()
    model.config.use_cache = True

    input_device = (
        model
        .get_input_embeddings()
        .weight
        .device
    )

    print("\nĐã nạp Qwen Base + QLoRA Adapter.")
    print("Input device:", input_device)

    return model, tokenizer


def peft_answer(
    model,
    tokenizer,
    messages: list[dict],
    max_new_tokens: int = 512,
    repetition_penalty: float = 1.05,
):
    """
    Nhận messages đã có ngữ cảnh RAG
    và sinh câu trả lời.
    """

    if not isinstance(messages, list):
        raise TypeError(
            "messages phải là danh sách."
        )

    if not messages:
        raise ValueError(
            "messages không được rỗng."
        )

    if max_new_tokens <= 0:
        raise ValueError(
            "max_new_tokens phải lớn hơn 0."
        )

    input_device = (
        model
        .get_input_embeddings()
        .weight
        .device
    )

    inputs = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    )

    inputs = {
        key: value.to(input_device)
        for key, value in inputs.items()
    }

    input_token_count = (
        inputs["input_ids"].shape[1]
    )

    torch.cuda.synchronize()

    started_at = time.perf_counter()

    with torch.inference_mode():
        generated_ids = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            repetition_penalty=repetition_penalty,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
            use_cache=True,
        )

    torch.cuda.synchronize()

    generation_time = (
        time.perf_counter() - started_at
    )

    answer_token_ids = generated_ids[
        0,
        input_token_count:
    ]

    answer = tokenizer.decode(
        answer_token_ids,
        skip_special_tokens=True,
    ).strip()

    if not answer:
        raise RuntimeError(
            "Mô hình sinh câu trả lời rỗng."
        )

    return answer, generation_time


def unload_peft_model(
    model=None,
    tokenizer=None,
):
    """
    Hỗ trợ dọn bộ nhớ sau khi inference.
    Sau khi gọi hàm, phía notebook vẫn cần
    gán model = None và tokenizer = None.
    """

    if model is not None:
        del model

    if tokenizer is not None:
        del tokenizer

    gc.collect()

    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()

    print("Đã thực hiện dọn bộ nhớ GPU.")