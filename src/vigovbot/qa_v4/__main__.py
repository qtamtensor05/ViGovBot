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
    parser.add_argument('--oracle-evidence', action='store_true', help='Diagnostic evidence-only upper bound; run only')
    parser.add_argument("--unit-map", type=Path, help="JSON chunk ID to v4 unit ID lists")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--view", help="ID view file; defaults to main test for the small dataset, balanced otherwise")
    parser.add_argument("--split", choices=["dev", "test"])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--concurrency", type=int, default=1,
                        help="Parallel questions, or parallel conversations in free-running mode")
    parser.add_argument("--mode", choices=["reference_history", "free_running"], default="reference_history")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--judgments", type=Path)
    parser.add_argument("--lexical", action="store_true", help="Enable BLEU/ROUGE (requires evaluation extras)")
    bert_options = parser.add_mutually_exclusive_group()
    bert_options.add_argument('--bertscore', action='store_true')
    bert_options.add_argument('--bert-cache', type=Path, help='Validated per-case BERT cache bound to input fingerprint')
    parser.add_argument('--bert-model', default='xlm-roberta-large')
    parser.add_argument('--bert-device', default='cpu')
    parser.add_argument('--bert-batch-size', type=int, default=1)
    args = parser.parse_args(argv)
    args.dataset, args.view = resolve_dataset(args.dataset, args.view)
    if args.no_retrieval and args.endpoint:
        parser.error("--no-retrieval cannot be combined with --endpoint")
    if args.oracle_evidence and (args.no_retrieval or args.endpoint or args.command != 'run'):
        parser.error('--oracle-evidence requires local run and cannot combine with baseline/HTTP')
    if args.top_k < 1 or args.timeout <= 0 or args.concurrency < 1 or (args.limit is not None and args.limit < 1):
        parser.error("top-k, timeout, concurrency and limit must be positive")
    if args.command == "ask" and not args.question:
        parser.error("--question is required")
    if args.command == "score":
        if not args.predictions:
            parser.error("--predictions is required")
        from .scoring import evaluate
        cases = select_rows(read_jsonl(args.dataset / "cases.jsonl"), args.dataset, args.view, args.split, args.limit)
        predictions = list(read_jsonl(args.predictions))
        if args.unit_map:
            from .retrieval_metrics import apply_mapping
            mapping = json.loads(args.unit_map.read_text(encoding='utf-8-sig'))
            units = {u['unit_id']: u for u in read_jsonl(args.dataset / 'knowledge_units.jsonl')}
            for entry in mapping.get('chunks', {}).values():
                if entry.get('status') != 'reviewed': continue
                for uid in entry.get('unit_ids', []):
                    if uid not in units or units[uid]['source_sha256'] != entry.get('source_sha256'):
                        raise ValueError('Mapping unit/source mismatch: ' + uid)
            predictions = apply_mapping(predictions, mapping)
        modes = {p.get("history_mode") for p in predictions if p.get("history_mode")}
        if len(modes) > 1:
            raise ValueError("Cannot score mixed history modes")
        report = evaluate(cases, predictions, list(read_jsonl(args.judgments)) if args.judgments else [],
                          k=args.top_k, lexical=args.lexical, bert=args.bertscore,
                          model=args.bert_model, device=args.bert_device, batch_size=args.bert_batch_size,
                          bert_cache=json.loads(args.bert_cache.read_text(encoding='utf-8')) if args.bert_cache else None,
                          progress=True)
        from .audit import sha256
        report['provenance'] = {str(p): sha256(p) for p in
            [args.dataset / 'cases.jsonl', args.dataset / args.view, args.predictions,
             args.unit_map, args.judgments, args.bert_cache] if p}
        manifest = args.dataset / 'manifest.json'
        report['dataset_status'] = json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else None
        from .review import fingerprint
        report['benchmark'] = {'cases_sha256': sha256(args.dataset / 'cases.jsonl'),
                               'selected_ids_sha256': fingerprint(sorted(c['id'] for c in cases))}
        report['case_groups'] = {c['id']: c.get('conversation_id') or c.get('procedure_family_id')
                                 or c.get('document_id') or c['id'] for c in cases}
        report["history_mode"] = next(iter(modes), None)
        from .report import finalize_report
        report = finalize_report(report, predictions, {c["id"] for c in cases}, args.predictions)
        out = args.out or Path("outputs/qa_v4/scores.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("x", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
        print(f"[Score] Hoàn tất: {out}", flush=True)
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
        raise ValueError("During run, unit-map must map chunk IDs to lists of unit IDs; use reviewed schema at score time")
    from .adapter import existing_rag, http_rag, ollama_baseline, ollama_oracle
    oracle_contexts = None
    if args.oracle_evidence:
        ids = {q['id'] for q in queries}
        # Only evidence is forwarded. Reference text and behavior labels stay in the evaluator.
        oracle_contexts = {c['id']: c['evidence'] for c in read_jsonl(args.dataset / 'cases.jsonl') if c['id'] in ids}
        session = ollama_oracle(args.config)
    elif args.no_retrieval:
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
            from .audit import sha256
            provenance = {'mode': 'oracle' if args.oracle_evidence else ('base' if args.no_retrieval else 'rag'),
                          'inputs': {str(p): sha256(p) for p in
                              [args.dataset / 'runner_queries.jsonl', args.dataset / args.view]},
                          'config_sha256': sha256(args.config) if not args.endpoint else None}
            report = run_queries(queries, answer, args.out or Path("outputs/qa_v4/predictions.jsonl"), args.mode,
                                 oracle_contexts=oracle_contexts, provenance=provenance,
                                 concurrency=args.concurrency)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return int(report["failed"] > 0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
