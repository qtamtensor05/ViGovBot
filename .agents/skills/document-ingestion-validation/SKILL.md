---
name: document-ingestion-validation
description: Validate document and PDF ingestion quality across extraction, cleaning, metadata, sections and chunks. Use for pipeline quality audits or Bronze/Silver/Gold comparisons.
---

# Document Ingestion Validation

Establish lineage and record counts across extraction, cleaning, metadata,
sectioning, and chunking stages. For JSONL artifacts, run
`scripts/validate_ingestion.py` and interpret results with
[the quality contract](references/quality-contract.md).

Check empty or lost text, page/section order, required metadata, exact duplicates,
chunk identity and boundaries, and content retention. Report counts, denominators,
stage-to-stage deltas, and representative failures. Treat configurable thresholds
and heuristics as warnings, not facts.

Do not modify source documents or infer OCR accuracy without ground truth. This
workflow validates ingestion artifacts; it does not score retrieval or answers.
