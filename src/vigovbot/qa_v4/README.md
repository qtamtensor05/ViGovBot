# Giao tiếp và đánh giá RAG với QA v4

Module đọc QA, gửi câu hỏi và lịch sử cho RAG hiện có, nhận câu trả lời rồi
đánh giá. Module không có pipeline BM25, model embedding hoặc model sinh
câu trả lời riêng.

Luồng: `runner_queries.jsonl → RAG hiện có → predictions.jsonl → evaluator v4.1`.
Chỉ bước `score` đọc `cases.jsonl` chứa đáp án và nhãn.

## Chạy với RAG trong repository

Chạy từ thư mục gốc, sau khi cài `python -m pip install -e ".[rag,evaluation]"`.
Corpus và Ollama cần sẵn sàng theo cấu hình RAG hiện tại.

```powershell
python -m vigovbot qa-v4 chat --config rag_config.yaml
python -m vigovbot qa-v4 run --config rag_config.yaml --split test --limit 10 --out outputs/qa_v4/smoke.jsonl
python -m vigovbot qa-v4 score --split test --limit 10 --predictions outputs/qa_v4/smoke.jsonl --out outputs/qa_v4/smoke_scores.json
```

## Baseline Qwen không retrieval

`--no-retrieval` gọi trực tiếp model Ollama trong cấu hình, không đọc corpus, không
nạp encoder và không dùng FAISS. Có thể chạy chế độ này trong lúc corpus đang được
embedding (nếu tài nguyên CPU/GPU đủ). Không truyền đáp án tham chiếu vào model.

```powershell
python -m vigovbot qa-v4 run --config configs/inference.yaml --no-retrieval --split test --limit 10 --out outputs/qa_v4/qwen7b_baseline_smoke.jsonl
python -m vigovbot qa-v4 score --split test --limit 10 --predictions outputs/qa_v4/qwen7b_baseline_smoke.jsonl --out outputs/qa_v4/qwen7b_baseline_smoke_scores.json
```

Prediction baseline dùng cùng schema chấm điểm, nhưng không có evidence truy hồi;
report vì vậy không công bố recall/MRR.

Adapter tái sử dụng `prepare`, `inference_session` và `answer_question` của
`vigovbot.rag.pipeline`; dùng cùng corpus, embedding, FAISS, tokenizer, routing,
prompt và model theo `rag_config.yaml`. Phiên suy luận được tải một lần cho
toàn bộ batch.

`ask --question "..."` gửi một câu hỏi; chat hỗ trợ `/reset` và `/exit`.
`--top-k` chỉ điều chỉnh k khi chấm, còn `top_k` truy hồi lấy từ cấu hình RAG.

## Chạy với API RAG đã có

```powershell
python -m vigovbot qa-v4 run --endpoint http://localhost:8000/rag --split test --out outputs/qa_v4/http_test.jsonl
```

POST chỉ gửi `{question, history}`. API trả object có `answer` hoặc `prediction`,
`action` và các trường tùy chọn: `retrieved_unit_ids`, `retrieved_chunk_ids`,
`retrieved`, `citations`, `telemetry`. Module không mở server; endpoint phải có sẵn.

## Chọn QA và lịch sử

`--dataset` mặc định là `Data/qa_test_v4/rag_tthc_v4_1`, dùng view `views_balanced.json`.
Có thể truyền đường dẫn thư mục bộ test hoặc tên ngắn `rag_v4_small` để chọn
`Data/qa_test_v4/rag_tthc_balanced_small`. Bộ nhỏ mặc định dùng `views_main_test.json`
(6.384 lượt test chính); challenge và dev chạy riêng qua `--view` và `--split`.
Nếu thư mục bộ test có `views_main_test.json`, view này được chọn mặc định;
nếu không, dùng `views_balanced.json`. `--view` luôn ưu tiên lựa chọn tường minh.

Chạy từ thư mục gốc bằng môi trường `env` trên Windows:

```powershell
env\Scripts\python.exe -m vigovbot qa-v4 run --dataset rag_v4_small --config configs/inference.yaml --split test --mode free_running --out outputs/qa_v4/small_main.jsonl
env\Scripts\python.exe -m vigovbot qa-v4 score --dataset rag_v4_small --split test --lexical --predictions outputs/qa_v4/small_main.jsonl --out outputs/qa_v4/small_main_scores.json
```

Để chạy baseline Ollama trên cùng bộ nhỏ, thêm `--no-retrieval` vào lệnh `run`
và chọn đường dẫn output mới. Để chạy challenge, thêm
`--view views_challenge_test.json` vào cả `run` và `score`.
Prediction lưu cùng `question`, `answer` (hoặc `error`), `id`, `conversation_id`
và `turn_index`; đáp án tham chiếu chỉ được đọc ở bước chấm.

`--mode reference_history` dùng lịch sử chuẩn trong `runner_queries.jsonl`.
`--mode free_running` dùng câu trả lời RAG vừa sinh, tách lịch sử theo hội thoại
và từ chối chuỗi thiếu hoặc sai thứ tự trước khi tải model.

`--limit` dùng để chạy thử, có thể cắt hội thoại. Dùng cùng view/split/limit
khi `run` và `score` để chấm cùng tập; bỏ limit khi chạy toàn bộ benchmark.
File đầu ra đã tồn tại sẽ bị từ chối ghi đè. Lỗi từng lượt được lưu trong
predictions; `run` trả exit code 1 nếu có lỗi.

Trong khi chạy, tiến độ hiển thị thời gian còn lại và giờ hoàn thành dự kiến cho
toàn bộ tập đã chọn (sau view/split/limit). ETA dùng thời gian chạy trung bình của
các câu đã hoàn tất nên sẽ ổn định dần; những câu đầu có thể dao động do thời gian
khởi động model và độ dài câu khác nhau.

## Điểm và hiệu suất

Score báo tỷ lệ thành công/lỗi, action accuracy, độ tương đồng với đáp án,
latency trung bình/p50/p95/p99 và thời gian retrieval/generation nếu được cung cấp.
File `.run.json` ghi thời gian batch, thời điểm bắt đầu/kết thúc, phương pháp tính
ETA và số request thành công mỗi giây. Đây là chạy tuần tự, không phải kiểm thử tải
đồng thời và không gồm thời gian tải model ban đầu.

`--judgments judgments.jsonl` bổ sung phán quyết ngữ nghĩa theo `judge_rubric.md`.
`--lexical` bật BLEU/ROUGE/chrF/TER, cần cài thêm `sacrebleu>=2,<3`.
Điểm tương đồng không chứng minh nội dung đúng; correctness và faithfulness
chỉ có khi cung cấp judgments. Evaluator được chuyển từ bộ QA v4.1.

## Đối chiếu bằng chứng

Chunk ID của RAG có thể khác `unit_id` của QA v4. Module giữ nguyên chunk ID,
không tự coi chúng là unit ID và không suy ra mapping từ đáp án.

Để chấm recall/MRR, API cần trả unit ID v4 hoặc cung cấp `--unit-map map.json`
ở bước `run`. Schema: `{"rag_chunk_1": ["1.000005#u001"]}`. Mapping phải dựa trên
đối chiếu bằng chứng nguồn. Nếu thiếu hoặc mapping không đầy đủ, score bỏ điểm
retrieval và ghi `retrieval_evaluation.available=false`; các điểm trả lời,
hành vi và thời gian vẫn có.

Data bị gitignore, cần có bộ QA tại máy chạy. Nguồn là snapshot PDF,
không xác nhận hiệu lực pháp luật hiện tại.
