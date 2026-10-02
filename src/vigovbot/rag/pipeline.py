from __future__ import annotations
import time
import gc
import json
import logging
from contextlib import contextmanager
from pathlib import Path

from vigovbot.embeddings.embedder import load_encoder
from vigovbot.evaluation.dataset import load_cases
from vigovbot.evaluation.runner import evaluate_cases
from vigovbot.ingestion.unified import verify_corpus
from vigovbot.llm.llm_client import check_model, unload_model
from vigovbot.prompts.prompt_templates import SYSTEM_PROMPT
from vigovbot.rag.version import PIPELINE_VERSION
from vigovbot.rag.routing import routing_messages, parse_route, parse_answer
from vigovbot.retrieval.retriever import Retriever
from vigovbot.utils.helpers import json_hash
from vigovbot.experiments import ensure_run, runtime_identity
from vigovbot.vectordb.vector_store import prepare_corpus
from vigovbot.prompts.prompt_templates import build_messages, validate_history
from vigovbot.llm.llm_client import ollama_answer
from vigovbot.artifacts import output_lock
from vigovbot.console import configure_console

LOG = logging.getLogger(__name__)


def select_cases(config):
    if config.data.dataset_path is None and config.data.dataset_zip is None:
        raise ValueError("Evaluation requires dataset_path or dataset_zip; use ask for inference only")
    cases = load_cases(config.data.dataset_path, config.data.dataset_zip)
    return cases, cases[: config.evaluation.max_cases] if config.evaluation.max_cases else cases


def source_fingerprint():
    """Phát hiện mã pipeline đổi, kể cả khi quên tăng số phiên bản."""
    root = Path(__file__).resolve().parents[1]
    folders = ("rag", "evaluation", "retrieval", "prompts", "llm")
    paths = [p for folder in folders for p in (root / folder).glob("*.py")]
    paths += [root / "ingestion/unified.py", root / "embeddings/embedder.py", root / "vectordb/vector_store.py"]
    paths += [root / name for name in ("schemas.py", "artifacts.py", "experiments.py", "utils/helpers.py")]
    return json_hash({str(p.relative_to(root)): p.read_text(encoding="utf-8") for p in sorted(paths)})


def manifest_base(config, cases, selected):
    identity, corpus_manifest = verify_corpus(config.data.unified_source, allow_legacy=config.data.allow_legacy_corpus)
    return {
        "pipeline_version": PIPELINE_VERSION,
        "source_fingerprint": source_fingerprint(),
        "parameters": config.model_dump(mode="json"),
        "settings": config.inference_settings(),
        "prompt": SYSTEM_PROMPT,
        "dataset_sha256": json_hash(cases),
        "selected_ids": [c["id"] for c in selected],
        "corpus_identity": identity,
        "corpus_embedding": corpus_manifest["embedding"] if corpus_manifest else None,
        "runtime": runtime_identity(),
    }


def verify_report_input(config, cases, selected):
    path = config.data.output_dir / "run_manifest.json"
    if not path.exists():
        raise ValueError("Chưa có run_manifest.json; chạy evaluate hoặc run trước")
    actual = json.loads(path.read_text(encoding="utf-8"))
    if any(actual.get(key) != value for key, value in manifest_base(config, cases, selected).items()):
        raise ValueError("Cấu hình/mã nguồn/dữ liệu không khớp kết quả đã lưu; dùng cấu hình gốc để report")


def prepare(config):
    result = prepare_corpus(
        config.data.unified_source, config.data.cache_dir, allow_legacy=config.data.allow_legacy_corpus
    )
    embedding = result[2].get("embedding")
    if embedding is not None:
        if config.embedding.model != embedding["model"] or (
            config.embedding.revision is not None and config.embedding.revision != embedding["revision"]
        ):
            raise ValueError("Query encoder model/revision does not match corpus embedding")
    LOG.info("Corpus: %d vector", result[2]["count"])
    return result


