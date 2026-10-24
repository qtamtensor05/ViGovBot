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
        if str(dataset).endswith("rag_tthc_three_1500"):
            default_view = "views_single_1500.json"
        else:
            default_view = "views_balanced.json"
        candidates = ("views_main_test.json", "views_single_1500.json", "views_balanced.json")
        view = next((name for name in candidates if (dataset / name).is_file()), None)
        if view is None and str(dataset).endswith(("rag_tthc_three_1500", "rag_tthc_v4_1")):
            view = default_view
    return dataset, view


def dataset_file(dataset, kind, split=None):
    """Resolve both QA v4 and unified-v2 package layouts without copying gold."""
    direct = dataset / ("cases.jsonl" if kind == "cases" else "runner_queries.jsonl")
    if direct.is_file():
        return direct
    package_split = split or "test"
    name = f"{package_split}.jsonl" if kind == "cases" else f"{package_split}_queries.jsonl"
    for packaged in (dataset / "data" / "rag" / name, dataset / "data" / name):
        if packaged.is_file():
            return packaged
    raise FileNotFoundError(f"Cannot find {kind} for split {package_split!r} in {dataset}")


def select_rows(rows, dataset, view, split, limit=None):
    ids = set(json.loads((dataset / view).read_text(encoding="utf-8-sig"))) if view else None
    selected = [r for r in rows if (ids is None or r["id"] in ids) and (not split or r["split"] == split)]
    if not selected:
        raise ValueError("No cases selected")
    return selected[:limit] if limit else selected


