# Module `vigovbot.evaluation`

## Trách nhiệm

Module đọc bộ test, điều phối inference theo từng ca, lưu kết quả có thể tiếp tục,
tính metric và sinh báo cáo. Ground truth không được đưa vào pipeline trả lời.

## Thành phần và luồng dữ liệu

```text
dataset.py → case[] → runner.py → answer_fn(question.text)
                           │              │
                           │              └── prediction + retrieval + timing
                           └── raw_predictions.jsonl / errors.jsonl
                                           │
                                      report.py → metric + summary + biểu đồ
```

| File | Trách nhiệm |
|---|---|
| `dataset.py` | Đọc và chuẩn hóa bộ test từ file hoặc ZIP |
| `runner.py` | Chạy từng ca, resume theo ID và cô lập lỗi từng ca |
| `metrics.py` | Exact match, accuracy chuẩn hóa, BLEU và ROUGE |
| `report.py` | BERTScore, source recall, thống kê độ trễ, CSV/JSON và biểu đồ |

## Đầu vào và đầu ra

`evaluate_cases()` nhận danh sách case, thư mục đầu ra, manifest cấu hình và
callback `answer_fn`. Kết quả được ghi tăng dần vào `raw_predictions.jsonl`;
exception của từng case được ghi vào `errors.jsonl`.

`generate_report()` đọc prediction đã lưu và tạo `case_metrics.jsonl`,
`case_metrics.csv`, `summary.json`, báo cáo theo nhóm, `metrics.png` và tùy chọn
`baseline_vs_rag.csv`.

## Ràng buộc

Resume chỉ hợp lệ khi manifest lượt chạy không thay đổi. ID đã hoàn thành không
được chạy lại. Ground truth chỉ được gắn vào bản ghi sau khi `answer_fn` trả kết
quả. Báo cáo yêu cầu ít nhất một prediction hợp lệ và sử dụng khóa khi ghi file.

[Kiến trúc hệ thống](../../../docs/architecture.md) · [Module RAG](../rag/README.md)
