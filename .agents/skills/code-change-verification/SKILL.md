---
name: code-change-verification
description: Select and run proportionate lint, type, unit, integration and regression checks for code changes. Use after implementation or when assessing readiness.
---

# Code Change Verification

Map the current diff to the nearest unit, integration, regression, lint, type,
build, and artifact checks. Run focused checks first; broaden to shared or full
suites when the changed contract or regression risk warrants it. Include
`git diff --check` and inspect the final diff.

Record each command, exit status, and meaningful result. Separate `PASS`, `FAIL`,
`SKIPPED`, and `NOT VERIFIED`, with reasons for checks not run. Validate real
artifacts when behavior depends on them.

Compilation, help output, mocks, source inspection, and a timed-out command do not
prove runtime end-to-end behavior. Keep the final readiness claim within the
environment and behavior actually tested.
