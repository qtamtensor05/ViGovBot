"""Connect the QA runner to the existing RAG without changing its models."""
from contextlib import contextmanager
import json
from urllib.request import Request, urlopen


def normalize_result(result, unit_mapping=None):
    if not isinstance(result, dict):
        raise ValueError("RAG response must be an object")
    answer = result.get("answer", result.get("prediction"))
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("RAG response must contain a nonempty answer/prediction")
    chunks = result.get("retrieved_chunk_ids", [h["chunk_id"] for h in result.get("retrieved", [])])
    units = result.get("retrieved_unit_ids")
    if units is None and unit_mapping is not None:
        units = list(dict.fromkeys(uid for cid in chunks for uid in unit_mapping.get(cid, [])))
        unmapped = [cid for cid in chunks if cid not in unit_mapping]
        status = "incomplete_mapping" if unmapped else "mapped"
    else:
        unmapped = []
        status = "provided" if units is not None else "unavailable"
    if units is not None and (not isinstance(units, list) or any(not isinstance(uid, str) for uid in units)):
        raise ValueError("retrieved_unit_ids must be a list of strings")
    telemetry = result.get("telemetry", {
        "retrieval_seconds": result.get("retrieval_s"), "routing_seconds": result.get("routing_s"),
        "generation_seconds": result.get("generation_s"),
        "output_tokens": (result.get("raw_ollama") or {}).get("eval_count"),
    })
    normalized = {"answer": answer, "action": result.get("action"), "retrieved_chunk_ids": chunks,
                  "citations": result.get("citations", []), "context_used": result.get("context_used", []),
                  "retrieval_query": result.get("retrieval_query"), "telemetry": telemetry,
                  "unit_mapping_status": status, "unmapped_chunk_ids": unmapped}
    if units is not None:
        normalized["retrieved_unit_ids"] = units
    return normalized


@contextmanager
def existing_rag(config_path, unit_mapping=None):
    # Reuse the existing config, corpus, query encoder, tokenizer and inference logic.
    from vigovbot.rag.config import load_config
    from vigovbot.rag.pipeline import prepare, inference_session, answer_question
    from vigovbot.llm.llm_client import check_model

    config = load_config(config_path)
    paths = prepare(config)
    check_model(config.llm.ollama_url, config.llm.model)
    with inference_session(config, paths) as (retriever, tokenizer):
        def answer(question, history=None):
            result = answer_question(question, retriever, tokenizer, config.inference_settings(),
                                     history=history, structured=True)
            return normalize_result(result, unit_mapping)
        yield answer


@contextmanager
def http_rag(endpoint, timeout=300, unit_mapping=None):
    def answer(question, history=None):
        request = Request(endpoint, data=json.dumps({"question": question, "history": history or []},
                          ensure_ascii=False).encode("utf-8"), headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=timeout) as response:
            return normalize_result(json.load(response), unit_mapping)
    yield answer
