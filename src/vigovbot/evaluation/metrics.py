"""Legacy baseline-notebook metrics. Not comparable to vi-lexical-v1 scores.

Normalization and lexical backends are shared with modern evaluation.
BLEU remains macro sentence BLEU, rescaled to 0..1 for this report.
"""

from vigovbot.evaluation.lexical import VietnameseTokenizer, bleu_metric
from vigovbot.utils.text import normalize_vietnamese
from rouge_score import rouge_scorer

METRIC_CONTRACT_VERSION = "baseline-vi-lexical-v3"


def normalize_answer(text: str) -> str:
    if text is None:
        return ""

    return normalize_vietnamese(str(text))


def exact_match(prediction: str, reference: str) -> int:
    return int(str(prediction).strip() == str(reference).strip())


def normalized_accuracy(prediction: str, reference: str) -> int:
    return int(normalize_answer(prediction) == normalize_answer(reference))


def bleu_score(prediction: str, reference: str) -> float:
    pred_tokens = normalize_vietnamese(prediction).split()
    ref_tokens = normalize_vietnamese(reference).split()

    if not pred_tokens or not ref_tokens:
        return 0.0

    return bleu_metric().sentence_score(" ".join(pred_tokens), [" ".join(ref_tokens)]).score / 100.0


rouge = rouge_scorer.RougeScorer(
    ["rouge1", "rouge2", "rougeL"],
    use_stemmer=False,
    tokenizer=VietnameseTokenizer(),
)


def rouge_scores(prediction: str, reference: str):
    result = rouge.score(
        normalize_answer(reference),
        normalize_answer(prediction),
    )

    return {
        "rouge1_f1": float(result["rouge1"].fmeasure),
        "rouge2_f1": float(result["rouge2"].fmeasure),
        "rougeL_f1": float(result["rougeL"].fmeasure),
    }
