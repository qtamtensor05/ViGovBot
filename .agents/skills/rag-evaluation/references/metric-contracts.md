# Hợp đồng metric RAG

## Retrieval

- `Precision@K = relevant retrieved in top K / K` (hoặc số item thực trả về nếu
  benchmark khai báo như vậy); luôn ghi quy ước denominator.
- `Recall@K = relevant retrieved in top K / total known relevant`; không tính nếu
  không biết tổng relevant.
- `MRR = mean(1 / rank of first relevant)`; query không có relevant retrieved có
  reciprocal rank 0, còn query không có relevance judgment phải loại/đánh dấu.
- `nDCG@K = DCG@K / IDCG@K`; ghi rõ gain, discount và relevance binary/graded.

## Generation và hành vi hội thoại

- EM và token F1 cần normalization được công bố. BLEU/ROUGE/BERTScore đo mức
  tương đồng, không tự chứng minh factuality hay groundedness.
- Tách single-turn, multi-turn, answer, partial, clarify, abstain/no-answer và
  premise-correction khi contract dữ liệu có các cohort này.
- BERTScore chỉ chạy khi dependency/model khả dụng; ghi model, device và batch.

## Groundedness và hiệu năng

- Groundedness/faithfulness cần evidence span hoặc evaluator có tên, version,
  prompt và sample identity. Không thay judgment thiếu bằng similarity.
- Latency phải nêu điểm bắt đầu/kết thúc và percentile; throughput phải nêu
  concurrency, duration và warm-up. Resource metrics cần nguồn đo và interval.
- Token/cost chỉ lấy từ provider telemetry và pricing có timestamp.

Mọi metric thiếu input hoặc dependency được báo `null`/`unavailable`, không thay
bằng 0. Mỗi bảng phải có sample size và lý do loại mẫu.
