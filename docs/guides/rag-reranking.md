# Rerank tài liệu RAG

> Lịch sử: tích hợp reranker trực tiếp vào runtime RAG đã được gỡ. Các cấu hình
> runtime hiện truy xuất FAISS top 5; xem [báo cáo benchmark](../reports/reranker-latency-20261029.md)
> để biết số đo của lần thử trước. Tài liệu dưới đây ghi lại thiết kế đã thử.

## Luồng xử lý

Các profile RAG lấy tối đa 10 ứng viên từ FAISS, chấm từng cặp câu hỏi và đoạn
tài liệu bằng cross-encoder `BAAI/bge-reranker-v2-m3`, rồi chỉ gửi ba đoạn điểm
cao nhất vào bước tạo câu trả lời. Điểm `reranker_score` là logit của model; thứ
hạng cuối được ghi trong `rerank_rank`. Điểm và thứ hạng FAISS ban đầu vẫn được
giữ trong trace.

Model hỗ trợ đa ngôn ngữ, dùng đầu vào query-passage và điểm số cao hơn biểu thị
mức liên quan cao hơn. Cấu hình hiện ghim snapshot
`953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`; snapshot đang tải được ghi trong
metadata reranker của kết quả.

## Cấu hình

Trong `configs/rag/inference*.yaml`:

```yaml
retrieval:
  top_k: 3
  candidate_top_k: 10
  reranker:
    enabled: true
    model: BAAI/bge-reranker-v2-m3
    revision: 953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e
    device: cpu
    batch_size: 4
    max_length: 512
```

Reranker chạy CPU theo mặc định để không tranh VRAM với Qwen/QLoRA. Có thể đặt
`device: cuda` trên máy có CUDA; khi ấy model dùng FP16. Giữ `candidate_top_k`
lớn hơn hoặc bằng `top_k`.

Model được tải lười ở truy vấn RAG đầu tiên vào cache Hugging Face. Docker dùng
volume `huggingface-cache` chung cho web CPU và GPU nên tải một lần có thể được
dùng lại. Nếu tải model hoặc inference lỗi, runtime ghi `reranker.status` là
`fallback` và tiếp tục với ba ứng viên đầu theo thứ tự FAISS. Nếu tắt bằng
`enabled: false`, runtime cũng giữ ba ứng viên đầu nhưng không tải model.

Trace API ghi model, revision, số ứng viên đã chấm, trạng thái và thời gian
`rerank_seconds`. Mỗi nguồn trả về có `faiss_rank`, `faiss_score`,
`reranker_score` và `rerank_rank` khi rerank thành công. Cần chạy retrieval
benchmark trên tập Golden/relevance hiện hành trước khi kết luận reranker cải
thiện chất lượng; việc tích hợp không thay cho đánh giá đó.
