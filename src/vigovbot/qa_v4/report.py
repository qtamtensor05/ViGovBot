"""Report retrieval scores only when evidence IDs are compatible."""
import json
from pathlib import Path


def finalize_report(report, predictions, selected_ids, prediction_path):
    if report.get('retrieval_evaluation', {}).get('rank_unit') == 'original_unique_chunk':
        path = Path(str(prediction_path) + '.run.json')
        if path.exists():
            report['runner_performance'] = json.loads(path.read_text(encoding='utf-8'))
        return report
    valid = [p for p in predictions if p["id"] in selected_ids and not p.get("error")]
    available = bool(valid) and all("retrieved_unit_ids" in p and p.get("unit_mapping_status")
                                   not in {"unavailable", "incomplete_mapping"} for p in valid)
    report["retrieval_evaluation"] = {"available": available,
        "note": "Requires explicit v4 unit IDs or complete chunk-to-unit mapping."}
    if not available:
        keys = {"judged_evidence_recall_at_k", "mrr_at_k", "judged_hit_rate_at_k", "unjudged_retrieved_count"}
        def strip(value):
            if isinstance(value, dict):
                return {k: strip(v) for k, v in value.items() if k not in keys}
            if isinstance(value, list):
                return [strip(v) for v in value]
            return value
        report = strip(report)
    path = Path(str(prediction_path) + ".run.json")
    if path.exists():
        report["runner_performance"] = json.loads(path.read_text(encoding="utf-8"))
    return report
