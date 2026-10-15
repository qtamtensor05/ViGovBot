# Hợp đồng metric RAG

- Precision@K = số item relevant trong top K / K; Recall@K cần tổng relevant.
- Hit@K là 1 nếu có ít nhất một relevant item; MRR dùng rank relevant đầu tiên.
- nDCG@K cần graded relevance hoặc binary relevance được khai báo.
- EM và token F1 cần normalization công khai. BLEU/ROUGE/BERTScore là độ tương
  đồng chuỗi/ngữ nghĩa, không tự chứng minh factual correctness.
- Context metrics và faithfulness cần evidence/judge cùng version, prompt và
  sample identity. Báo null khi thiếu input, không thay bằng 0.
- Latency phải nêu boundary đo; throughput phải nêu concurrency và duration.
  Token/cost chỉ tính từ usage/provider pricing có timestamp.
