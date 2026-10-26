"""Lazy cross-encoder reranking for the online RAG pipeline."""

from __future__ import annotations

from functools import lru_cache
import threading


class CrossEncoderReranker:
    def __init__(self, model_name, device="cpu", batch_size=20, max_length=512):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        if device == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("CUDA reranker requested but torch.cuda.is_available() is false")
        self.device = device
        self.batch_size = batch_size
        self.max_length = max_length
        self._torch = torch
        self._tokenizer = AutoTokenizer.from_pretrained(model_name)
        dtype = torch.float16 if device == "cuda" else torch.float32
        self._model = AutoModelForSequenceClassification.from_pretrained(model_name, dtype=dtype)
        self._model.to(device)
        self._model.eval()
        self._lock = threading.Lock()
        self.metadata = {
            "model": model_name,
            "device": device,
            "dtype": str(dtype).replace("torch.", ""),
            "batch_size": batch_size,
            "max_length": max_length,
            "parameters": sum(parameter.numel() for parameter in self._model.parameters()),
        }

    def score(self, pairs):
        scores = []
        with self._lock:
            for start in range(0, len(pairs), self.batch_size):
                batch = pairs[start:start + self.batch_size]
                inputs = self._tokenizer(
                    batch, padding=True, truncation=True, max_length=self.max_length,
                    return_tensors="pt",
                )
                inputs = {key: value.to(self.device) for key, value in inputs.items()}
                with self._torch.inference_mode():
                    logits = self._model(**inputs, return_dict=True).logits.view(-1).float()
                scores.extend(float(value) for value in logits.cpu().tolist())
        return scores


@lru_cache(maxsize=4)
def load_reranker(model_name, device, batch_size, max_length):
    """Load one immutable reranker per configuration and reuse it across requests."""
    return CrossEncoderReranker(model_name, device, batch_size, max_length)


def rerank_hits(question, hits, settings):
    """Rerank candidate hits and return the configured final context depth."""
    config = settings.get("reranker") or {}
    if not config.get("enabled", False):
        return list(hits[:settings["top_k"]])
    reranker = load_reranker(
        config["model"], config.get("device", "cpu"),
        config.get("batch_size", 20), config.get("max_length", 512),
    )
    pairs = [(question, hit.get("text_content", "")) for hit in hits]
    scores = reranker.score(pairs)
    if len(scores) != len(hits):
        raise ValueError("Reranker returned a score count different from candidate count")
    from vigovbot.retrieval.retriever import preferred_section_types

    preferred_sections = preferred_section_types(question)
    ranked = sorted(
        ((hit, float(score), rank) for rank, (hit, score) in enumerate(zip(hits, scores), 1)),
        key=lambda item: (
            0 if item[0].get("section_type") in preferred_sections else 1,
            -item[1], item[2],
        ),
    )
    return [
        {
            **hit,
            "faiss_rank": faiss_rank,
            "faiss_score": hit.get("score"),
            "reranker_score": score,
            "rerank_rank": rerank_rank,
        }
        for rerank_rank, (hit, score, faiss_rank) in enumerate(ranked[:settings["top_k"]], 1)
    ]
