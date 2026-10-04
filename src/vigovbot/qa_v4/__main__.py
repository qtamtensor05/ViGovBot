import argparse
import json
from pathlib import Path

from vigovbot.console import configure_console
from .io import read_jsonl


def resolve_dataset(dataset, view=None):
    """Resolve built-in aliases while retaining support for custom dataset paths."""
    aliases = {
        "rag_v4_small": Path("Data/qa_test_v4/rag_tthc_balanced_small"),
        "rag_tthc_balanced_small": Path("Data/qa_test_v4/rag_tthc_balanced_small"),
        "test_rag_three_1500": Path("Data/qa_test_v4/rag_tthc_three_1500"),
        "rag_tthc_three_1500": Path("Data/qa_test_v4/rag_tthc_three_1500"),
        "rag_tthc_v4_1": Path("Data/qa_test_v4/rag_tthc_v4_1"),
    }
    dataset = aliases.get(str(dataset), Path(dataset))
    if view is None:
        candidates = ("views_main_test.json", "views_single_1500.json", "views_balanced.json")
        view = next((name for name in candidates if (dataset / name).is_file()), "views_balanced.json")
    return dataset, view


def select_rows(rows, dataset, view, split, limit=None):
    ids = set(json.loads((dataset / view).read_text(encoding="utf-8-sig"))) if view else None
    selected = [r for r in rows if (ids is None or r["id"] in ids) and (not split or r["split"] == split)]
    if not selected:
        raise ValueError("No cases selected")
    return selected[:limit] if limit else selected


def main(argv=None):
    configure_console()
    parser = argparse.ArgumentParser(description="Send QA v4 to the existing RAG and evaluate responses")
    parser.add_argument("command", choices=["ask", "chat", "run", "score"])
    parser.add_argument("--dataset", type=Path, default=Path("Data/qa_test_v4/rag_tthc_v4_1"),
                        help="Dataset directory or alias: rag_v4_small, rag_tthc_three_1500, rag_tthc_v4_1")
    parser.add_argument("--question")
    connection = parser.add_mutually_exclusive_group()
    connection.add_argument("--config", default="rag_config.yaml")
    connection.add_argument("--endpoint", help="Existing RAG HTTP endpoint")
    parser.add_argument("--no-retrieval", action="store_true",
                        help="Run the configured Ollama model directly without corpus/FAISS")
    parser.add_argument("--unit-map", type=Path, help="JSON chunk ID to v4 unit ID lists")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--view", help="ID view file; defaults to main test for the small dataset, balanced otherwise")
    parser.add_argument("--split", choices=["dev", "test"])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--mode", choices=["reference_history", "free_running"], default="reference_history")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--judgments", type=Path)
    parser.add_argument("--lexical", action="store_true", help="Enable BLEU/ROUGE (requires evaluation extras)")
    args = parser.parse_args(argv)
    args.dataset, args.view = resolve_dataset(args.dataset, args.view)
    if args.no_retrieval and args.endpoint:
        parser.error("--no-retrieval cannot be combined with --endpoint")
    if args.top_k < 1 or args.timeout <= 0 or (args.limit is not None and args.limit < 1):
        parser.error("top-k, timeout and limit must be positive")
    if args.command == "ask" and not args.question:
        parser.error("--question is required")
    if args.command == "score":
        if not args.predictions:
            parser.error("--predictions is required")
        from .scoring import evaluate
        cases = select_rows(read_jsonl(args.dataset / "cases.jsonl"), args.dataset, args.view, args.split, args.limit)
        predictions = list(read_jsonl(args.predictions))
        modes = {p.get("history_mode") for p in predictions if p.get("history_mode")}
        if len(modes) > 1:
            raise ValueError("Cannot score mixed history modes")
        report = evaluate(cases, predictions, list(read_jsonl(args.judgments)) if args.judgments else [],
                          k=args.top_k, lexical=args.lexical)
        report["history_mode"] = next(iter(modes), None)
        from .report import finalize_report
        report = finalize_report(report, predictions, {c["id"] for c in cases}, args.predictions)
        out = args.out or Path("outputs/qa_v4/scores.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("x", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
        print(json.dumps(report["coverage"], ensure_ascii=False))
        return 0
    queries = None
    if args.command == "run":
        from vigovbot.evaluation.multiturn import load_queries, validate_sequence
        queries = load_queries(args.dataset / "runner_queries.jsonl",
                               args.dataset / args.view if args.view else None, args.split)
        if args.limit:
            queries = queries[:args.limit]
        if args.mode == "free_running":
            validate_sequence(queries)
        if (args.out or Path("outputs/qa_v4/predictions.jsonl")).exists():
            raise FileExistsError("Output already exists; choose a new output path")
    mapping = json.loads(args.unit_map.read_text(encoding="utf-8-sig")) if args.unit_map else None
    if mapping is not None and (not isinstance(mapping, dict) or any(
            not isinstance(v, list) or any(not isinstance(uid, str) for uid in v) for v in mapping.values())):
        raise ValueError("unit-map must map chunk IDs to lists of unit IDs")
    from .adapter import existing_rag, http_rag, ollama_baseline
    if args.no_retrieval:
        session = ollama_baseline(args.config)
    elif args.endpoint:
        session = http_rag(args.endpoint, args.timeout, mapping)
    else:
        session = existing_rag(args.config, mapping)
    with session as answer:
        if args.command == "ask":
            print(json.dumps(answer(args.question), ensure_ascii=False, indent=2))
        elif args.command == "chat":
            history = []
            print("Nhập câu hỏi; /reset xóa lịch sử; /exit thoát.")
            while True:
                try:
                    question = input("Bạn: ").strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if question == "/exit":
                    break
                if question == "/reset":
                    history = []
                    continue
                if not question:
                    continue
                try:
                    result = answer(question, history)
                except Exception as exc:
                    print(f"Lỗi: {exc}")
                    continue
                print(f"RAG ({result['action']}): {result['answer']}")
                print("Nguồn: " + json.dumps(result["citations"], ensure_ascii=False))
                history += [{"role": "user", "content": question}, {"role": "assistant", "content": result["answer"]}]
        else:
            from .runner import run_queries
            report = run_queries(queries, answer, args.out or Path("outputs/qa_v4/predictions.jsonl"), args.mode)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return int(report["failed"] > 0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
