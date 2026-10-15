---
name: chatbot-api-testing
description: Test chatbot API contracts, validation, streaming, sessions, context isolation, timeouts and errors. Use for API verification with local or explicitly authorized endpoints.
---

# Chatbot API Testing

Prefer the local test client or mock transport. Derive a case matrix from the
request/response contract and cover valid payloads, validation failures, status
and error schemas, content type, timeouts, and dependency failures.

For streaming, verify frame order, termination, malformed frames, cancellation,
and disconnect behavior. For conversation state, use at least two synthetic
session identities and verify continuity within one session and isolation across
sessions; include no-answer and multi-turn cases when the API supports them.

Record endpoint class, case, observed status/schema, and measured latency. Redact
tokens, cookies, personal data, and raw private prompts. Do not call production,
send sensitive data externally, or load-test without explicit scope and authority.
