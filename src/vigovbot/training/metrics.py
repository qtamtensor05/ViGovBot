from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter


def normalize_vietnamese(text: str) -> str:
    text = unicodedata.normalize("NFC", text).casefold()
    return " ".join(re.sub(r"[^\w\s]", " ", text).split())


def word_tokens(text: str) -> list[str]:
    return normalize_vietnamese(text).split()


def token_prf(prediction: str, reference: str) -> dict[str, float]:
    predicted, expected = Counter(word_tokens(prediction)), Counter(word_tokens(reference))
    overlap = sum((predicted & expected).values())
    precision = overlap / sum(predicted.values()) if predicted else 0.0
    recall = overlap / sum(expected.values()) if expected else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"token_precision": precision, "token_recall": recall, "token_f1": f1}


def perplexity(loss: float) -> float:
    return math.exp(loss) if loss < 709 else float("inf")


def generation_metrics(prediction: str, reference: str) -> dict[str, float | None]:
    values: dict[str, float | None] = {
        "exact_match": float(prediction.strip() == reference.strip()),
        "normalized_exact_match": float(normalize_vietnamese(prediction) == normalize_vietnamese(reference)),
        **token_prf(prediction, reference),
    }
    try:
        from rouge_score import rouge_scorer
        scores = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=False).score(reference, prediction)
        values.update({name: scores[key].fmeasure for name, key in
                       (("rouge_1", "rouge1"), ("rouge_2", "rouge2"), ("rouge_l", "rougeL"))})
    except ImportError:
        values.update({"rouge_1": None, "rouge_2": None, "rouge_l": None})
    try:
        import sacrebleu
        values["bleu"] = sacrebleu.sentence_bleu(prediction, [reference], use_effective_order=True).score
        values["chrf"] = sacrebleu.sentence_chrf(prediction, [reference]).score
    except ImportError:
        values.update({"bleu": None, "chrf": None})
    return values


def aggregate_generation_metrics(rows: list[dict]) -> dict[str, float | None]:
    if not rows:
        return {}
    metric_names = sorted({key for row in rows for key, value in row["metrics"].items()
                           if value is not None and key not in {"bleu", "chrf"}})
    result = {
        key: sum(float(row["metrics"][key]) for row in rows if row["metrics"].get(key) is not None)
        / sum(row["metrics"].get(key) is not None for row in rows)
        for key in metric_names
    }
    try:
        import sacrebleu
        predictions = [row["prediction"] for row in rows]
        references = [[row["reference"] for row in rows]]
        result["bleu"] = sacrebleu.corpus_bleu(predictions, references).score
        result["chrf"] = sacrebleu.corpus_chrf(predictions, references).score
    except ImportError:
        result.update(bleu=None, chrf=None)
    return result


def structured_checks(prediction: str, reference: str) -> dict[str, bool | None]:
    patterns = {
        "procedure_code": r"\b\d+(?:\.\d+){2,}[A-Za-z0-9_-]*\b",
        "monetary_amount": r"\b\d[\d.,]*\s*(?:đồng|vnd)",
        "legal_reference": r"\b(?:luật|nghị định|thông tư|quyết định)\s*(?:số\s*)?[\w./-]+",
        "authority": r"\b(?:bộ|sở|phòng|ban|cục|uỷ ban|cơ quan)\s+[^,.;\n]{2,80}",
    }
    result: dict[str, bool | None] = {}
    for name, pattern in patterns.items():
        expected = {normalize_vietnamese(value) for value in re.findall(pattern, reference, re.IGNORECASE)}
        actual = {normalize_vietnamese(value) for value in re.findall(pattern, prediction, re.IGNORECASE)}
        result[name] = expected <= actual if expected else None
    result["unsupported_claims"] = None  # Requires evidence or a human/grounded judge.
    result["appropriate_private_status_refusal"] = None  # Only meaningful on labeled status queries.
    return result
