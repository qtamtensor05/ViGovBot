"""Small CPU intent classifier and versioned artifact helpers for RAG routing."""

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path


SCHEMA_VERSION = 1
DIRECT_LABELS = {"in_scope.new_question", "out_of_scope.new_question"}
VALID_LABELS = {
    "in_scope.new_question", "in_scope.follow_up", "in_scope.ambiguous",
    "mixed.new_question", "mixed.follow_up", "mixed.ambiguous",
    "out_of_scope.new_question",
}
DEFAULT_THRESHOLDS = {
    "in_scope.new_question": 0.92,
    "out_of_scope.new_question": 0.98,
}


class ClassifierArtifactError(RuntimeError):
    """The optional classifier cannot be trusted, so routing must fall back."""


@dataclass(frozen=True)
class IntentPrediction:
    label: str
    confidence: float
    threshold: float | None
    accepted: bool
    latency_s: float

    @property
    def scope(self):
        return self.label.split(".", 1)[0]

    @property
    def relation(self):
        return self.label.split(".", 1)[1]

    def diagnostics(self):
        return {
            "backend": "fasttext",
            "label": self.label,
            "scope": self.scope,
            "relation": self.relation,
            "confidence": self.confidence,
            "threshold": self.threshold,
            "accepted": self.accepted,
            "latency_s": self.latency_s,
        }


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def classifier_text(question, history):
    """Serialize only bounded conversational text; labels never enter the model input."""
    messages = history[-6:] if history else []
    parts = ["[HISTORY]"]
    for message in messages:
        content = " ".join(str(message.get("content", "")).split())[:1000]
        parts.append(f"{message.get('role', 'unknown')}: {content}")
    parts.extend(("[QUESTION]", " ".join(question.split())))
    return "\n".join(parts)


def load_metadata(metadata_path, model_path):
    metadata_path, model_path = Path(metadata_path), Path(model_path)
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ClassifierArtifactError(f"Invalid classifier metadata: {exc}") from exc
    required = {"schema_version", "model_sha256", "labels", "thresholds", "dataset_sha256"}
    if not isinstance(metadata, dict) or not required.issubset(metadata):
        raise ClassifierArtifactError("Classifier metadata is missing required fields")
    if metadata["schema_version"] != SCHEMA_VERSION:
        raise ClassifierArtifactError("Unsupported classifier artifact schema")
    labels = set(metadata["labels"])
    if labels != VALID_LABELS:
        raise ClassifierArtifactError("Classifier taxonomy is incomplete or invalid")
    thresholds = metadata["thresholds"]
    if any(label not in thresholds or not 0 < thresholds[label] <= 1 for label in DIRECT_LABELS):
        raise ClassifierArtifactError("Classifier direct-route thresholds are invalid")
    if not model_path.is_file() or _sha256(model_path) != metadata["model_sha256"]:
        raise ClassifierArtifactError("Classifier model is missing or does not match its SHA-256")
    return metadata


class FastTextIntentClassifier:
    def __init__(self, model_path, metadata_path):
        self.model_path = Path(model_path)
        self.metadata = load_metadata(metadata_path, model_path)
        try:
            import fasttext
        except ImportError as exc:
            raise ClassifierArtifactError("Install the 'routing' extra to use FastText") from exc
        try:
            self.model = fasttext.load_model(str(self.model_path))
        except (OSError, ValueError) as exc:
            raise ClassifierArtifactError(f"Cannot load classifier model: {exc}") from exc

    def predict(self, question, history):
        started = time.perf_counter()
        text = classifier_text(question, history).replace("\n", " ")
        if hasattr(self.model, "f"):
            # fasttext 0.9.3's Python wrapper uses np.array(copy=False), which
            # raises on NumPy 2.x. The native API returns the same (prob, label)
            # pairs without introducing a NumPy compatibility dependency.
            pairs = self.model.f.predict(text + "\n", 1, 0.0, "strict")
            probabilities = [pair[0] for pair in pairs]
            labels = [pair[1] for pair in pairs]
        else:
            labels, probabilities = self.model.predict(text, k=1)
        if not labels or not probabilities:
            raise ClassifierArtifactError("Classifier returned no prediction")
        label = labels[0].removeprefix("__label__")
        if label not in set(self.metadata["labels"]):
            raise ClassifierArtifactError(f"Classifier returned unknown label: {label}")
        confidence = float(probabilities[0])
        if not math.isfinite(confidence) or not 0 <= confidence <= 1:
            raise ClassifierArtifactError("Classifier returned invalid confidence")
        threshold = self.metadata["thresholds"].get(label)
        return IntentPrediction(
            label=label,
            confidence=confidence,
            threshold=threshold,
            accepted=label in DIRECT_LABELS and threshold is not None and confidence >= threshold,
            latency_s=time.perf_counter() - started,
        )


@lru_cache(maxsize=4)
def get_classifier(model_path, metadata_path):
    return FastTextIntentClassifier(model_path, metadata_path)


def read_dataset(path):
    records = []
    ids = set()
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at line {line_number}: {exc}") from exc
            required = {"id", "split", "group", "question", "history", "scope", "relation"}
            if not isinstance(row, dict) or not required.issubset(row):
                raise ValueError(f"Line {line_number} is missing routing dataset fields")
            label = f"{row['scope']}.{row['relation']}"
            if label not in VALID_LABELS or row["split"] not in {"train", "validation", "test"}:
                raise ValueError(f"Line {line_number} has an invalid label or split")
            if not isinstance(row["question"], str) or not row["question"].strip() or not isinstance(row["history"], list):
                raise ValueError(f"Line {line_number} has invalid question/history")
            if not isinstance(row["id"], str) or not row["id"] or row["id"] in ids:
                raise ValueError(f"Line {line_number} has an invalid or duplicate id")
            ids.add(row["id"])
            if any(not isinstance(message, dict) or message.get("role") not in {"user", "assistant"}
                   or not isinstance(message.get("content"), str) or not message["content"].strip()
                   for message in row["history"]):
                raise ValueError(f"Line {line_number} has invalid history messages")
            row["label"] = label
            records.append(row)
    if not records:
        raise ValueError("Routing dataset is empty")
    groups = {}
    for row in records:
        previous = groups.setdefault(str(row["group"]), row["split"])
        if previous != row["split"]:
            raise ValueError(f"Group leakage across splits: {row['group']}")
    return records


