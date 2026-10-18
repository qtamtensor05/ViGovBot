"""Deterministic fixtures for budget and masking tests, not model compatibility evidence."""


class FakeTokenizer:
    """Deterministic masking fixture; not evidence of real-model compatibility."""
    pad_token_id = 0
    eos_token_id = 2

    def apply_chat_template(self, messages, tokenize=True, add_generation_prompt=False, **kwargs):
        values = []
        for message in messages:
            values.extend([10 if message["role"] == "user" else 20])
            values.extend(range(30, 30 + len(message["content"].split())))
            values.append(2)
        if add_generation_prompt:
            values.append(20)
        return values


class MappingTokenizer(FakeTokenizer):
    def apply_chat_template(self, *args, **kwargs):
        return {"input_ids": [super().apply_chat_template(*args, **kwargs)], "attention_mask": [[1]]}


class CharacterTokenizer:
    def __init__(self, *, overhead=0, serialize_messages=False):
        self.overhead = overhead
        self.serialize_messages = serialize_messages

    def encode(self, text, **kwargs):
        return list(map(ord, text))

    def decode(self, ids):
        return "".join(map(chr, ids))

    def apply_chat_template(self, messages, **kwargs):
        text = str(messages) if self.serialize_messages else "".join(m["content"] for m in messages)
        return self.encode(text) + [0] * self.overhead
