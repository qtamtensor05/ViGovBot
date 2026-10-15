---
name: usage-benchmark
description: Design and analyze controlled A/B benchmarks comparing Codex workflows with and without custom skills. Use only with real comparable runs and provider telemetry, never synthetic savings claims.
---

# Usage Benchmark

Compare baseline and skills on the same task set, repository revision, model,
reasoning effort, environment, tool permissions, and acceptance rubric. Randomize
or counterbalance condition order and retain raw run records so invalid or rerun
cases remain auditable.

Collect provider-reported input, output, and cached tokens when available, plus
elapsed time, turns, reruns/rework, test outcomes, and rubric completion. Use
`scripts/summarize_benchmark.py` only after confirming runs are comparable.

Do not replace token telemetry with text length, invent missing runs, or claim
savings from a methodology document. Report sample size, paired differences,
missing fields, invalid runs, uncertainty, and conclusions bounded by the data.
Do not start paid or externally mutating benchmark runs without explicit scope
and authority.
