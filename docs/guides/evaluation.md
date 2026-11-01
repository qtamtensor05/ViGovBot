# Đánh giá và báo cáo QLoRA

Test độc lập không tham gia training, Early Stopping hoặc chọn checkpoint.

```powershell
python -m vigovbot.training.evaluate --run_dir outputs/qlora/<run-id> --split test
vigov report plots --run-id <run-id>
vigov report build --run-id <run-id>
```

Evaluation lưu prediction từng mẫu trong `predictions/` và metric tổng hợp trong
`metrics/`. Report chỉ đọc giá trị persisted; measurement không có được đánh dấu
`unavailable`, không được nội suy hoặc bịa. Plot giữ marker best checkpoint và
Early Stopping khi artifact thực tế có các trường tương ứng.

Các metric được giữ gồm loss/perplexity theo target token, EM/normalized EM,
precision/recall/F1, ROUGE, BLEU, chrF, so sánh baseline/fine-tuned và prediction
từng mẫu. Đánh giá RAG và các mô hình trên Golden v3 được thực hiện qua quy trình [QA/RAG evaluation](qa-rag-evaluation.md).