@contextmanager
def inference_session(config, paths):
    from transformers import AutoTokenizer

    encoder = retriever = None
    try:
        encoder_settings = config.embedding.model_dump()
        if paths[2].get("embedding") is not None:
            encoder_settings["revision"] = paths[2]["embedding"]["revision"]
        encoder = load_encoder(**encoder_settings)
        tokenizer = AutoTokenizer.from_pretrained(config.llm.tokenizer, revision=config.llm.tokenizer_revision)
        retriever = Retriever(paths[0], paths[1], encoder)
        yield retriever, tokenizer
    finally:
        if retriever is not None:
            retriever.close()
            retriever.encoder = None
        encoder = None
        gc.collect()
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        try:
            unload_model(config.llm.ollama_url, config.llm.model)
        except Exception as exc:
            LOG.warning("Không dỡ được Qwen khỏi Ollama: %s", exc)


def execute(config, command="run", *, question=None, history=None):
    configure_console()
    if command not in {"prepare", "ask", "smoke", "evaluate", "report", "run"}:
        raise ValueError(f"Unknown command: {command}")
    if command in {"evaluate", "report", "run"}:
        with output_lock(config.data.output_dir, ".pipeline.lock"):
            return _execute(config, command, question=question, history=history)
    return _execute(config, command, question=question, history=history)


