---
name: dataset-validation
description: Validate ViGovBot JSON or JSONL datasets for schema, splits, duplicates, leakage, distributions and conversational edge cases. Use before training or evaluation.
---

# Dataset Validation

Identify the record schema, stable identity, split contract, and single-turn or
multi-turn structure. Run `scripts/validate_dataset.py` for deterministic JSONL,
exact-duplicate, and cross-split checks; use additional analysis only when the
dataset schema requires it.

Report schema errors, within-split duplicates, cross-split leakage, distributions,
and representative records. When fields exist, cover domain, difficulty, action,
answer/no-answer, clarify, typo, ambiguity, premise correction, and conversation
history. State the method and threshold for near-duplicate checks and label their
results as candidates rather than confirmed duplicates.

Do not rewrite, delete, or rebalance source data unless requested. Preserve sample
identity so later training and evaluation reports can be traced to the same rows.
