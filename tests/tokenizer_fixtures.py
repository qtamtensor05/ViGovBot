"""Deterministic character fixtures for budget tests, not model tokenization evidence."""


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
