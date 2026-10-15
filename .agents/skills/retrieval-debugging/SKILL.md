---
name: retrieval-debugging
description: Diagnose lexical, semantic, hybrid and reranked retrieval in ViGovBot. Use when retrieved chunks are irrelevant, missing or incorrectly ranked; not for generation-only failures.
---

# Retrieval Debugging

Phân biệt lỗi truy xuất với lỗi sinh.

## Hợp đồng

- Input: Query, top-k chunks có score/metadata, retrieval config và expected evidence nếu có.
- Output: Phân tích từng query: candidate generation, filter, rank/rerank, relevance, failure class và thử nghiệm kế tiếp.

## Quy trình

+1. Tái hiện cùng index/config/query và lưu top-k thô.\n2. Kiểm tra identity, filter, embedding normalization, lexical/semantic contribution và reranker.\n3. So evidence cần thiết với retrieved chunks; nếu context đủ nhưng answer sai, phân loại generation failure.\n4. Chỉ đổi một biến mỗi thử nghiệm và ghi metric trước/sau.

## Ví dụ

Yêu cầu phù hợp: "diagnose a retrieval failure." Thực hiện quy trình trên và báo rõ bằng chứng.

## Giới hạn và kiểm chứng

Không gọi thiếu evidence là generation failure. Không rebuild index hay tải model khi chưa được yêu cầu. Kiểm chứng bằng scenario tương ứng trong
`docs/agent-skills/TEST_REPORT.md`; nếu có script, chạy cả fixture hợp lệ và input lỗi.
