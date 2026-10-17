"""Dataset serialization only; blank lines are skipped, input is never repaired."""

from vigovbot.utils.jsonl import iter_jsonl


def read_jsonl(path):
    for _, value in iter_jsonl(path, blank_lines="skip"):
        yield value
