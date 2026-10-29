"""Local four-head PhoBERT inference; no generative router or keyword fallback.

Input/CLS pooling/thresholds match the supplied training bundle. The classifier
does not extract entities: the adapter resolves them against the current corpus
and signed state, and asks for clarification when field/entity pairing is unknown.
"""
from __future__ import annotations

import json
import math
import re
import time
import unicodedata
from functools import lru_cache
from pathlib import Path
from threading import Lock

from vigovbot.retrieval.retriever import extract_source_codes

LABEL_MAP = {
    "phạm_vi": {"Trong phạm vi": "IN_SCOPE", "Ngoài phạm vi": "OUT_OF_SCOPE",
                "Hỗn hợp phạm vi": "MIXED_SCOPE"},
    "mạch_hội_thoại": {"Câu hỏi mới": "NEW", "Hỏi tiếp": "FOLLOW_UP"},
    "trộn_thủ_tục": {"Không": False, "Có": True},
    "mục_nội_dung": {"Tổng quan": "OVERVIEW", "Trình tự thực hiện": "PROCEDURE",
                     "Cách thức thực hiện": "SUBMISSION_METHOD", "Thành phần hồ sơ": "DOSSIER",
                     "Thời hạn giải quyết": "PROCESSING_TIME", "Cơ quan thực hiện": "AUTHORITY",
                     "Kết quả thực hiện": "RESULT", "Phí, lệ phí": "FEE", "Căn cứ pháp lý": "LEGAL_BASIS",
                     "Điều kiện thực hiện": "ELIGIBILITY", "Mẫu đơn, tờ khai": "FORM"},
}
HEAD_KEYS = dict(zip(LABEL_MAP, ("scope", "flow", "mix", "sections")))
_LOAD_LOCK = Lock()
CATALOG_SCOPE_LOWER = 0.50
CATALOG_SCOPE_UPPER = 0.85


def read_metadata(path):
    meta = json.loads(Path(path).read_text(encoding="utf-8"))
    if set(meta.get("labels", {})) != set(LABEL_MAP) or meta.get("head_keys") != HEAD_KEYS:
        raise ValueError("PhoBERT metadata has incompatible heads")
    for task, mapping in LABEL_MAP.items():
        labels = meta["labels"][task]
        if not isinstance(labels, list) or len(labels) != len(mapping) or set(labels) != set(mapping):
            raise ValueError(f"PhoBERT label mismatch: {task}")
    thresholds = meta.get("thresholds")
    if (not isinstance(thresholds, list) or len(thresholds) != len(LABEL_MAP["mục_nội_dung"])
            or any(type(t) not in (int, float) or not math.isfinite(t) or not 0 <= t <= 1 for t in thresholds)):
        raise ValueError("PhoBERT requires its per-label thresholds")
    if (meta.get("segmenter") != "pyvi" or meta.get("input_mode") != "full"
            or type(meta.get("max_len")) is not int or not 6 <= meta["max_len"] <= 256):
        raise ValueError("Unsupported PhoBERT preprocessing contract")
    return meta


def encode_segments(tokenizer, segments, segmenter, max_len):
    """NFC + whitespace + PyVi; preserve all three segments, truncate longest first."""
    pieces = []
    for text in segments:
        text = " ".join(unicodedata.normalize("NFC", text or "").split())
        pieces.append(tokenizer.encode(segmenter(text), add_special_tokens=False) if text else [])
    if len(pieces) != 3 or max_len < 6:
        raise ValueError("PhoBERT expects question, previous message, selected procedure")
    while sum(map(len, pieces)) > max_len - 6:
        longest = max(range(3), key=lambda i: len(pieces[i]))
        pieces[longest].pop()
    ids = [tokenizer.cls_token_id]
    for i, piece in enumerate(pieces):
        if i:
            ids.extend([tokenizer.sep_token_id, tokenizer.sep_token_id])
        ids.extend(piece)
    return ids + [tokenizer.sep_token_id]


