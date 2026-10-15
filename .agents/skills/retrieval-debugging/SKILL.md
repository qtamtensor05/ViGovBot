---
name: retrieval-debugging
description: Diagnose lexical, semantic, hybrid and reranked retrieval in ViGovBot. Use when retrieved chunks are irrelevant, missing or incorrectly ranked; not for generation-only failures.
---

# Retrieval Debugging

Reproduce the same query, index, filters, configuration, and top K, then preserve
raw candidates with scores and metadata. Trace candidate generation through
lexical, semantic, hybrid fusion, filters, and reranking as applicable.

Verify document/chunk identity, embedding/query normalization, score direction,
filter behavior, fusion weights, and reranker inputs. Compare the evidence needed
for the expected answer with retrieved chunks. If sufficient evidence is present
but the answer is wrong, classify the failure as generation rather than retrieval.

Change one variable per experiment and compare the same labeled query set with
appropriate retrieval metrics. Do not rebuild an index or download a model unless
the requested diagnosis requires and authorizes it.
