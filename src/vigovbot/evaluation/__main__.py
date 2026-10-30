"""Single Golden evaluation workflow."""
import argparse
import json
from pathlib import Path
from vigovbot.console import configure_console
from .workflow import dispatch


def main(argv=None):
    configure_console()
    parser = argparse.ArgumentParser(description="Golden: validate -> run -> score -> report")
    parser.add_argument("command", choices=["validate", "run", "score", "report", "evaluate", "compare"])
    parser.add_argument("--dataset", type=Path, default=Path("Data/dataset_v3"))
    parser.add_argument("--split", choices=["train", "val", "test"], default="test")
    parser.add_argument("--profile", choices=["base", "rag", "qlora"])
    parser.add_argument("--run-id")
    parser.add_argument("--output-root", type=Path, default=Path("outputs/evaluation"))
    parser.add_argument("--scope", choices=["full", "retrieval"], default="full")
    parser.add_argument("--endpoint", default="http://localhost:8001/api/chat")
    parser.add_argument("--config", type=Path, default=Path("configs/rag/inference.yaml"))
    parser.add_argument("--model-metadata", type=Path,
                        help="JSON provenance for fine-tuned model/adapter revisions")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--complete-trace", action="store_true")
    parser.add_argument("--judge-model")
    parser.add_argument("--judge-endpoint", default="http://localhost:11434")
    parser.add_argument("--bertscore", action="store_true")
    parser.add_argument("--extended-metrics", action="store_true")
    parser.add_argument("--rescore", action="store_true",
                        help="Rebuild derived score artifacts from existing predictions without inference")
    parser.add_argument("--bert-model", default="xlm-roberta-large")
    parser.add_argument("--bert-device", choices=["cpu", "cuda"], default="cpu")
    parser.add_argument("--bert-batch-size", type=int, default=16)
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--ks", type=int, nargs="+", default=[1, 3, 5, 10])
    parser.add_argument("--other-run-id")
    args = parser.parse_args(argv)
    if args.command != "validate" and not args.run_id:
        parser.error("--run-id is required")
    if args.command in {"run", "evaluate"} and not args.profile:
        parser.error("--profile is required")
    if args.rescore and args.command not in {"score", "evaluate"}:
        parser.error("--rescore is only valid with score or evaluate")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    if args.timeout <= 0 or args.top_k < 1 or args.bert_batch_size < 1 or any(k < 1 for k in args.ks):
        parser.error("timeout, top-k, ks and batch size must be positive")
    try:
        report = dispatch(args)
    except (ValueError, FileNotFoundError, FileExistsError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return int(report.get("execution_status", {}).get("error", 0) > 0)


if __name__ == "__main__":
    raise SystemExit(main())