def decode_probabilities(probabilities, meta):
    value, scores = {}, {}
    for task, head in HEAD_KEYS.items():
        labels, probs = meta["labels"][task], probabilities[head]
        if len(probs) != len(labels) or any(not math.isfinite(p) or not 0 <= p <= 1 for p in probs):
            raise ValueError(f"Invalid PhoBERT probabilities: {head}")
        scores[head] = dict(zip(labels, probs))
        if head == "sections":
            value[head] = [LABEL_MAP[task][label] for label, p, t in zip(labels, probs, meta["thresholds"])
                           if p >= t]
        else:
            value[head] = LABEL_MAP[task][labels[max(range(len(probs)), key=probs.__getitem__)]]
    return {**value, "probabilities": scores}


class PhoBERTRouter:
    def __init__(self, checkpoint, threads=2):
        import torch
        from torch import nn
        from transformers import AutoModel, PhobertTokenizer
        from pyvi import ViTokenizer
        from vigovbot.artifacts import file_hash

        root = Path(checkpoint).resolve()
        self.meta = read_metadata(root / "meta.json")
        required = ("meta.json", "heads.pt", "vocab.txt", "bpe.codes", "encoder/config.json",
                    "encoder/model.safetensors")
        for name in required:
            if not (root / name).is_file():
                raise FileNotFoundError(f"PhoBERT checkpoint missing {name}: {root}")
        if threads < 1:
            raise ValueError("PhoBERT CPU thread count must be positive")
        torch.set_num_threads(threads)
        self.tokenizer = PhobertTokenizer(vocab_file=str(root / "vocab.txt"), merges_file=str(root / "bpe.codes"))
        self.encoder = AutoModel.from_pretrained(root / "encoder", local_files_only=True).to("cpu").eval()
        self.heads = nn.ModuleDict({head: nn.Linear(self.encoder.config.hidden_size, len(self.meta["labels"][task]))
                                   for task, head in HEAD_KEYS.items()})
        weights = torch.load(root / "heads.pt", map_location="cpu", weights_only=True)
        normalized = {}
        for key, tensor in weights.items():
            name = key.removeprefix("heads.")
            if name in normalized:
                raise ValueError("Duplicate PhoBERT head key")
            normalized[name] = tensor
        self.heads.load_state_dict(normalized, strict=True)
        self.heads.eval()
        self.segmenter = ViTokenizer.tokenize
        self.identity = {name: file_hash(root / name) for name in required}
        self.lock = Lock()

    def predict(self, question, previous_message="", procedure=""):
        import torch

        with self.lock, torch.inference_mode():
            ids = encode_segments(self.tokenizer, [question, previous_message, procedure], self.segmenter,
                                  self.meta["max_len"])
            tokens = torch.tensor([ids], dtype=torch.long)
            pooled = self.encoder(input_ids=tokens, attention_mask=torch.ones_like(tokens)).last_hidden_state[:, 0]
            probabilities = {}
            for name, head in self.heads.items():
                logits = head(pooled)[0]
                probabilities[name] = (logits.sigmoid() if name == "sections" else logits.softmax(-1)).tolist()
            return {**decode_probabilities(probabilities, self.meta), "encoded_length": len(ids),
                    "thresholds": dict(zip(self.meta["labels"]["mục_nội_dung"], self.meta["thresholds"])),
                    "preprocessing": {k: self.meta[k] for k in ("max_len", "segmenter", "input_mode")}}


@lru_cache(maxsize=1)
def _cached_router(checkpoint, threads):
    return PhoBERTRouter(checkpoint, threads)


def get_router(settings):
    # lru_cache alone can construct duplicate models on concurrent cache misses.
    with _LOAD_LOCK:
        return _cached_router(str(Path(settings["routing_phobert_path"]).resolve()),
                              settings.get("routing_phobert_threads", 2))