def main(argv=None):
    configure_console()
    parser = argparse.ArgumentParser(description="Run unified ViGovBot evaluation workflows")
    parser.add_argument("command", choices=["ask", "chat", "run", "score", "test", "retrieval-run", "retrieval-score", "run-v2", "noise-v2", "score-noise-v2", "export-v2", "score-v2-offline", "judge-v2", "pairwise-v2", "complete-v2"])
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--complete-trace", action="store_true")
    parser.add_argument("--extended-metrics", action="store_true", help="Offline Vietnamese exact METEOR and sentence embedding cosine")
    parser.add_argument("--other-predictions", type=Path)
    parser.add_argument("--judge-model", help="Explicit installed Ollama judge model name")
    parser.add_argument("--judge-endpoint", default="http://localhost:11434")
    parser.add_argument("--dataset", type=Path, default=Path("Data/qa_test_v4/rag_tthc_v4_1"),
                        help="Dataset directory or alias: rag_v4_small, rag_tthc_three_1500, rag_tthc_v4_1")
    parser.add_argument("--question")
    parser.add_argument("--run-id", help="Completed QLoRA run ID for test, or immutable run ID for export-v2")
    parser.add_argument("--golden-dir", type=Path, default=Path("Data/golden_dataset"),
                        help="Golden train/val/test directory for offline export-v2")
    parser.add_argument("--architecture", choices=["base", "finetuned", "rag_base", "rag_finetuned"],
                        help="Model architecture recorded by export-v2")
    parser.add_argument("--model-name", help="Model/checkpoint label recorded by export-v2")
    parser.add_argument("--model-id", help="Web model ID for run-v2; defaults from architecture")
    parser.add_argument("--model-config", type=Path,
                        help="Optional JSON provenance/config object for export-v2; never executes the model")
    parser.add_argument("--allow-partial", action="store_true",
                        help="Allow cached predictions to cover only part of the selected Golden split")
    connection = parser.add_mutually_exclusive_group()
    connection.add_argument("--config", default="configs/rag/inference.yaml")
    connection.add_argument("--endpoint", help="Existing RAG HTTP endpoint")
    connection.add_argument("--qlora-run-dir", type=Path,
                            help="Evaluate best_adapter from a completed QLoRA run without retrieval")
    parser.add_argument("--no-retrieval", action="store_true",
                        help="Run the configured Ollama model directly without corpus/FAISS")
    parser.add_argument('--oracle-evidence', action='store_true', help='Diagnostic evidence-only upper bound; run only')
    parser.add_argument("--unit-map", type=Path, help="JSON chunk ID to v4 unit ID lists")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--ks", type=int, nargs="+", default=[1, 3, 5],
                        help="Ranks reported by retrieval-score")
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--view", help="ID view file; defaults to main test for the small dataset, balanced otherwise")
    parser.add_argument("--split", choices=["train", "val", "dev", "test"])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--concurrency", type=int, default=1,
                        help="Parallel questions, or parallel conversations in free-running mode")
    parser.add_argument("--batch-size", type=int, default=1,
                        help="True generation batch size; supported only by local QLoRA reference-history runs")
    parser.add_argument("--verify-batch-equivalence", type=int, default=4,
                        help="Compare this many single and batched QLoRA answers before writing output")
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
    parser.add_argument('--bert-batch-size', type=int, default=16)
    args = parser.parse_args(argv)
    if args.command in {"retrieval-run", "retrieval-score"}:
        if not args.out:
            parser.error(f"{args.command} requires --out")
        if args.split == "dev":
            parser.error(f"{args.command} uses the selected QA split without generation")
        dataset, view = resolve_dataset(args.dataset, args.view)
        from .retrieval_benchmark import run_retrieval, score_retrieval
        if args.command == "retrieval-run":
            report = run_retrieval(
                dataset=dataset, view=view, split=args.split or "test", config_path=args.config,
                output=args.out, top_k=args.top_k, limit=args.limit,
            )
        else:
            missing = [name for name, value in (("--predictions", args.predictions),) if not value]
            if missing:
                parser.error("retrieval-score requires " + ", ".join(missing))
            report = score_retrieval(
                dataset=dataset, view=view, split=args.split or "test", predictions=args.predictions,
                unit_map=args.unit_map, output=args.out, ks=args.ks, limit=args.limit,
            )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    if args.command == "noise-v2":
        if not args.predictions or not args.out or not args.model_id or args.split == "dev":
            parser.error("noise-v2 requires --predictions, --out and --model-id")
        from .noise import run_noise
        statuses = run_noise(
            dataset=args.golden_dir, split=args.split or "test", predictions=args.predictions,
            output=args.out, endpoint=args.endpoint or "http://localhost:8001/api/chat",
            model_id=args.model_id,
        )
        counts = {status: list(statuses.values()).count(status) for status in sorted(set(statuses.values()))}
        print(json.dumps({"output": str(args.out), "case_status": counts}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "score-noise-v2":
        if not args.judgments or not args.other_predictions or not args.out:
            parser.error("score-noise-v2 requires --judgments, --other-predictions and --out")
        from .noise import score_noise
        print(json.dumps(score_noise(
            clean_judgments=args.judgments, noise_judgments=args.other_predictions, output=args.out,
        ), ensure_ascii=False, indent=2))
        return 0
    if args.command == "complete-v2":
        if not args.architecture or not args.out or not args.judge_model or args.split == "dev":
            parser.error("complete-v2 requires --architecture, --out and --judge-model")
        from .complete import complete
        print(json.dumps(complete(dataset=args.golden_dir, split=args.split or "test", architecture=args.architecture,
                                  output=args.out, model_id=args.model_id, judge_model=args.judge_model,
                                  endpoint=args.endpoint or "http://localhost:8001/api/chat", judge_endpoint=args.judge_endpoint,
                                  bert_model=args.bert_model, bert_device=args.bert_device,
                                  bert_batch_size=args.bert_batch_size), ensure_ascii=False, indent=2))
        return 0
    if args.command == "pairwise-v2":
        if not args.predictions or not args.other_predictions or not args.out or args.split == "dev":
            parser.error("pairwise-v2 requires two predictions and --out")
        from .pairwise import pairwise
        print(json.dumps(pairwise(dataset=args.golden_dir, split=args.split or "test", predictions=args.predictions,
                                  other=args.other_predictions, output=args.out, judgments=args.judgments), ensure_ascii=False))
        return 0
    if args.command == "judge-v2":
        if not args.judge_model or not args.predictions or not args.out or args.split == "dev":
            parser.error("judge-v2 requires --judge-model, --predictions, --out and Golden split")
        from .ollama_judge import judge
        print(json.dumps(judge(dataset=args.golden_dir, split=args.split or "test",
                               predictions=args.predictions, output=args.out,
                               model=args.judge_model, endpoint=args.judge_endpoint,
                               limit=args.limit, resume=args.resume,
                               allow_partial=args.allow_partial), ensure_ascii=False, indent=2))
        return 0
    if args.command == "run-v2":
        missing = [name for name, value in (("--architecture", args.architecture), ("--out", args.out)) if not value]
        if missing:
            parser.error("run-v2 requires " + ", ".join(missing))
        if args.split == "dev":
            parser.error("run-v2 uses Golden split names train, val or test; dev is not valid")
        from .v2 import run_v2
        report = run_v2(
            dataset=args.golden_dir, split=args.split or "test", architecture=args.architecture,
            output=args.out, limit=args.limit, endpoint=args.endpoint or "http://localhost:8001/api/chat",
            model_id=args.model_id, timeout=args.timeout, resume=args.resume, complete_trace=args.complete_trace,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return int(report["execution_status"].get("error", 0) > 0)
    if args.command == "export-v2":
        missing = [name for name, value in (("--run-id", args.run_id), ("--architecture", args.architecture),
                                             ("--model-name", args.model_name), ("--out", args.out)) if not value]
        if missing:
            parser.error("export-v2 requires " + ", ".join(missing))
        if args.split == "dev":
            parser.error("export-v2 uses Golden split names train, val or test; dev is not valid")
        from .v2 import export_v2
        summary = export_v2(
            dataset=args.golden_dir, split=args.split or "test", predictions=args.predictions,
            architecture=args.architecture, model_name=args.model_name, run_id=args.run_id,
            output=args.out, model_config_path=args.model_config, allow_partial=args.allow_partial,
            judgments=args.judgments,
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    if args.command == "score-v2-offline":
        missing = [name for name, value in (("--architecture", args.architecture), ("--predictions", args.predictions),
                                             ("--out", args.out)) if not value]
        if missing:
            parser.error("score-v2-offline requires " + ", ".join(missing))
        if args.split == "dev":
            parser.error("score-v2-offline uses Golden split names train, val or test; dev is not valid")
        from .offline_v2 import score_offline_v2
        summary = score_offline_v2(
            dataset=args.golden_dir, split=args.split or "test", predictions=args.predictions,
            architecture=args.architecture, output=args.out, bertscore=args.bertscore,
            bert_model=args.bert_model, bert_device=args.bert_device, bert_batch_size=args.bert_batch_size,
            extended=args.extended_metrics, allow_partial=args.allow_partial,
        )
        print(json.dumps({"output": str(args.out), "metrics": summary["metrics"]}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "test":
        if not args.run_id:
            parser.error("--run-id is required for test")
        from vigovbot.training.evaluate import evaluate
        result = evaluate(Path("outputs/qlora") / args.run_id, split=args.split or "test", limit=args.limit)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    args.dataset, args.view = resolve_dataset(args.dataset, args.view)
    if args.no_retrieval and args.endpoint:
        parser.error("--no-retrieval cannot be combined with --endpoint")
    if args.no_retrieval and args.qlora_run_dir:
        parser.error("--no-retrieval cannot be combined with --qlora-run-dir")
    if args.qlora_run_dir and args.concurrency != 1:
        parser.error("Local QLoRA evaluation requires --concurrency 1 on a single GPU")
    if args.oracle_evidence and (args.no_retrieval or args.endpoint or args.command != 'run'):
        parser.error('--oracle-evidence requires local run and cannot combine with baseline/HTTP')
    if (args.top_k < 1 or args.timeout <= 0 or args.concurrency < 1 or args.batch_size < 1
            or args.verify_batch_equivalence < 0 or (args.limit is not None and args.limit < 1)):
        parser.error("top-k, timeout, concurrency and limit must be positive")
    if args.batch_size > 1 and (not args.qlora_run_dir or args.mode != "reference_history"):
        parser.error("--batch-size > 1 is supported only with --qlora-run-dir and --mode reference_history")
    if args.command == "ask" and not args.question:
        parser.error("--question is required")
    if args.command == "score":
        if not args.predictions:
            parser.error("--predictions is required")
        from .scoring import evaluate
        cases_path = dataset_file(args.dataset, "cases", args.split)
        cases = select_rows(read_jsonl(cases_path), args.dataset, args.view, args.split, args.limit)
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
            [cases_path, args.dataset / args.view if args.view else None, args.predictions,
             args.unit_map, args.judgments, args.bert_cache] if p}
        manifest = args.dataset / 'manifest.json'
        report['dataset_status'] = json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else None
        from .review import fingerprint
        report['benchmark'] = {'cases_sha256': sha256(cases_path),
                               'selected_ids_sha256': fingerprint(sorted(c['id'] for c in cases))}
        report['case_groups'] = {c['id']: c.get('conversation_id') or c.get('procedure_family_id')
                                 or c.get('document_id') or c['id'] for c in cases}
        report["history_mode"] = next(iter(modes), None)
        from .benchmark_report import finalize_report
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
        queries = load_queries(dataset_file(args.dataset, "queries", args.split),
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
    from .adapter import existing_rag, http_rag, ollama_baseline, ollama_oracle, qlora_adapter
    oracle_contexts = None
    if args.oracle_evidence:
        ids = {q['id'] for q in queries}
        # Only evidence is forwarded. Reference text and behavior labels stay in the evaluator.
        oracle_contexts = {c['id']: c['evidence'] for c in read_jsonl(
            dataset_file(args.dataset, "cases", args.split)) if c['id'] in ids}
        session = ollama_oracle(args.config)
    elif args.qlora_run_dir:
        session = qlora_adapter(args.qlora_run_dir)
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
            from .benchmark_runner import run_queries
            from .audit import sha256
            if args.qlora_run_dir and args.batch_size > 1 and args.verify_batch_equivalence:
                sample = queries[:min(args.verify_batch_equivalence, len(queries))]
                singles = [answer(item["question"], history=item.get("history", []))["answer"] for item in sample]
                batched = answer.answer_batch([{"question": item["question"], "history": item.get("history", [])}
                                               for item in sample])
                batch_answers = [item["answer"] for item in batched]
                if singles != batch_answers:
                    raise RuntimeError("Batch equivalence check failed; use --batch-size 1 for this model")
                print(f"[QLoRA] Batch equivalence PASS on {len(sample)} samples.", flush=True)
            provenance = {'mode': ('oracle' if args.oracle_evidence else
                                   ('qlora' if args.qlora_run_dir else ('base' if args.no_retrieval else 'rag'))),
                          'inputs': {str(p): sha256(p) for p in
                              [dataset_file(args.dataset, "queries", args.split),
                               args.dataset / args.view if args.view else None] if p},
                          'config_sha256': (sha256(args.qlora_run_dir / "config.yaml") if args.qlora_run_dir else
                                            (sha256(args.config) if not args.endpoint else None)),
                          'adapter_path': str(args.qlora_run_dir / "best_adapter") if args.qlora_run_dir else None,
                          'output_contract': ('plain_assistant_answer_action_unavailable'
                                              if args.qlora_run_dir else None)}
            report = run_queries(queries, answer, args.out or Path("outputs/qa_v4/predictions.jsonl"), args.mode,
                                 oracle_contexts=oracle_contexts, provenance=provenance,
                                 concurrency=args.concurrency, batch_size=args.batch_size)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return int(report["failed"] > 0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
