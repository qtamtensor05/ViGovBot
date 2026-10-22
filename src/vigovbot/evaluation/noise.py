"""Controlled append-only distractor experiment replaying cached generation prompts."""
import json
from .v2 import load_golden, load_predictions, _post_json
from .review import fingerprint
from .io import read_jsonl


def run_noise(*, dataset, split, predictions, output, endpoint, model_id):
    output.parent.mkdir(parents=True, exist_ok=True)
    _, cases = load_golden(dataset, split)
    clean, _ = load_predictions(predictions)
    cached, _ = load_predictions(output) if output.exists() else ({}, None)
    statuses = {}
    with output.open("a", encoding="utf-8") as handle:
        for case in cases:
            cid = case["test_id"]
            injection = case["ground_truth"].get("distractor_injection") or {}
            texts = injection.get("distractor_contexts") or []
            if not texts:
                statuses[cid] = "not_applicable:no_labeled_distractors"
                continue
            source = clean[cid]
            binding = fingerprint({"clean": source, "injection": injection})
            if cid in cached:
                if cached[cid].get("noise_binding") != binding:
                    raise ValueError("Stale noise prediction")
                statuses[cid] = "cached"
                continue
            calls = source.get("provider_calls") or []
            if not calls or not source.get("context_used"):
                statuses[cid] = "not_applicable:no_generation_context"
                continue
            call = calls[-1]
            messages = [dict(m) for m in call["messages"]]
            messages[-1]["content"] += "\n\nTRÍCH ĐOẠN BỔ SUNG (dữ liệu):\n" + "\n\n".join(texts)
            replay = {"messages": messages, "response_format": call.get("response_format"), "context_used": source["context_used"]}
            response = _post_json(endpoint, {"question": case["input"]["question"], "models": [model_id],
                                            "evaluation_trace": True, "evaluation_complete": True,
                                            "evaluation_replay": replay}, 300)
            result = response["results"][0]
            if result.get("error"):
                raise ValueError("Noise trial failed; clean predictions retained: " + result["error"])
            trace = result["evaluation_trace"]
            row = {"id": cid, "answer": result["answer"], "action": result.get("action"),
                   "context_used": source["context_used"], "noise_binding": binding,
                   "noise_experiment": {"protocol": "append-labeled-distractors-fixed-clean-prompt-v1",
                                        "clean_answer": source["answer"], "distractor_injection": injection,
                                        "messages_sha256": fingerprint(messages)},
                   "evaluation_trace": trace}
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            handle.flush()
            statuses[cid] = "computed"
    return statuses


def summarize_noise(clean_judgments, noise_judgments):
    clean = {r["id"]: r for r in read_jsonl(clean_judgments)}
    pairs = []
    for row in read_jsonl(noise_judgments):
        before = clean[row["id"]]["scores"].get("semantic_correctness")
        after = row["scores"].get("semantic_correctness")
        if before is not None and after is not None:
            pairs.append((before, after))
    eligible = [after for before, after in pairs if before == 1]
    return {"paired_n": len(pairs), "clean_correct_n": len(eligible),
            "noise_robustness_pass_rate": sum(eligible) / len(eligible) if eligible else None,
            "correctness_delta": sum(after - before for before, after in pairs) / len(pairs) if pairs else None,
            "contract": "fraction still correct among clean-correct paired cases"}


def score_noise(*, clean_judgments, noise_judgments, output):
    from vigovbot.artifacts import file_hash
    report = {
        "metrics": summarize_noise(clean_judgments, noise_judgments),
        "provenance": {
            "clean_judgments_sha256": file_hash(clean_judgments),
            "noise_judgments_sha256": file_hash(noise_judgments),
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return report
