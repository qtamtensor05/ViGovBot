---
name: rag-evaluation
description: Evaluate retrieval, generation, RAG quality and performance with explicit metric contracts. Use for benchmark design, scoring or interpretation; do not collapse unrelated metrics into one score.
---

# RAG Evaluation

Tính và diễn giải metric đúng điều kiện.

## Hợp đồng

- Input: Prediction/reference records; retrieval judgments; timing/resource measurements; config và sample identity.
- Output: Metric theo nhóm với sample size, dependency, provenance, unavailable values và giới hạn.

## Quy trình

+1. Xác định unit và denominator trước khi tính.\n2. Retrieval: Recall/Precision/Hit/MRR/nDCG@K chỉ khi có relevance labels. Generation: EM/F1/BLEU/ROUGE/BERTScore theo input hợp lệ.\n3. Context Precision/Recall, Faithfulness, Answer Relevancy cần evaluator và provenance rõ.\n4. Latency/throughput/resource/token/cost chỉ báo khi đo được. Đọc `references/metric-contracts.md`.

## Ví dụ

Yêu cầu phù hợp: "evaluate a ViGovBot RAG run." Thực hiện quy trình trên và báo rõ bằng chứng.

## Giới hạn và kiểm chứng

Không gộp metric khác bản chất. Không gọi similarity là factual accuracy; không ước tính token bằng độ dài chuỗi. Kiểm chứng bằng scenario tương ứng trong
`docs/agent-skills/TEST_REPORT.md`; nếu có script, chạy cả fixture hợp lệ và input lỗi.
