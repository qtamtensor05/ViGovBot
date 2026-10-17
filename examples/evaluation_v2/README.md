# Evaluation Run v2 — Vigov

Files:
- `evaluation_run_v2.schema.json`: strict JSON Schema 2020-12 for individual run/case results.
- `evaluation_run_v2.example.jsonl`: TWO real Golden test cases with **no fabricated predictions or scores** (answerable and unanswerable).
- `metrics_config_v2.json`: scorer configuration/policy starter. Pin model revisions before production.
- `golden_compatibility_report.json`: dataset structure audit.

## Compatibility
All 3,850 cases have `ground_truth.expected_answer`; scoring EM, token-F1, ROUGE and BERTScore needs actual `generation_output.actual_output`. Unanswerable test cases intentionally have empty context/facts/citations; source-scoped abstention must be scored separately.

Ground truth does **not** provide model predictions, inference traces, retrieval ranks, judge ratings, GPU telemetry or human annotations. Thus full metric computation is **not automatic** from the Golden file.

## Fair evaluation
Hold prompts/config/references and split fixed across architectures. For Base/FT, retrieval-only metrics = null with `metric_details.<metric>.status=not_applicable`. Do not treat null as zero. For RAG compute retrieval metrics only with actual retrieved IDs plus reliable relevance mapping. Do not leak golden context, expected route, labels or source_code filters unless those filters would be available in production for all relevant systems.

`evaluation_run_results.jsonl` v1 was a **single pretty-printed JSON template despite the .jsonl extension**, not a per-line JSONL run result. V2 example contains two actual JSONL records, one per line.

## Recommended implementation
Capture trace once; score repeatably and version scorers; save macro and slice reports separately. For BERTScore pin multilingual model/version/layer/IDF, for word-token F1 use consistent Vietnamese segmentation. For unanswerable, report abstention and answerable utility separately. Pairwise/CI and judge-human agreement are aggregate statistics, not single-case scores.
