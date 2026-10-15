---
name: rag-architecture-review
description: Review RAG architecture boundaries and coupling in ViGovBot. Use for architecture audits or proposed structural changes; do not trigger for a narrow bug fix.
---

# RAG Architecture Review

Trace the requested flow from entry points and configuration through ingestion,
indexing, retrieval/reranking, prompt assembly, generation, API/session handling,
and evaluation. Map data ownership and module boundaries before judging coupling.

Report evidence-backed findings, affected contracts, severity, and the smallest
compatible improvement. Look for duplicated business logic, dependency cycles,
implicit configuration, and boundaries that prevent independent testing. Separate
confirmed source findings from runtime hypotheses.

This is an architecture workflow, not a style review or authorization to refactor.
When the user asks only for review, do not change code. Source inspection alone
does not verify deployed, model, GPU, or production behavior.