def classify_phobert(question, history, state, settings, clarifier):
    started = time.perf_counter()
    router = get_router(settings)
    previous = history[-1]["content"] if history else ""
    selected = state.get("selected", []) if state else []
    procedure = clarifier.catalog[selected[0]]["name"] if len(selected) == 1 else ""
    prediction = router.predict(question, previous, procedure)
    predictions = [prediction]
    adapter_decisions = []
    scope, flow, sections, mixed = (prediction[k] for k in ("scope", "flow", "sections", "mix"))
    identity = clarifier.resolve_identity(question, allow_short_name=True)
    codes = extract_source_codes(question) or identity["codes"]
    confirmation = None
    mixed_scope_fallback_allowed = False
    if scope == "OUT_OF_SCOPE" and codes:
        probability = prediction.get("probabilities", {}).get("scope", {}).get("Ngoài phạm vi")
        curated_alias = identity["source"] == "curated_alias" and len(codes) == 1
        in_override_band = (type(probability) in (int, float) and math.isfinite(probability)
                            and CATALOG_SCOPE_LOWER <= probability < CATALOG_SCOPE_UPPER)
        override = curated_alias or in_override_band
        outcome = ("curated_alias_overrode_out_of_scope" if curated_alias else
                   "catalog_identity_overrode_out_of_scope" if in_override_band else "kept_out_of_scope")
        adapter_decisions.append({
            "type": "catalog_scope_arbitration",
            "outcome": outcome,
            "p_out_of_scope": probability,
            "override_band": [CATALOG_SCOPE_LOWER, CATALOG_SCOPE_UPPER],
        })
        if override:
            # Catalog identity arbitrates only an uncertain model decision. It
            # still does not infer or overwrite section labels.
            scope = "IN_SCOPE"
    if scope == "OUT_OF_SCOPE":
        confirmation = clarifier.confirmation_candidates(question, settings)
    route = dict(scope=scope, conversation=flow, mixed_procedures=mixed, sections=sections,
                 query=question, needs_clarification=False, clarification="", requests=[])

    def finish():
        return route, dict(backend="phobert", attempts=len(predictions), seconds=time.perf_counter()-started,
                           tokens=sum(p["encoded_length"] for p in predictions), errors=[],
                           predictions=predictions, adapter_decisions=adapter_decisions,
                           procedure_confirmation=confirmation,
                           mixed_scope_fallback_allowed=mixed_scope_fallback_allowed,
                           checkpoint=router.identity)

    def clarify(text):
        route.update(needs_clarification=True, clarification=text, requests=[])
        return finish()

    if scope == "OUT_OF_SCOPE":
        route.update(query="", sections=[], mixed_procedures=False)
        return finish()
    if scope == "MIXED_SCOPE":
        # The classifier cannot rewrite away unsupported content. Retain only
        # independently in-scope clauses; no lexical scope/section classifier.
        parts = [p.strip(" ,.") for p in re.split(r"[;\n?!]+|\s+và\s+", question, flags=re.I) if p.strip(" ,.")]
        supported = []
        if 1 < len(parts) <= 8:
            for part in parts[:8]:
                pred = router.predict(part, previous, procedure)
                predictions.append(pred)
                if pred["scope"] == "IN_SCOPE":
                    supported.append((part, pred))
        if len(supported) != 1 or supported[0][1]["mix"]:
            # Rewrite only when PhoBERT found no independently safe clause.
            # Bound the batch like clause classification, and never let the
            # LLM choose among multiple in-scope requests.
            mixed_scope_fallback_allowed = len(parts) <= 8 and not supported
            return clarify("Bạn vui lòng tách rõ phần hỏi về một thủ tục hành chính và nội dung cần tra cứu.")
        question, supported_prediction = supported[0]
        sections = supported_prediction["sections"]
        flow = supported_prediction["flow"]
        mixed = False
        route.update(query=question, sections=sections, conversation=flow, mixed_procedures=False)

    # Global heads have no spans or per-procedure field links. Do not manufacture
    # these links from a union of section labels or reuse one selected procedure.
    if mixed:
        return clarify("Bạn đang hỏi nhiều thủ tục. Vui lòng hỏi riêng từng thủ tục và mục cần xem để tránh ghép nhầm thông tin.")
    if not codes and flow == "FOLLOW_UP":
        if len(selected) != 1:
            return clarify("Bạn đang hỏi tiếp thủ tục nào? Vui lòng nêu tên hoặc mã thủ tục.")
        codes = selected
    # Multiple codes for one mention are candidates, not a multi-procedure request.
    entity = codes[0] if len(codes) == 1 else question
    route["requests"] = [dict(procedure=entity, query=question, sections=sections)]
    return finish()