def _execute(config, command="run", *, question=None, history=None):
    """prepare / smoke / evaluate / report / run; run thực hiện toàn bộ quy trình."""
    if command == "report":
        cases, selected = select_cases(config)
        verify_report_input(config, cases, selected)
        from vigovbot.evaluation.report import generate_report

        return generate_report(config, selected)
    if command == "ask" and (not isinstance(question, str) or not question.strip()):
        raise ValueError("Question must be nonempty")
    if command not in {"prepare", "ask"}:
        cases, selected = select_cases(config)
    paths = prepare(config)
    if command == "prepare":
        return {"count": paths[2]["count"], "database": str(paths[1])}
    model = check_model(config.llm.ollama_url, config.llm.model)
    if command == "ask":
        with inference_session(config, paths) as (retriever, tokenizer):
            return answer_question(question, retriever, tokenizer, config.inference_settings(), history=history)
    manifest = {**manifest_base(config, cases, selected), "ollama_digest": model.get("digest")}
    # Kiểm tra trước khi tải BGE-M3, tránh phí tài nguyên nếu cấu hình không khớp.
    if command != "smoke":
        ensure_run(config.data.output_dir, manifest)
    with inference_session(config, paths) as (retriever, tokenizer):

        def answer(question):
            return answer_question(question, retriever, tokenizer, config.inference_settings())

        if command in ("smoke", "run"):
            for case in selected[: config.evaluation.smoke_test_n]:
                result = answer(case["question"]["text"])
                print(
                    json.dumps(
                        {
                            "id": case["id"],
                            "question": case["question"]["text"],
                            "prediction": result["prediction"],
                            "latency_s": result["latency_s"],
                            "sources": result["retrieved"],
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                )
        if command == "smoke":
            return {"smoke_cases": min(config.evaluation.smoke_test_n, len(selected))}
        rows = evaluate_cases(selected, config.data.output_dir, manifest, answer)
    LOG.info("Hoàn tất %d/%d câu. Lỗi nếu có: %s", len(rows), len(selected), config.data.output_dir / "errors.jsonl")
    if not rows:
        raise RuntimeError("Không có câu trả lời thành công; kiểm tra errors.jsonl")
    if command == "evaluate":
        return {"completed": len(rows), "requested": len(selected)}
    from vigovbot.evaluation.report import generate_report

    return generate_report(config, selected)


def answer_question(question, retriever, tokenizer, settings, history=None, *, structured=False):
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Question must be nonempty")
    history = validate_history(history)
    started = time.perf_counter()
    routing_enabled = settings.get("routing_enabled", True)
    route, routing_raw, routing_s, routing_tokens = None, None, 0.0, 0
    if routing_enabled:
        routing_started = time.perf_counter()
        route_messages, routing_tokens = routing_messages(question, history, tokenizer, settings)
        route_text, routing_raw, _ = ollama_answer(route_messages, {**settings, "response_format": "json"})
        route = parse_route(route_text, history)
        routing_s = time.perf_counter() - routing_started

    def early_answer(text, action, reason, *, hits=(), used=(), tokens=0, retrieval_s=0.0):
        return {
            "prediction": text, "action": action, "decision_reason": reason,
            "routing": route, "routing_s": routing_s, "routing_prompt_tokens_estimated": routing_tokens,
            "raw_routing": routing_raw, "retrieval_query": None if not hits else retrieval_query,
            "evidence_status": "missing" if reason == "no_context" else None,
            "retrieved": [{key: h[key] for key in ("row_id", "score", "chunk_id", "source_file", "source_code")}
                          for h in hits],
            "context_used": list(used), "prompt_tokens_estimated": tokens,
            "retrieval_s": retrieval_s, "generation_s": 0.0,
            "latency_s": time.perf_counter() - started, "raw_ollama": None,
        }

    if route and route["scope"] == "out_of_scope":
        return early_answer("Mình hỗ trợ tra cứu thủ tục hành chính Việt Nam. Bạn cần tìm hiểu thủ tục nào?",
                            "abstain", "out_of_scope")
    if route and route["relation"] == "ambiguous":
        return early_answer(route["clarification"], "clarify", "ambiguous_question")
    # Rewrite follow-ups using only the supplied conversation, never evaluation labels.
    retrieval_query = question
    if route:
        # A new question must not inherit any previous subject, even via a rewritten query.
        retrieval_query = question if route["relation"] == "new_question" else route["query"]
        # The resolved query is sufficient for generation; old topics/assistant claims stay out.
        question = retrieval_query
        history = []
    elif history:
        rewrite_messages = [
            {"role": "system", "content": "Viết lại câu hỏi cuối thành một truy vấn tra cứu độc lập bằng tiếng Việt. "
             "Dùng lịch sử để xác định thủ tục và các chi tiết người dùng đã sửa. "
             "Không trả lời câu hỏi, không thêm thông tin. Chỉ xuất truy vấn."},
            *history, {"role": "user", "content": question},
        ]
        if len(tokenizer.apply_chat_template(rewrite_messages, tokenize=True, add_generation_prompt=True)) > (
                settings["num_ctx"] - settings["num_predict"] - 256):
            raise ValueError("Lịch sử quá dài so với NUM_CTX")
        retrieval_query, _, _ = ollama_answer(rewrite_messages, settings)
    retrieval_started = time.perf_counter()
    hits = retriever.search(retrieval_query, settings["top_k"])
    retrieval_s = time.perf_counter() - retrieval_started
    structured = structured or routing_enabled
    messages, used, tokens = build_messages(
        question, hits, tokenizer, settings["num_ctx"], settings["num_predict"], settings["max_chunk_tokens"],
        history=history, structured=structured, evidence_check=routing_enabled,
    )
    if routing_enabled and not used:
        result = early_answer("Chưa tìm thấy thông tin trong tài liệu để trả lời câu hỏi này.",
                              "abstain", "no_context", hits=hits, used=used, tokens=tokens, retrieval_s=retrieval_s)
        result["retrieval_query"] = retrieval_query
        return result
    generation_settings = {**settings, "response_format": "json"} if structured else settings
    answer, raw, generation_s = ollama_answer(messages, generation_settings)
    action = evidence = None
    if structured:
        answer, action, evidence = parse_answer(answer, require_evidence=routing_enabled)
    return {
        "prediction": answer,
        "action": action,
        "routing": route,
        "routing_s": routing_s,
        "routing_prompt_tokens_estimated": routing_tokens,
        "raw_routing": routing_raw,
        "evidence_status": evidence,
        "decision_reason": "evidence_assessment" if routing_enabled else "routing_disabled",
        "retrieval_query": retrieval_query,
        "retrieved": [
            {key: h[key] for key in ("row_id", "score", "chunk_id", "source_file", "source_code")} for h in hits
        ],
        "context_used": used,
        "prompt_tokens_estimated": tokens,
        "retrieval_s": retrieval_s,
        "generation_s": generation_s,
        "latency_s": time.perf_counter() - started,
        "raw_ollama": raw,
    }
