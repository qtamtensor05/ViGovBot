"""Offline extensions; review identity is checked before any output is written."""
from .io import read_jsonl
from .provenance import fingerprint
from .ollama_judge import validate, validate_claims, judgment_payload


def load_reviews(path, cases, predictions):
    if path is None:
        return {}
    cases = {c["test_id"]: c for c in cases}
    result = {}
    for review in read_jsonl(path):
        cid = review.get("id")
        if cid in result or cid not in cases or cid not in predictions:
            raise ValueError("Duplicate or unknown review ID")
        if review.get("input_sha256") != fingerprint(judgment_payload(cases[cid], predictions[cid])):
            raise ValueError("Stale review input hash: " + cid)
        if review.get("reviewer_kind") not in {"ai", "human"} or not review.get("reviewer") or not review.get("rubric_sha256"):
            raise ValueError("Review provenance required")
        validate(review)
        if "claims" in review:
            generation = predictions[cid].get("execution", {}).get("generation") or {}
            validate_claims(review["claims"], generation.get("actual_output"))
            allowed = set(cases[cid]["ground_truth"].get("ground_truth_context_ids", []))
            retrieval = predictions[cid].get("execution", {}).get("retrieval") or {}
            allowed.update(c.get("context_id") for c in retrieval.get("contexts", []) if isinstance(c, dict))
            if any(set(claim["source_ids"]) - allowed for claim in review["claims"]):
                raise ValueError("Unknown claim evidence ID")
        result[cid] = review
    return result


def extend_record(record, prediction, review=None):
    evaluation = record["evaluation_results"]
    def put(group, key, value, scorer):
        status = "computed" if value is not None else "missing_input"
        evaluation["metrics"].setdefault(group, {})[key] = {
            "value": value, "status": status, "scorer_version": scorer if value is not None else None,
            "reason": None if value is not None else "Required trace or reviewed judgment is unavailable",
        }
    gt = record["golden"]["ground_truth"]
    from vigovbot.utils.text import normalize_vietnamese as normalize_text
    expected = gt.get("ground_truth_sub_queries") or []
    query_processing = prediction.get("execution", {}).get("query_processing") or {}
    actual = query_processing.get("sub_queries")
    if expected and isinstance(actual, list) and all(isinstance(q, str) for q in expected):
        gold_queries = {normalize_text(q) for q in expected}
        predicted_queries = {normalize_text(q["query"]) for q in actual}
        matched = gold_queries & predicted_queries
        put("query_processing", "sub_query_recall", len(matched) / len(gold_queries), "normalized-exact-set-v1")
        put("query_processing", "sub_query_precision", len(matched) / len(predicted_queries) if predicted_queries else 0.0, "normalized-exact-set-v1")
        mapping = gt.get("sub_query_context_mapping") or {}
        retrieval = prediction.get("execution", {}).get("retrieval") or {}
        actual_mapping = {item["sub_query_id"]: [context["context_id"] for context in item.get("contexts", [])]
                          for item in retrieval.get("sub_query_results", [])}
        coverage = []
        for query, ids in mapping.items():
            if not isinstance(ids, list) or not ids:
                continue
            found = set()
            for item in actual:
                if normalize_text(item["query"]) == normalize_text(query):
                    found.update(actual_mapping.get(item["sub_query_id"], []))
            coverage.append(float(bool(found & set(ids))))
        if coverage:
            put("retrieval", "multi_intent_retrieval_coverage", sum(coverage) / len(coverage), "normalized-query-known-evidence-hit-v1")
    relevant = set(gt.get("ground_truth_context_ids", []))
    retrieval = prediction.get("execution", {}).get("retrieval") or {}
    retrieved = list(dict.fromkeys(context["context_id"] for context in retrieval.get("contexts", [])))
    depth = retrieval.get("top_k")
    if record["architecture"] in {"rag", "finetuned_rag"} and relevant and type(depth) is int and depth >= 10:
        hits, ap = 0, 0.0
        for rank, cid in enumerate(retrieved[:10], 1):
            if cid in relevant:
                hits += 1
                ap += hits / rank
        put("retrieval", "map_at_10", ap / min(10, len(relevant)), "binary-ap10-v1")
    if review:
        for key, value in review["scores"].items():
            group = next((g for g in ("generation", "robustness")
                          if key in evaluation["metrics"].get(g, {})), None)
            if group:
                put(group, key, value, "review:" + review["reviewer"])
        claims = review.get("claims", [])
        if claims:
            put("generation", "unsupported_claim_rate", sum(c["verdict"] != "supported" for c in claims) / len(claims), "judge-extracted-claims-v1")
            put("generation", "hallucination_rate", sum(c["verdict"] == "contradicted" for c in claims) / len(claims), "judge-evidence-contradiction-rate-v1")
