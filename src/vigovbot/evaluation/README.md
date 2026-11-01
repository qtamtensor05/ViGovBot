# Module `vigovbot.evaluation`

## Trách nhiệm

Module thực thi quy trình đánh giá chuẩn hoá (Evaluation v3.2) trên Golden dataset (`Data/dataset_v3`).
Tách biệt hoàn toàn giữa quá trình thu thập phản hồi (`run`) và quá trình chấm điểm offline (`score`).
Ground truth tuyệt đối không được đưa vào prompt hoặc pipeline trả lời của mô hình.

## Thành phần và luồng dữ liệu

```text
Data/dataset_v3 (test_rag / test_router / fintuning)
               │
               ▼
   workflow.py / records.py (capture_predictions)
               │
               ▼
     predictions.jsonl (tuân thủ schema/prediction.schema.json)
               │
               ▼
   workflow.py / records.py (build_record + export_scores)
   ├── scoring.py (supplemental metrics: sacrebleu, chrf, BERTScore, MAP@5)
   ├── extended.py (sub-queries, multi-intent coverage, MAP@10)
   ├── ollama_judge.py (LLM-as-a-judge: faithfulness, relevance)
   └── pairwise.py (đối đầu run A vs run B)
               │
               ▼
  case-scores.jsonl & scores.json (tuân thủ evaluation_case & summary v3.2)
```

| File | Trách nhiệm |
|---|---|
| `workflow.py` | Điều phối toàn bộ vòng đời run-directory: `validate`, `run`, `score`, `report`, `compare` |
| `records.py` | Scorer trung tâm: nạp Golden v3, thu thập prediction, tính điểm ranking $k \in \{1, 3, 5, 10, 15\}$, routing, format, xuất summary |
| `scoring.py` | Tính điểm bổ sung offline: sacrebleu, chrF/chrF++, CER, WER, MAP@5, BERTScore, cosine similarity |
| `lexical.py` | Chuẩn hóa NFC/casefold, Exact Match, Token Precision/Recall/F1, ROUGE-1/2/L |
| `extended.py` | Tính sub-query precision/recall, multi-intent coverage, MAP@10, unsupported claim rate |
| `ollama_judge.py` | LLM-as-a-judge độc lập đánh giá trích xuất claim, context relevance và faithfulness |
| `pairwise.py` | So sánh đối đầu trực tiếp giữa hai run ID trên cùng tập dữ liệu |
| `retrieval_benchmark.py` | Thu thập kết quả truy hồi độc lập (`run_retrieval`) và reranking (`rerank_retrieval`) không gọi LLM |
| `execution.py` | Cơ chế retry có kiểm soát và điều phối request tuần tự hoặc đa luồng |
| `provenance.py` | SHA-256 fingerprinting và bảo toàn nguồn gốc dữ liệu |

## Sử dụng qua CLI `vigov eva`

```powershell
# 1. Kiểm tra tính toàn vẹn của split dữ liệu
vigov eva validate --dataset Data/dataset_v3 --split test

# 2. Thu thập câu trả lời từ endpoint
vigov eva run --dataset Data/dataset_v3 --split test --profile rag --run-id rag-v3

# 3. Chấm điểm offline và tính các chỉ số
vigov eva score --run-id rag-v3 --extended-metrics --bertscore

# 4. Tái chấm điểm prediction có sẵn mà không gọi lại model
vigov eva score --run-id rag-v3 --extended-metrics --bertscore --rescore

# 5. So sánh đối đầu giữa hai lần chạy
vigov eva compare --run-id rag-v3 --other-run-id base-v3
```

## Ràng buộc
- Tuyệt đối không nội suy dữ liệu hoặc gán điểm 0 cho các giá trị không đo được; dùng `null` và `status="unavailable"` / `"not_applicable"`.
- Mọi artifact điểm số đều được băm SHA-256 để kiểm chứng nguồn gốc.
