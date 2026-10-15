---
name: chatbot-api-testing
description: Test chatbot API contracts, validation, streaming, sessions, context isolation, timeouts and errors. Use for API verification with local or explicitly authorized endpoints.
---

# Chatbot API Testing

Kiểm thử API an toàn và tái lập.

## Hợp đồng

- Input: Endpoint được phép, request schema, auth handling và expected contract.
- Output: Ma trận case, status/schema/stream/session kết quả, latency và lỗi đã lọc secrets.

## Quy trình

+1. Ưu tiên local test client hoặc mock transport.\n2. Kiểm tra valid/invalid payload, error schema, timeout và content type.\n3. Với streaming, kiểm tra frame order, completion và disconnect. Với session, dùng hai identity để kiểm tra isolation.\n4. Redact token/cookie/PII khỏi artifact.

## Ví dụ

Yêu cầu phù hợp: "test the local chatbot API." Thực hiện quy trình trên và báo rõ bằng chứng.

## Giới hạn và kiểm chứng

Không gửi dữ liệu nhạy cảm ra dịch vụ ngoài. Không load-test hoặc gọi production nếu chưa được yêu cầu. Kiểm chứng bằng scenario tương ứng trong
`docs/agent-skills/TEST_REPORT.md`; nếu có script, chạy cả fixture hợp lệ và input lỗi.
