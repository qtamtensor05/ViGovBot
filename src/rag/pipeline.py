from __future__ import annotations
import time
import gc
import json
import logging
from contextlib import contextmanager
from pathlib import Path

from src.embeddings.embedder import load_encoder
from src.evaluation.dataset import load_cases
from src.evaluation.runner import evaluate_cases
from src.ingestion.unified import corpus_identity
from src.llm.llm_client import check_model, unload_model
from src.prompts.prompt_templates import SYSTEM_PROMPT
from src.rag.version import PIPELINE_VERSION
from src.retrieval.retriever import Retriever
from src.utils.helpers import json_hash, ensure_run
from src.vectordb.vector_store import prepare_corpus
from src.prompts.prompt_templates import build_messages
from src.llm.llm_client import ollama_answer

LOG = logging.getLogger(__name__)


def select_cases(config):
    cases = load_cases(config.data.dataset_path, config.data.dataset_zip)
    return cases, cases[:config.evaluation.max_cases] if config.evaluation.max_cases else cases


def source_fingerprint():
    """Phát hiện mã pipeline đổi, kể cả khi quên tăng số phiên bản."""
    root = Path(__file__).resolve().parents[1]
    folders = ("rag", "evaluation", "retrieval", "prompts", "llm", "utils")
    paths = [p for folder in folders for p in (root / folder).glob("*.py")]
    paths += [root / "ingestion/unified.py", root / "embeddings/embedder.py", root / "vectordb/vector_store.py"]
    return json_hash({str(p.relative_to(root)): p.read_text(encoding="utf-8") for p in sorted(paths)})


def manifest_base(config, cases, selected):
    return {"pipeline_version": PIPELINE_VERSION, "source_fingerprint": source_fingerprint(),
            "parameters": config.model_dump(mode="json"), "settings": config.inference_settings(),
            "prompt": SYSTEM_PROMPT, "dataset_sha256": json_hash(cases),
            "selected_ids": [c["id"] for c in selected],
            "corpus_identity": corpus_identity(config.data.unified_source)}


def verify_report_input(config, cases, selected):
    path = config.data.output_dir / "run_manifest.json"
    if not path.exists():
        raise ValueError("Chưa có run_manifest.json; chạy evaluate hoặc run trước")
    actual = json.loads(path.read_text(encoding="utf-8"))
    if any(actual.get(key) != value for key, value in manifest_base(config, cases, selected).items()):
        raise ValueError("Cấu hình/mã nguồn/dữ liệu không khớp kết quả đã lưu; dùng cấu hình gốc để report")


def prepare(config):
    result = prepare_corpus(config.data.unified_source, config.data.cache_dir)
    cases, selected = select_cases(config)
    LOG.info("Corpus: %d vector. Bộ test: %d câu; được chọn: %d", result[2]["count"], len(cases), len(selected))
    return result, cases, selected


@contextmanager
def inference_session(config, paths):
    from transformers import AutoTokenizer
    encoder = retriever = None
    try:
        encoder = load_encoder(**config.embedding.model_dump())
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


def execute(config, command="run"):
    """prepare / smoke / evaluate / report / run; run thực hiện toàn bộ quy trình."""
    if command == "report":
        cases, selected = select_cases(config)
        verify_report_input(config, cases, selected)
        from src.evaluation.report import generate_report
        return generate_report(config, selected)
    paths, cases, selected = prepare(config)
    if command == "prepare":
        return {"count": paths[2]["count"], "database": str(paths[1])}
    model = check_model(config.llm.ollama_url, config.llm.model)
    manifest = {**manifest_base(config, cases, selected), "ollama_digest": model.get("digest")}
    # Kiểm tra trước khi tải BGE-M3, tránh phí tài nguyên nếu cấu hình không khớp.
    if command != "smoke":
        ensure_run(config.data.output_dir, manifest)
    with inference_session(config, paths) as (retriever, tokenizer):
        def answer(question):
            return answer_question(question, retriever, tokenizer, config.inference_settings())
        if command in ("smoke", "run"):
            for case in selected[:config.evaluation.smoke_test_n]:
                result = answer(case["question"]["text"])
                print(json.dumps({"id": case["id"], "question": case["question"]["text"],
                                  "prediction": result["prediction"], "latency_s": result["latency_s"],
                                  "sources": result["retrieved"]}, ensure_ascii=False, indent=2))
        if command == "smoke":
            return {"smoke_cases": min(config.evaluation.smoke_test_n, len(selected))}
        rows = evaluate_cases(selected, config.data.output_dir, manifest, answer)
    LOG.info("Hoàn tất %d/%d câu. Lỗi nếu có: %s", len(rows), len(selected), config.data.output_dir / "errors.jsonl")
    if not rows:
        raise RuntimeError("Không có câu trả lời thành công; kiểm tra errors.jsonl")
    if command == "evaluate":
        return {"completed": len(rows), "requested": len(selected)}
    from src.evaluation.report import generate_report
    return generate_report(config, selected)

def answer_question(question, retriever, tokenizer, settings):
    started = time.perf_counter()
    hits = retriever.search(question, settings["top_k"])
    retrieval_s = time.perf_counter() - started
    messages, used, tokens = build_messages(question, hits, tokenizer, settings["num_ctx"],
                                          settings["num_predict"], settings["max_chunk_tokens"])
    answer, raw, generation_s = ollama_answer(messages, settings)
    return {"prediction": answer, "retrieved": [
                {key: h[key] for key in ("row_id", "score", "chunk_id", "source_file", "source_code")}
                for h in hits], "context_used": used, "prompt_tokens_estimated": tokens,
            "retrieval_s": retrieval_s, "generation_s": generation_s,
            "latency_s": time.perf_counter() - started, "raw_ollama": raw}
