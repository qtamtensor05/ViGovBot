---
name: rag-evaluation
description: Evaluate retrieval, generation, RAG quality and performance with explicit metric contracts. Use for benchmark design, scoring or interpretation; do not collapse unrelated metrics into one score.
---

# RAG Evaluation

Define the evaluation unit, sample identity, denominator, configuration, and
available judgments before scoring. Read
[metric contracts](references/metric-contracts.md) whenever choosing or
interpreting metrics.

Report retrieval, generation, groundedness, and performance separately:

- retrieval: Precision@K, Recall@K, MRR, and nDCG@K only with suitable relevance
  judgments;
- generation: normalized EM/token F1 and optional BLEU, ROUGE, or BERTScore when
  their dependencies and valid references are available;
- groundedness: evidence-supported claims or judge-based measures with the judge,
  prompt, version, and provenance recorded;
- performance: measured latency boundaries, throughput/concurrency, resource use,
  token usage, and dated cost inputs.

Keep single-turn, multi-turn, and no-answer/clarification cohorts identifiable.
Use `null`/`unavailable` for missing inputs or dependencies, never zero or an
estimate. Do not combine unrelated metrics into one score or treat similarity as
factual accuracy.
