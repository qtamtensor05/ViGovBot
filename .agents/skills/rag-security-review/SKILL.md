---
name: rag-security-review
description: Review RAG prompt injection, instruction-data separation, retrieval data exposure, document authorization and session isolation. Use for threat modeling or security test design.
---

# RAG Security Review

Threat-model và tạo test có thể chạy.

## Hợp đồng

- Input: Trust boundaries, data classification, access model, prompt/context assembly và API/session flow.
- Output: Finding có evidence, attack precondition, impact, executable safe test và mitigation ưu tiên.

## Quy trình

+1. Xác định actor, asset, trust boundary và quyền thực tế.\n2. Kiểm tra direct/indirect prompt injection, context delimiting, cross-tenant retrieval và history isolation.\n3. Thiết kế canary/synthetic test không chứa dữ liệu thật.\n4. Phân loại confirmed/potential/not tested; không khai thác ngoài phạm vi.

## Ví dụ

Yêu cầu phù hợp: "review RAG security risks." Thực hiện quy trình trên và báo rõ bằng chứng.

## Giới hạn và kiểm chứng

Không exfiltrate dữ liệu, không thử production hoặc destructive payload khi chưa được phép. Kiểm chứng bằng scenario tương ứng trong
`docs/agent-skills/TEST_REPORT.md`; nếu có script, chạy cả fixture hợp lệ và input lỗi.
