from __future__ import annotations

# Canonical implementation; the top-level training package is a compatibility shim.

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
    """Tokenize Qwen chat and supervise assistant content plus its EOS marker."""
    full = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=False)
    full = token_ids(full)
    if len(full) > max_length:
        raise ValueError(
            f"Conversation has {len(full)} tokens, exceeding max_seq_length={max_length}; "
            "refusing to truncate an assistant target"
        )
    labels = [IGNORE_INDEX] * len(full)
    for index, message in enumerate(messages):
        if message["role"] == "assistant":
            # The generation prompt ends immediately before assistant content, so
            # role/header tokens remain masked while content, <|im_end|> and the
            # template newline are supervised.
            start = len(token_ids(tokenizer.apply_chat_template(
                messages[:index], tokenize=True, add_generation_prompt=True
            )))
            end = len(token_ids(tokenizer.apply_chat_template(
                messages[: index + 1], tokenize=True, add_generation_prompt=False
            )))
            if not 0 <= start < end <= len(full):
                raise ValueError("Chat template produced inconsistent assistant token boundaries")
            labels[start:end] = full[start:end]
    if not any(value != IGNORE_INDEX for value in labels):
        raise ValueError("Conversation contains no assistant target tokens")
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
