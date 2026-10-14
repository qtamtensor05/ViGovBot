from __future__ import annotations

IGNORE_INDEX = -100


def token_ids(value) -> list[int]:
    if isinstance(value, dict) or hasattr(value, "keys"):
        value = value["input_ids"]
    if hasattr(value, "tolist"):
        value = value.tolist()
    if value and isinstance(value[0], list):
        if len(value) != 1:
            raise ValueError("Expected one tokenized conversation")
        value = value[0]
    return list(value)


def encode_assistant_only(tokenizer, messages: list[dict], max_length: int) -> dict[str, list[int]]:
    """Tokenize Qwen chat and supervise only assistant message spans."""
    full = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=False)
    full = token_ids(full)
    labels = [IGNORE_INDEX] * len(full)
    previous = 0
    for index, message in enumerate(messages):
        prefix = tokenizer.apply_chat_template(messages[: index + 1], tokenize=True, add_generation_prompt=False)
        current = len(token_ids(prefix))
        if message["role"] == "assistant":
            labels[previous:current] = full[previous:current]
        previous = current
    if len(full) > max_length:
        full = full[:max_length]
        labels = labels[:max_length]
    if not any(value != IGNORE_INDEX for value in labels):
        raise ValueError("Truncation removed every assistant target token; increase max_seq_length or filter the example")
    return {"input_ids": full, "attention_mask": [1] * len(full), "labels": labels}


def padding_collator(tokenizer):
    def collate(features):
        import torch
        width = max(len(item["input_ids"]) for item in features)
        pad_id = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id
        result = {"input_ids": [], "attention_mask": [], "labels": []}
        for item in features:
            pad = width - len(item["input_ids"])
            result["input_ids"].append(item["input_ids"] + [pad_id] * pad)
            result["attention_mask"].append(item["attention_mask"] + [0] * pad)
            result["labels"].append(item["labels"] + [IGNORE_INDEX] * pad)
        return {key: torch.tensor(value, dtype=torch.long) for key, value in result.items()}
    return collate
