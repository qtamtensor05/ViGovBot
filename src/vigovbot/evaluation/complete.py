"""One invocation, immutable predictions, resumable local judging and offline scoring."""
import json
from .v2 import run_v2, export_v2
from .ollama_judge import judge
from .offline_v2 import score_offline_v2
from vigovbot.artifacts import file_hash


REQUIRED_WEB_CAPABILITIES = {
    "automatic_complete_trace",
    "retrieval_top_k_10",
    "sub_query_retrieval",
    "claim_citations",
    "provider_call_token_usage",
    "provider_call_ttft",
    "provider_call_latency",
    "provider_call_gpu_samples",
    "runtime_identity",
    "noise_replay",
    "gpu_release_before_offline_scoring",
}


def complete(*, dataset, split, architecture, output, model_id, judge_model, endpoint,
             judge_endpoint, bert_model, bert_device, bert_batch_size):
    import requests
    from urllib.parse import urlsplit, urlunsplit
    parts = urlsplit(endpoint)
    health_url = urlunsplit((parts.scheme, parts.netloc, "/api/health", "", ""))
    health = requests.get(health_url, timeout=20)
    health.raise_for_status()
    health_payload = health.json()
    capabilities = health_payload.get("evaluation_complete_capabilities") or {}
    missing_capabilities = sorted(name for name in REQUIRED_WEB_CAPABILITIES if capabilities.get(name) is not True)
    if health_payload.get("evaluation_complete_version") != 2 or missing_capabilities:
        detail = ", ".join(missing_capabilities) if missing_capabilities else "version 2"
        raise ValueError(f"Restart updated web server before complete-v2; missing {detail}; no inference started")
    import importlib.util
    missing = [name for name in ("nltk", "sentence_transformers", "bert_score", "sacrebleu") if importlib.util.find_spec(name) is None]
    if missing:
        raise ValueError("Scoring dependencies missing before inference: " + ", ".join(missing))
    gpu_response = requests.get(urlunsplit((parts.scheme, parts.netloc, "/api/evaluation-gpu", "", "")), timeout=20)
    gpu_response.raise_for_status()
    if gpu_response.json().get("status") != "measured":
        raise ValueError("GPU sampler unavailable on web host; fix before inference to avoid missing runtime measurements")
    tags = requests.get(judge_endpoint.rstrip("/") + "/api/tags", timeout=20)
    tags.raise_for_status()
    if not any(m.get("name") == judge_model for m in tags.json().get("models", [])):
        raise ValueError("Judge model must be installed before starting the run")
    output.mkdir(parents=True, exist_ok=True)
    identity_url = urlunsplit((parts.scheme, parts.netloc, "/api/evaluation-identity", "", ""))
    identity_response = requests.get(identity_url, timeout=120)
    identity_response.raise_for_status()
    identity = identity_response.json()
    from .v2 import DEFAULT_WEB_MODELS
    selected_model = model_id or DEFAULT_WEB_MODELS.get(architecture)
    selected_identity = identity.get("models", {}).get(selected_model, {})
    if not selected_identity.get("digest") and not selected_identity.get("adapter_files"):
        raise ValueError("Selected model has no verifiable weight identity; inference not started")
    identity["models"] = {selected_model: selected_identity}
    identity_path = output / "runtime-identity.json"
    if identity_path.exists():
        if json.loads(identity_path.read_text(encoding="utf-8")) != identity:
            raise ValueError("Model/index/config/source changed: refusing mixed resume")
    else:
        with identity_path.open("x", encoding="utf-8") as handle:
            json.dump(identity, handle, ensure_ascii=False, indent=2)
    predictions = output / "predictions.jsonl"
    report = run_v2(dataset=dataset, split=split, architecture=architecture, output=predictions,
                    model_id=model_id, endpoint=endpoint, resume=True, complete_trace=True)
    if report["execution_status"].get("error"):
        raise ValueError("Prediction failures retained; resolve failed cases before scoring")
    after = requests.get(identity_url, timeout=120)
    after.raise_for_status()
    after_identity = after.json()
    after_identity["models"] = {selected_model: after_identity.get("models", {}).get(selected_model)}
    if after_identity != identity:
        raise ValueError("Runtime identity changed during inference; retained artifacts require audit")
    from .io import read_jsonl
    rows = list(read_jsonl(predictions))
    for row in rows:
        if not row.get("effective_settings") or not row.get("provider_calls"):
            raise ValueError("Server lacks complete trace support; cached predictions retained")
    judgments = output / "judgments.jsonl"
    judge(dataset=dataset, split=split, predictions=predictions, output=judgments, model=judge_model,
          endpoint=judge_endpoint, resume=True)
    noise_summary = {"status": "not_applicable", "reason": "Architecture has no retrieved context"}
    if architecture.startswith("rag"):
        from .noise import run_noise, summarize_noise
        noise_predictions, noise_judgments = output / "noise-predictions.jsonl", output / "noise-judgments.jsonl"
        noise_statuses = run_noise(dataset=dataset, split=split, predictions=predictions, output=noise_predictions,
                                   endpoint=endpoint, model_id=selected_model)
        if noise_predictions.stat().st_size:
            judge(dataset=dataset, split=split, predictions=noise_predictions, output=noise_judgments,
                  model=judge_model, endpoint=judge_endpoint, resume=True, allow_partial=True)
            noise_summary = {"status": "computed", **summarize_noise(judgments, noise_judgments)}
        else:
            noise_summary = {"status": "not_applicable", "reason": "No eligible labeled distractor cases"}
        noise_summary["case_statuses"] = noise_statuses
    release_url = urlunsplit((parts.scheme, parts.netloc, "/api/evaluation-release", "", ""))
    release = requests.post(release_url, timeout=120)
    release.raise_for_status()
    judge_release = requests.post(
        judge_endpoint.rstrip("/") + "/api/generate",
        json={"model": judge_model, "keep_alive": 0},
        timeout=120,
    )
    judge_release.raise_for_status()
    supplemental = output / "supplemental.json"
    if not supplemental.exists():
        score_offline_v2(dataset=dataset, split=split, predictions=predictions, architecture=architecture,
                         output=supplemental, bertscore=True, bert_model=bert_model,
                         bert_device=bert_device, bert_batch_size=bert_batch_size, extended=True)
    scores = json.loads(supplemental.read_text(encoding="utf-8"))
    if scores["provenance"]["predictions_sha256"] != file_hash(predictions):
        raise ValueError("Stale supplemental scores")
    bert_details = scores["metrics"]["metric_details"].get("bertscore_f1", {})
    if bert_details.get("model") != bert_model:
        raise ValueError("Cached BERTScore model differs; use a new supplemental output")
    if scores["metrics"]["metric_details"].get("meteor", {}).get("status") != "computed":
        raise ValueError("Old supplemental artifact lacks extended metrics; rescore cached predictions to a new artifact")
    results = output / "results.jsonl"
    if not results.exists():
        export_v2(dataset=dataset, split=split, predictions=predictions, architecture=architecture,
                  model_name=model_id or architecture, run_id=output.name, output=results, judgments=judgments)
    summary = json.loads((output / "results.jsonl.summary.json").read_text(encoding="utf-8"))
    if summary["provenance"]["predictions_sha256"] != file_hash(predictions) or summary["provenance"].get("judgments_sha256") != file_hash(judgments):
        raise ValueError("Cached results differ from current predictions/judgments")
    gpu_samples = [s for row in rows for call in row.get("provider_calls", []) for s in call.get("gpu", {}).get("samples", [])]
    hardware = {"scope": "device-wide; all recorded calls", "sample_count": len(gpu_samples),
                "peak_device_memory_used_gib": max((s["memory_used_gib"] for s in gpu_samples), default=None),
                "mean_device_utilization_percent": sum(s["utilization_percent"] for s in gpu_samples) / len(gpu_samples) if gpu_samples else None}
    manifest = {"predictions_sha256": file_hash(predictions), "judgments_sha256": file_hash(judgments),
                "results": str(results), "supplemental": str(supplemental),
                "human_evaluation": "separate", "model_inference_reused_on_resume": True,
                "noise_robustness": noise_summary,
                "hardware": hardware,
                "metric_aggregates": summary["metric_aggregates"], "supplemental_metrics": scores["metrics"],
                "limitations": ["Device GPU samples include other processes; not allocator memory", "Local cost has no billing contract"]}
    with (output / "complete.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
    return manifest
