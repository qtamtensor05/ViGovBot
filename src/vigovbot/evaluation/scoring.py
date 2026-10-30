"""Supplemental offline metrics for immutable Evaluation v3.2 predictions."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from vigovbot.artifacts import file_hash
from vigovbot.utils.text import NORMALIZATION_VERSION, normalize_vietnamese

from .records import canonical_architecture, load_golden, load_predictions


SCORER_VERSION = "2"


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _tokens(value: str) -> list[str]:
    normalized = normalize_vietnamese(value)
    return normalized.split() if normalized else []


def _distance(left: list[str], right: list[str]) -> int:
    row = list(range(len(right) + 1))
    for left_index, left_value in enumerate(left, 1):
        previous, row[0] = row[0], left_index
        for right_index, right_value in enumerate(right, 1):
            saved = row[right_index]
            row[right_index] = min(
                row[right_index] + 1,
                row[right_index - 1] + 1,
                previous + (left_value != right_value),
            )
            previous = saved
    return row[-1]


def _error_rate(prediction: str, reference: str, *, words: bool) -> float:
    left = _tokens(prediction) if words else list(normalize_vietnamese(prediction))
    right = _tokens(reference) if words else list(normalize_vietnamese(reference))
    return _distance(left, right) / len(right) if right else float(bool(left))


def _average_precision_at_5(retrieved: list[str], relevant: list[str]) -> float:
    relevant_set = set(relevant)
    if not relevant_set:
        raise ValueError("MAP@5 requires at least one relevant ID")
    hits = 0
    precision_sum = 0.0
    for rank, chunk_id in enumerate(retrieved[:5], 1):
        if chunk_id in relevant_set:
            hits += 1
            precision_sum += hits / rank
    return precision_sum / min(5, len(relevant_set))


def _lexical_case(prediction: str, reference: str) -> dict:
    import sacrebleu

    return {
        "chrf": sacrebleu.sentence_chrf(prediction, [reference]).score,
        "chrf_pp": sacrebleu.sentence_chrf(prediction, [reference], word_order=2).score,
        "sacrebleu": sacrebleu.sentence_bleu(prediction, [reference], tokenize="none").score,
        "character_error_rate": _error_rate(prediction, reference, words=False),
        "word_error_rate": _error_rate(prediction, reference, words=True),
    }


def meteor_vi(prediction, reference):
    """METEOR exact-token variant: no English stemmer/WordNet for Vietnamese."""
    from nltk.translate.meteor_score import single_meteor_score
    class IdentityStemmer:
        def stem(self, word):
            return word
    class NoSynonyms:
        def synsets(self, word):
            return []
    return single_meteor_score(_tokens(reference), _tokens(prediction),
                               stemmer=IdentityStemmer(), wordnet=NoSynonyms())


def _bertscore(predictions: list[str], references: list[str], *, model: str, device: str, batch_size: int,
               score_fn=None) -> tuple[dict, list[dict]]:
    if batch_size < 1:
        raise ValueError("bert_batch_size must be positive")
    if score_fn is None:
        from bert_score import score as score_fn

    precision, recall, f1 = score_fn(
        predictions, references, model_type=model, device=device, batch_size=batch_size,
        lang="vi", verbose=True,
    )
    values = [
        {"bertscore_precision": float(p), "bertscore_recall": float(r), "bertscore_f1": float(f)}
        for p, r, f in zip(precision, recall, f1)
    ]
    return ({key: _mean([item[key] for item in values]) for key in values[0]}, values)


def score_supplemental(*, dataset: Path, split: str, predictions: Path, architecture: str, output: Path,
                     bertscore: bool = False, bert_model: str = "xlm-roberta-large", bert_device: str = "cpu",
                     bert_batch_size: int = 8, bert_score_fn=None, extended=False,
                     embedding_model="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                     allow_partial=False) -> dict:
    """Score cached v3.2 predictions without model inference or modifying exported results."""
    architecture = canonical_architecture(architecture)
    golden_path, golden_rows = load_golden(Path(dataset), split)
    prediction_rows, prediction_path = load_predictions(Path(predictions))
    golden_ids = {row["test_id"] for row in golden_rows}
    extra_ids = set(prediction_rows) - golden_ids
    missing_ids = golden_ids - set(prediction_rows)
    if extra_ids or (missing_ids and not allow_partial):
        raise ValueError(f"Predictions must cover the Golden split exactly; extra={len(extra_ids)}, missing={len(missing_ids)}")
    expected = len(golden_rows)
    if allow_partial:
        golden_rows = [row for row in golden_rows if row["test_id"] in prediction_rows]
        if not golden_rows:
            raise ValueError("Partial predictions do not match any Golden case")

    ordered_predictions = []
    references = []
    per_case = []
    for golden in golden_rows:
        prediction = prediction_rows[golden["test_id"]]
        answer = (prediction.get("execution", {}).get("generation") or {}).get("actual_output")
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError(f"Prediction {golden['test_id']} has no answer")
        ordered_predictions.append(answer)
        references.append(golden["ground_truth"]["expected_answer"])
        per_case.append({"test_id": golden["test_id"], **_lexical_case(
            answer, golden["ground_truth"]["expected_answer"]
        )})

    lexical_keys = ("chrf", "chrf_pp", "sacrebleu", "character_error_rate", "word_error_rate")
    lexical = {key: _mean([row[key] for row in per_case]) for key in lexical_keys}
    details = {
        key: {"status": "computed", "scorer_version": f"offline-v3-supplement-{SCORER_VERSION}"}
        for key in lexical
    }
    retrieval = {"map_at_5": None}
    if architecture in {"rag", "finetuned_rag"}:
        map_rows = []
        for golden in golden_rows:
            relevant = [item for item in golden["ground_truth"].get("ground_truth_context_ids", []) if isinstance(item, str)]
            if not relevant:
                continue
            retrieval = prediction_rows[golden["test_id"]].get("execution", {}).get("retrieval") or {}
            retrieved = [item.get("context_id") for item in retrieval.get("contexts", [])]
            value = _average_precision_at_5([item for item in retrieved if isinstance(item, str)], relevant)
            per_case[golden_rows.index(golden)]["map_at_5"] = value
            map_rows.append(value)
        retrieval["map_at_5"] = _mean(map_rows)
        details["map_at_5"] = {
            "status": "computed", "n": len(map_rows), "denominator": "min(5, known_relevant)",
            "scorer_version": f"offline-v3-supplement-{SCORER_VERSION}",
        }
    else:
        details["map_at_5"] = {"status": "not_applicable", "reason": "Base architecture has no retrieval"}

    if bertscore:
        aggregate, values = _bertscore(
            ordered_predictions, references, model=bert_model, device=bert_device,
            batch_size=bert_batch_size, score_fn=bert_score_fn,
        )
        lexical.update(aggregate)
        for row, value in zip(per_case, values):
            row.update(value)
        for key in aggregate:
            details[key] = {
                "status": "computed", "model": bert_model, "device": bert_device,
                "batch_size": bert_batch_size, "scorer_version": f"offline-v2-supplement-{SCORER_VERSION}",
            }
    else:
        for key in ("bertscore_precision", "bertscore_recall", "bertscore_f1"):
            lexical[key] = None
            details[key] = {"status": "unavailable", "reason": "BERTScore was not requested"}

    for key, reason in {
        "embedding_cosine_similarity": "No configured embedding-judge contract",
        "meteor": "No Vietnamese METEOR contract or resources are configured",
    }.items():
        lexical[key] = None
        details[key] = {"status": "unavailable", "reason": reason}
    if extended:
        from sentence_transformers import SentenceTransformer
        encoder = SentenceTransformer(embedding_model, device=bert_device)
        left = encoder.encode(ordered_predictions, normalize_embeddings=True, batch_size=bert_batch_size)
        right = encoder.encode(references, normalize_embeddings=True, batch_size=bert_batch_size)
        cosine = (left * right).sum(axis=1).tolist()
        meteor = [meteor_vi(p, r) for p, r in zip(ordered_predictions, references)]
        for row, m, c in zip(per_case, meteor, cosine):
            row.update(meteor=float(m), embedding_cosine_similarity=float(c))
        lexical.update(meteor=_mean(meteor), embedding_cosine_similarity=_mean(cosine))
        details["meteor"] = {"status": "computed", "contract": "vi-normalized-exact METEOR, identity stemmer, no synonyms, nltk defaults"}
        details["embedding_cosine_similarity"] = {"status": "computed", "model": embedding_model, "device": bert_device,
                                                   "revision": getattr(encoder[0].auto_model.config, "_commit_hash", None),
                                                   "contract": "L2-normalized sentence embeddings, dot product, macro mean"}

    report = {
        "schema_version": "3.2.0-supplement-1", "architecture": architecture, "split": split,
        "expected": expected, "scored_records": len(golden_rows),
        "prediction_records": len(prediction_rows), "missing_predictions": len(missing_ids),
        "partial": bool(missing_ids),
        "metric_contract": {
            "normalization_version": NORMALIZATION_VERSION,
            "sacrebleu": "macro mean of sentence BLEU, tokenize=none, scale 0-100",
            "chrf": "macro mean of sentence chrF, sacrebleu default configuration, scale 0-100",
            "chrf_pp": "macro mean of sentence chrF++, word_order=2, scale 0-100",
            "character_error_rate": "mean normalized Levenshtein over NFC/casefold characters",
            "word_error_rate": "mean normalized Levenshtein over NFC/casefold whitespace tokens",
            "map_at_5": "binary relevance, retrieved top-5, AP denominator min(5, known relevant)",
        },
        "metrics": {"lexical": lexical, "retrieval": retrieval, "metric_details": details},
        "per_case": per_case,
        "provenance": {
            "golden_dataset": str(golden_path), "golden_sha256": file_hash(golden_path),
            "predictions": str(prediction_path), "predictions_sha256": file_hash(prediction_path),
            "scorer_version": f"offline-v3-supplement-{SCORER_VERSION}",
            "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "inference_performed": False,
        },
    }
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, allow_nan=False)
    return report
