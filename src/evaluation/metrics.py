"""Answer metrics consistent with the original baseline notebook."""
import re
import unicodedata

def normalize_answer(text: str) -> str:
    if text is None:
        return ""

    text = unicodedata.normalize("NFC", str(text)).lower().strip()
    text = re.sub(r'[“”"`]', "", text)
    text = re.sub(r"[.,;:!?()\[\]{}]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def exact_match(prediction: str, reference: str) -> int:
    return int(str(prediction).strip() == str(reference).strip())

def normalized_accuracy(prediction: str, reference: str) -> int:
    return int(
        normalize_answer(prediction) ==
        normalize_answer(reference)
    )

from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction

smooth = SmoothingFunction().method1

def bleu_score(prediction: str, reference: str) -> float:
    pred_tokens = normalize_answer(prediction).split()
    ref_tokens = normalize_answer(reference).split()

    if not pred_tokens or not ref_tokens:
        return 0.0

    # BLEU-4 với smoothing để tránh quá nhiều case bằng 0 ở câu ngắn.
    return float(
        sentence_bleu(
            [ref_tokens],
            pred_tokens,
            weights=(0.25, 0.25, 0.25, 0.25),
            smoothing_function=smooth,
        )
    )

from rouge_score import rouge_scorer

rouge = rouge_scorer.RougeScorer(
    ["rouge1", "rouge2", "rougeL"],
    use_stemmer=False,
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