def train_artifact(dataset_path, output_dir, *, epoch=25, lr=0.3, word_ngrams=2,
                   thresholds=None):
    try:
        import fasttext
    except ImportError as exc:
        raise RuntimeError("Install the 'routing' extra before training") from exc
    dataset_path, output_dir = Path(dataset_path), Path(output_dir)
    rows = read_dataset(dataset_path)
    train_rows = [row for row in rows if row["split"] == "train"]
    validation_rows = [row for row in rows if row["split"] == "validation"]
    test_rows = [row for row in rows if row["split"] == "test"]
    if not train_rows or not validation_rows or not test_rows:
        raise ValueError("Routing dataset requires non-empty train, validation and test splits")
    train_labels = {row["label"] for row in train_rows}
    if train_labels != VALID_LABELS:
        raise ValueError("Training split must include every routing taxonomy label")
    output_dir.mkdir(parents=True, exist_ok=True)
    training_file = output_dir / "fasttext-training.txt"
    training_file.write_text("\n".join(
        f"__label__{row['label']} {classifier_text(row['question'], row['history']).replace(chr(10), ' ')}"
        for row in train_rows
    ) + "\n", encoding="utf-8")
    model = fasttext.train_supervised(
        input=str(training_file), epoch=epoch, lr=lr, wordNgrams=word_ngrams,
        dim=32, bucket=50000, minCount=1, minn=2, maxn=5, loss="softmax", thread=1,
    )
    model_path = output_dir / "intent-router.bin"
    model.save_model(str(model_path))
    training_file.unlink()
    metadata = {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model_sha256": _sha256(model_path),
        "dataset_sha256": _sha256(dataset_path),
        "labels": sorted(train_labels),
        "thresholds": {**DEFAULT_THRESHOLDS, **(thresholds or {})},
        "training": {"epoch": epoch, "lr": lr, "word_ngrams": word_ngrams,
                     "dim": 32, "bucket": 50000, "min_count": 1},
        "split_counts": {name: sum(row["split"] == name for row in rows)
                         for name in ("train", "validation", "test")},
    }
    metadata_path = output_dir / "intent-router.metadata.json"
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return model_path, metadata_path


def evaluate_artifact(dataset_path, model_path, metadata_path, split="test"):
    rows = [row for row in read_dataset(dataset_path) if row["split"] == split]
    if not rows:
        raise ValueError(f"Routing dataset has no {split} rows")
    classifier = FastTextIntentClassifier(model_path, metadata_path)
    labels = sorted({row["label"] for row in rows})
    confusion = {actual: {predicted: 0 for predicted in labels} for actual in labels}
    fallback = 0
    latencies = []
    for row in rows:
        prediction = classifier.predict(row["question"], row["history"])
        confusion.setdefault(row["label"], {}).setdefault(prediction.label, 0)
        confusion[row["label"]][prediction.label] += 1
        fallback += not prediction.accepted
        latencies.append(prediction.latency_s)
    recalls, f1s = {}, []
    for label in labels:
        tp = confusion.get(label, {}).get(label, 0)
        actual = sum(confusion.get(label, {}).values())
        predicted = sum(row.get(label, 0) for row in confusion.values())
        recall = tp / actual if actual else 0.0
        precision = tp / predicted if predicted else 0.0
        recalls[label] = recall
        f1s.append(2 * precision * recall / (precision + recall) if precision + recall else 0.0)
    scope_counts = {scope: {"actual": 0, "correct": 0} for scope in ("in_scope", "mixed", "out_of_scope")}
    for actual_label, predictions in confusion.items():
        actual_scope = actual_label.split(".", 1)[0]
        scope_counts[actual_scope]["actual"] += sum(predictions.values())
        scope_counts[actual_scope]["correct"] += sum(
            count for predicted_label, count in predictions.items()
            if predicted_label.split(".", 1)[0] == actual_scope)
    scope_recall = {scope: values["correct"] / values["actual"] if values["actual"] else None
                    for scope, values in scope_counts.items()}
    ordered = sorted(latencies)
    def percentile(p):
        return ordered[max(0, math.ceil(p * len(ordered)) - 1)]
    macro_f1 = sum(f1s) / len(f1s)
    result = {
        "split": split, "records": len(rows), "macro_f1": macro_f1,
        "recall": recalls, "scope_recall": scope_recall,
        "fallback_rate": fallback / len(rows), "latency_s": {"p50": percentile(0.5), "p95": percentile(0.95)},
        "confusion_matrix": confusion,
        "estimated_hybrid_qwen_call_reduction": 1 - fallback / len(rows),
    }
    result["quality_gates"] = {
        "macro_f1_gte_0_95": macro_f1 >= 0.95,
        "in_scope_recall_gte_0_98": (scope_recall["in_scope"] or 0) >= 0.98,
        "out_of_scope_recall_gte_0_95": (scope_recall["out_of_scope"] or 0) >= 0.95,
        "estimated_qwen_call_reduction_gte_0_70": 1 - fallback / len(rows) >= 0.70,
    }
    result["quality_gates_passed"] = all(result["quality_gates"].values())
    return result
