---
name: rag-security-review
description: Review RAG prompt injection, instruction-data separation, retrieval data exposure, document authorization and session isolation. Use for threat modeling or security test design.
---

# RAG Security Review

Define actors, assets, data classification, authorization rules, and trust
boundaries across documents, retrieval, prompt assembly, tools, sessions, and
responses. Review direct and indirect prompt injection, instruction/data
separation, document-level authorization, cross-tenant retrieval, history
isolation, output disclosure, and tool escalation.

For each finding, record evidence, preconditions, affected asset, impact,
confidence, and a prioritized mitigation. Use synthetic documents, identities,
and canaries for tests; classify outcomes as confirmed, potential, or not tested.

Do not exfiltrate real data, execute destructive payloads, probe production, or
cross authorization boundaries without explicit scope and authority.
