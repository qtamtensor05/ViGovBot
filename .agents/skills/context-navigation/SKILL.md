---
name: context-navigation
description: Locate repository entry points and load only the context needed for a non-trivial task. Use when the implementation is unknown, spans modules, or context size needs deliberate control; skip a known one-file edit.
---

# Context Navigation

Start from the request, the nearest `AGENTS.md`, known entry points, and targeted
`rg --files`/`rg` searches. Follow registrations, imports, callers, configuration,
tests, and documentation only far enough to support the next decision.

Build a small map of entry point → implementation → configuration/data → tests.
Open supporting references only when that branch of the task becomes relevant.
Refresh facts likely to drift and expand scope only when evidence shows a
cross-module effect.

When context or token cost is an explicit constraint, batch independent searches,
limit command output at the source, and retain errors, contracts, and verification
evidence. Report token savings only from provider telemetry; never substitute
character counts or omit required evidence to meet an arbitrary cap.

Avoid generated artifacts, model outputs, datasets, and binary trees unless the
task depends on them. Distinguish compatibility wrappers from canonical code and
stop exploring once the task has enough verified context.
