# Đánh giá và báo cáo QLoRA

Test độc lập không tham gia training, Early Stopping hoặc chọn checkpoint.

```powershell
vigovbot eva test --run-id <run-id>
vigovbot report plots --run-id <run-id>
vigovbot report build --run-id <run-id>
```

Evaluation lưu prediction từng mẫu trong `predictions/` và metric tổng hợp trong
`metrics/`. Report chỉ đọc giá trị persisted; measurement không có được đánh dấu
`unavailable`, không được nội suy hoặc bịa. Plot giữ marker best checkpoint và
Early Stopping khi artifact thực tế có các trường tương ứng.

Các metric được giữ gồm loss/perplexity theo target token, EM/normalized EM,
precision/recall/F1, ROUGE, BLEU, chrF, so sánh baseline/fine-tuned và prediction
từng mẫu. BERTScore/QA-v4 có quy trình riêng trong [QA/RAG evaluation](qa-rag-evaluation.md).
