from __future__ import annotations

import argparse
import json
from pathlib import Path

from vigovbot.training.artifacts import write_json
from vigovbot.training.config import load_config, resolve_path
from vigovbot.training.data import analyze_splits, dataset_paths, read_jsonl, sha256_file
from vigovbot.training.masking import token_ids


def _percentile(values: list[int], percentage: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[round((len(ordered) - 1) * percentage)]


def token_statistics(records: list[dict], tokenizer) -> dict:
    lengths = [len(token_ids(tokenizer.apply_chat_template(record["messages"], tokenize=True,
                                                            add_generation_prompt=False))) for record in records]
    return {"p50": _percentile(lengths, .50), "p90": _percentile(lengths, .90),
            "p95": _percentile(lengths, .95), "p99": _percentile(lengths, .99), "max": max(lengths, default=None)}


def validate(config: dict, with_tokenizer: bool = False, local_files_only: bool = False) -> dict:
    paths = dataset_paths(config)
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing dataset files: {missing}")
    splits = {name: read_jsonl(path) for name, path in paths.items()}
    report = analyze_splits(splits, float(config["data"].get("near_duplicate_threshold", .92)))
    for name, path in paths.items():
        report["splits"][name]["path"] = str(path)
        report["splits"][name]["sha256"] = sha256_file(path)
    report["token_statistics"] = {"status": "not_run", "reason": "Use --with-tokenizer; this may download tokenizer files."}
    if with_tokenizer:
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(config["model"]["name"], trust_remote_code=False,
                                                  local_files_only=local_files_only)
        report["token_statistics"] = {name: token_statistics(records, tokenizer) for name, records in splits.items()}
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate SFT JSONL and report split leakage")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output")
    parser.add_argument("--with-tokenizer", action="store_true",
                        help="Load the official tokenizer to calculate chat-template token percentiles")
    parser.add_argument("--local-files-only", action="store_true", help="Never contact the Hugging Face Hub")
    parser.add_argument("--set", action="append", default=[])
    args = parser.parse_args()
    config = load_config(args.config, args.set)
    report = validate(config, args.with_tokenizer, args.local_files_only)
    output = Path(args.output).resolve() if args.output else resolve_path(config, "outputs/qlora/dataset_report.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(output, report)
    print(json.dumps({"status": "valid", "report": str(output),
                      "records": {key: value["records"] for key, value in report["splits"].items()}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
