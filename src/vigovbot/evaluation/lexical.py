"""Shared lexical backends; each report declares its aggregation and score scale."""

from vigovbot.utils.text import NORMALIZATION_VERSION, word_tokens

METRIC_CONTRACT = {
    "version": "vi-lexical-v1",
    "normalization": NORMALIZATION_VERSION,
    "bleu": "SacreBLEU; tokenize=none; smooth_method=exp; effective_order=True; scale=0..100",
    "aggregation": "corpus BLEU; macro per-example ROUGE and normalized EM",
    "rouge": "rouge-score; Unicode word tokens; no stemming",
}


def bleu_metric():
    from sacrebleu.metrics import BLEU
    return BLEU(tokenize="none", smooth_method="exp", effective_order=True)


class VietnameseTokenizer:
    def tokenize(self, text):
        return word_tokens(text)
