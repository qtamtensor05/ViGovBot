"""Check implemented routing with local Qwen; no encoder/corpus is needed."""
import json
from pathlib import Path
import sys

from transformers import AutoTokenizer
from vigovbot.rag.config import load_config
from vigovbot.rag.pipeline import answer_question, source_fingerprint
from vigovbot.rag.version import PIPELINE_VERSION
from vigovbot.llm.llm_client import check_model
from probe_oil_spill_routing import QUESTION, EmptyRetriever


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    group = sys.argv[1]
    config = load_config("configs/inference.yaml")
    model_info = check_model(config.llm.ollama_url, config.llm.model)
    tokenizer = AutoTokenizer.from_pretrained(config.llm.tokenizer, local_files_only=True)
    passport_history = [{"role": "user", "content": "Tôi muốn tìm hiểu thủ tục cấp hộ chiếu."},
                        {"role": "assistant", "content": "Bạn muốn biết hồ sơ hay lệ phí cấp hộ chiếu?"}]
    if group == "oil":
        cases = [("oil_no_history", QUESTION, [], "in_scope", "new_question"),
                 ("oil_topic_change", QUESTION, passport_history, "in_scope", "new_question")]
    elif group == "basic":
        cases = [("follow_up", "Còn lệ phí?", passport_history, "in_scope", "follow_up"),
                 ("ambiguous", "Còn lệ phí?", [], "in_scope", "ambiguous"),
                 ("out_of_scope", "Viết bài thơ về mùa thu.", [], "out_of_scope", "new_question"),
                 ("new_question", "Hồ sơ cấp bản sao trích lục khai sinh gồm những gì?", [], "in_scope", "new_question")]
    else:
        raise ValueError("group must be oil or basic")
    rows = []
    for name, question, history, scope, relation in cases:
        result = answer_question(question, EmptyRetriever(), tokenizer, config.inference_settings(), history=history)
        route = result["routing"]
        passed = (route["scope"] == scope and route["relation"] == relation
                  and not result["fallback_reason"])
        if name == "follow_up":
            passed = passed and "hộ chiếu" in route["query"].lower()
        rows.append({"case": name, "question": question, "history": history, "passed": passed,
                     "expected": {"scope": scope, "relation": relation}, "result": result})
        print(json.dumps({"case": name, "passed": passed, "route": route,
                          "attempts": result["routing_attempts"], "fallback": result["fallback_reason"]},
                         ensure_ascii=False))
    artifact = Path(f"outputs/qa_v4/routing_implemented_{group}.json")
    artifact.write_text(json.dumps({"scope": "Routing-only smoke with empty retriever; synthetic histories",
                                    "pipeline_version": PIPELINE_VERSION, "source_fingerprint": source_fingerprint(),
                                    "settings": config.inference_settings(), "model_info": model_info,
                                    "tokenizer": config.llm.tokenizer,
                                    "tokenizer_revision": getattr(tokenizer, "init_kwargs", {}).get("_commit_hash"),
                                    "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Artifact: {artifact}")
    if not all(row["passed"] for row in rows):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
