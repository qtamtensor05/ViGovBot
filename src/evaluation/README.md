# Evaluation — đánh giá Qwen + RAG bằng qa_test

Module đọc bộ test, chạy câu hỏi độc lập, lưu prediction và tính metric.
Chỉ `question.text` được gửi tới pipeline trả lời; đáp án và ngữ cảnh mẫu không
được dùng để truy hồi hoặc sinh câu trả lời.

## Thành phần

| File | Trách nhiệm |
| --- | --- |
| [dataset.py](dataset.py) | Đọc JSONL/ZIP, kiểm tra schema và ID |
| [runner.py](runner.py) | Gọi `answer_fn`, lưu kết quả/lỗi, tiếp tục lượt chạy |
| [metrics.py](metrics.py) | Exact Match, Accuracy chuẩn hóa, BLEU-4 và ROUGE |
| [report.py](report.py) | BERTScore, tổng hợp, phân nhóm, CSV/JSON và biểu đồ |

## Dữ liệu và luồng chạy

`load_cases()` ưu tiên `data.dataset_path` nếu file tồn tại; nếu không, đọc
`data.dataset_zip`. ZIP cần đúng một file `dataset.jsonl`, có thể trong thư mục con.
Đầu vào bắt buộc có ID chuỗi duy nhất, `question.text/type/difficulty` dạng chuỗi
và `ground_truth.answer` dạng chuỗi. Câu hỏi không được rỗng.

1. [RAG orchestrator](../rag/README.md) chọn `max_cases` và xác minh manifest.
2. Runner đọc các ID đã thành công, xử lý từng câu chưa có kết quả.
3. Sau khi có câu trả lời, gắn đáp án chuẩn, ghi JSONL và flush ra ổ đĩa.
4. Câu lỗi được ghi riêng; không đánh dấu hoàn tất, sẽ thử lại khi chạy tiếp.
5. Report đọc prediction của các câu đã chọn, tính metric nhẹ và lưu trước khi chạy BERTScore.
6. Tính BERTScore, tổng hợp và xuất báo cáo. Qwen/BGE-M3 được pipeline giải phóng trước bước này.

## Chạy và cấu hình

```sh
python -m src.rag --config rag_config.yaml evaluate
python -m src.rag --config rag_config.yaml report
```

Nhóm `evaluation` trong [rag_config.yaml](../../rag_config.yaml):

| Khóa | Ý nghĩa |
| --- | --- |
| `smoke_test_n` | Số câu thử của lệnh `smoke`/`run`, mặc định 5; không ghi prediction chính |
| `max_cases` | `null` chạy toàn bộ; bộ qa_test hiện có 570 câu |
| `bertscore_model` | `xlm-roberta-large`, giữ giống baseline |
| `bertscore_device`, `bertscore_batch_size` | Mặc định CPU và 1 để giảm bộ nhớ |
| `baseline_summary_path` | Summary baseline để xuất bảng đối chiếu, đặt trước khi chạy |

## Metric và giới hạn diễn giải

| Metric | Cách hiểu hiện tại |
| --- | --- |
| Exact Match | Khớp chuỗi sau khi bỏ khoảng trắng hai đầu |
| Accuracy chuẩn hóa | Khớp sau chuẩn hóa chữ thường, Unicode, dấu câu và khoảng trắng |
| BLEU-4 | So khớp n-gram, có smoothing; lấy trung bình điểm từng câu |
| ROUGE-1/2/L | F1 theo thư viện rouge-score, giữ cách tính baseline |
| BERTScore | Precision/Recall/F1, không rescale baseline |
| `source_recall_at_k` | Tỷ lệ mã thủ tục trong ground truth được tìm thấy ở top-k |
| Thời gian | Tổng, truy hồi (gồm encode câu hỏi) và gọi LLM |

Accuracy không chấm `must_include`/đủ ý hay độ đúng pháp lý. ROUGE mặc định có hạn
chế với tiếng Việt; BERTScore cao không bảo đảm dữ kiện đúng. Source recall chỉ tính
khi có `ground_truth.source_documents[].code`; đó là điểm truy hồi theo mã nguồn,
không phải điểm câu trả lời hoặc recall theo chunk.

Metric chỉ tính trên câu thành công. Summary ghi `n_requested`, `n_cases`,
`n_missing`, `coverage`; không coi câu lỗi là câu trả lời sai trong trung bình.
So sánh baseline/RAG cần cùng tập test, phiên bản model và thiết lập metric/sinh.

## File kết quả

Trong `data.output_dir`:

- `raw_predictions.jsonl`: câu trả lời, nguồn top-k, ngữ cảnh thực dùng, thời gian và JSON Ollama.
- `errors.jsonl`: lịch sử lỗi nếu có; lỗi cũ có thể còn dù lần sau câu đó thành công.
- `run_manifest.json`: cấu hình/định danh lượt chạy do pipeline tạo.
- `case_metrics.jsonl`, `case_metrics.csv`, `summary.json`: metric chi tiết và tổng hợp.
- `by_question_type.csv`, `by_difficulty.csv`, `by_answerability.csv`, `metrics.png`: phân tích.
- `baseline_vs_rag.csv`: chỉ có khi cấu hình baseline summary.

Giữ cùng dữ liệu, code và cấu hình để tiếp tục. Khi thay đổi, chọn output mới;
không chạy hai phiên cùng thư mục. Cơ chế phục hồi JSONL nằm trong [utils](../utils/README.md).

[Quay lại tổng quan](../README.md)
