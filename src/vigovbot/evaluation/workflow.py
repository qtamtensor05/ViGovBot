"""Run-directory orchestration for the canonical Golden contract."""
import json
import os
import re
import tempfile
from pathlib import Path
from vigovbot.artifacts import file_hash, output_lock
from .records import load_golden, capture_predictions, export_scores, DEFAULT_WEB_MODELS
from .provenance import fingerprint

PROFILES = {"base": "base", "rag": "rag", "qlora": "finetuned"}


def run_directory(root, run_id):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", run_id or ""):
        raise ValueError("Invalid run-id: use letters, digits, dot, underscore or hyphen")
    return Path(root) / run_id


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)


def validate(dataset, split):
    path, rows = load_golden(dataset, split)
    return {"dataset": str(path.resolve()), "sha256": file_hash(path), "split": split,
            "expected": len(rows), "selected_ids_sha256": fingerprint([r["test_id"] for r in rows])}


def dispatch(args):
    if args.command == "validate":
        return validate(args.dataset, args.split)
    directory = run_directory(args.output_root, args.run_id)
    directory.mkdir(parents=True, exist_ok=True)
    with output_lock(directory, ".workflow.lock"):
        return _dispatch(args, directory)


def _dispatch(args, directory):
    manifest_path = directory / "run-manifest.json"
    predictions = directory / "predictions.jsonl"
    if args.command in {"run", "evaluate"}:
        identity = validate(args.dataset, args.split)
        if args.scope == "retrieval" and args.profile != "rag":
            raise ValueError("Retrieval scope requires profile rag")
        manifest = {**identity, "profile": args.profile, "scope": args.scope,
                    "run_id": args.run_id, "dataset_dir": str(args.dataset.resolve()),
                    "endpoint": args.endpoint, "limit": args.limit,
                    "complete_trace": args.complete_trace, "top_k": args.top_k,
                    "config": str(args.config.resolve()), "config_sha256": file_hash(args.config),
                    "model_metadata": str(args.model_metadata.resolve()) if args.model_metadata else None,
                    "model_metadata_sha256": file_hash(args.model_metadata) if args.model_metadata else None,
                    "model_id": DEFAULT_WEB_MODELS[PROFILES[args.profile]]}
        if manifest_path.exists():
            if not args.resume:
                raise FileExistsError("Run exists; use --resume with the same configuration")
            if _read(manifest_path) != manifest:
                raise ValueError("Dataset/profile/config changed; use a new run-id")
        else:
            _write(manifest_path, manifest)
        if args.scope == "retrieval":
            from .retrieval_benchmark import run_retrieval
            if args.resume and predictions.exists():
                raise ValueError("Retrieval capture cannot resume partial files; use a new run-id")
            report = run_retrieval(dataset=args.dataset, view=None, split=args.split,
                                   config_path=args.config, output=predictions,
                                   top_k=args.top_k, limit=args.limit, run_id=args.run_id)
        else:
            model_metadata = _read(args.model_metadata) if args.model_metadata else None
            report = capture_predictions(dataset=args.dataset, split=args.split, architecture=PROFILES[args.profile],
                            output=predictions, limit=args.limit, endpoint=args.endpoint,
                            timeout=args.timeout, resume=args.resume, complete_trace=args.complete_trace,
                            model_metadata=model_metadata, run_id=args.run_id)
        if args.command == "run" or report.get("execution_status", {}).get("error"):
            return report
    if not manifest_path.exists():
        raise FileNotFoundError("Run manifest missing; capture with vigov eva run first")
    manifest = _read(manifest_path)
    dataset = Path(manifest["dataset_dir"])
    if validate(dataset, manifest["split"])["sha256"] != manifest["sha256"]:
        raise ValueError("Golden data changed since capture")
    if args.profile and args.profile != manifest["profile"]:
        raise ValueError("Profile does not match the run manifest")
    if args.command == "compare":
        if not args.other_run_id:
            raise ValueError("compare requires --other-run-id")
        other = run_directory(args.output_root, args.other_run_id)
        right = _read(other / "run-manifest.json")
        if any(right[k] != manifest[k] for k in ("sha256", "split", "scope")):
            raise ValueError("Compared runs must use the same Golden split and scope")
        from .pairwise import pairwise
        return pairwise(dataset=dataset, split=manifest["split"], predictions=predictions,
                        other=other / "predictions.jsonl", output=directory / ("comparison-" + args.other_run_id + ".json"))
    score_path = directory / "scores.json"
    if args.command in {"score", "evaluate"}:
        if score_path.exists():
            if args.rescore:
                pass
            elif args.command == "score" or not args.resume:
                raise FileExistsError("Scores already exist")
        if not score_path.exists() or args.rescore:
            with tempfile.TemporaryDirectory(prefix=".score-", dir=directory) as temporary:
                temporary = Path(temporary)
                case_scores = temporary / "case-scores.jsonl"
                supplemental = None
                supplemental_path = None
                if manifest["scope"] == "retrieval":
                    summary = export_scores(
                        dataset=dataset, split=manifest["split"], predictions=predictions,
                        architecture="rag", model_name=manifest["model_id"], run_id=manifest["run_id"],
                        output=case_scores, output_reference=directory / "case-scores.jsonl",
                        allow_partial=args.allow_partial)
                else:
                    judgments = directory / "judgments.jsonl"
                    if args.judge_model:
                        from .ollama_judge import judge
                        judge(dataset=dataset, split=manifest["split"], predictions=predictions, output=judgments,
                              model=args.judge_model, endpoint=args.judge_endpoint,
                              resume=args.resume, allow_partial=args.allow_partial)
                    if args.bertscore or args.extended_metrics:
                        from .scoring import score_supplemental
                        supplemental_path = temporary / "supplemental.json"
                        supplemental = score_supplemental(
                            dataset=dataset, split=manifest["split"], predictions=predictions,
                            architecture=PROFILES[manifest["profile"]], output=supplemental_path,
                            bertscore=args.bertscore, bert_model=args.bert_model, bert_device=args.bert_device,
                            bert_batch_size=args.bert_batch_size, extended=args.extended_metrics,
                            allow_partial=args.allow_partial)
                    summary = export_scores(
                        dataset=dataset, split=manifest["split"], predictions=predictions,
                        architecture=PROFILES[manifest["profile"]], model_name=manifest["model_id"],
                        run_id=manifest["run_id"], output=case_scores,
                        judgments=judgments if judgments.exists() else None,
                        supplemental=supplemental, supplemental_path=supplemental_path,
                        supplemental_reference=directory / "supplemental.json",
                        output_reference=directory / "case-scores.jsonl",
                        allow_partial=args.allow_partial)
                temporary_score = temporary / "scores.json"
                _write(temporary_score, summary)
                os.replace(case_scores, directory / "case-scores.jsonl")
                os.replace(Path(str(case_scores) + ".summary.json"),
                           directory / "case-scores.jsonl.summary.json")
                if supplemental_path:
                    os.replace(supplemental_path, directory / "supplemental.json")
                elif args.rescore and (directory / "supplemental.json").exists():
                    (directory / "supplemental.json").unlink()
                os.replace(temporary_score, score_path)
                if args.rescore and (directory / "report.json").exists():
                    refreshed_report = {"run": manifest, "scores": summary, "inference_performed": False}
                    temporary_report = temporary / "report.json"
                    _write(temporary_report, refreshed_report)
                    os.replace(temporary_report, directory / "report.json")
        if args.command == "score":
            return _read(score_path)
    if not score_path.exists():
        raise FileNotFoundError("Scores missing; run vigov eva score first")
    report = {"run": manifest, "scores": _read(score_path), "inference_performed": False}
    report_path = directory / "report.json"
    if report_path.exists():
        if _read(report_path) != report:
            raise ValueError("Report differs from persisted scores")
    else:
        _write(report_path, report)
    return report
