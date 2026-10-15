---
name: minimal-diff-development
description: Implement the smallest coherent code change that satisfies a request while preserving contracts and unrelated work. Use for scoped fixes and features; not for an explicitly requested broad refactor.
---

# Minimal Diff Development

Inspect current Git state and the callers, tests, and public contracts affected by
the request. Implement the smallest coherent change that fixes the root cause,
preserving unrelated user work and existing API, configuration, and path contracts
unless the request requires changing them.

Avoid unrelated formatting, opportunistic refactors, and generated artifacts.
Expand scope only when evidence shows the root cause crosses a boundary; explain
that expansion in the handoff. Before completion, review the content diff, diff
stat, and untracked files, then run verification proportional to the behavior
changed.

Minimality is not a reason to retain a known-bad workaround or skip relevant tests.
