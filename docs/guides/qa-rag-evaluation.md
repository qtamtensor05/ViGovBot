# Quy trình đánh giá RAG có kiểm chứng - Evaluation v3.2

Quy trình đánh giá chính thức (Evaluation v3.2) sử dụng tập dữ liệu **`Data/dataset_v3`** và các schema tại **`schema/`**.

## 1. Hợp đồng dữ liệu và Schema

- **Dữ liệu chuẩn:** `Data/dataset_v3`
  - `test_rag/test_rag_pa1.jsonl`: Benchmark RAG chính thức theo Phương án 1 (Golden Ratio Balanced: 638 mẫu).
  - `test_rag/test_rag_pa2.jsonl`: Benchmark RAG theo Phương án 2 (Max Procedure Coverage: 874 mẫu).
  - `test_router/test_router.jsonl`: 1.246 mẫu kiểm thử bộ định tuyến PhoBERT và Clarifier.
- **Hợp đồng Schema v3.2:**
  - `schema/golden_dataset.schema.json`: Cấu trúc nhãn chuẩn Golden.
  - `schema/prediction.schema.json`: Định dạng kết quả dự đoán và telemetry thực tế (`predictions.jsonl`).
  - `schema/evaluation_case.schema.json`: Kết quả chấm điểm chi tiết từng ca (`case-scores.jsonl`).
  - `schema/evaluation_summary.schema.json`: Báo cáo tổng hợp toàn bộ lần chạy (`scores.json`).
  - `schema/output_router.jsonl`: Cấu trúc mẫu cho phân loại router và hành động.

---

## 2. Quy trình Thực thi Chuẩn qua `vigov eva`

### Bước 1: Kiểm tra tính toàn vẹn và Split
```powershell
$env:PYTHONUTF8 = "1"
vigov eva validate --dataset Data/dataset_v3 --split test
```

### Bước 2: Thu thập kết quả suy luận (`run`)
Lệnh gửi câu hỏi tới endpoint Web Chat (mặc định `http://localhost:8001/api/chat` với cờ `evaluation_trace=true`) và ghi nhận `predictions.jsonl`:

```powershell
# Đánh giá cấu hình RAG
vigov eva run --dataset Data/dataset_v3 --split test --profile rag --run-id rag-v3-01

# Đánh giá cấu hình Base (không RAG)
vigov eva run --dataset Data/dataset_v3 --split test --profile base --run-id base-v3-01

# Đánh giá cấu hình QLoRA Finetuned (yêu cầu metadata provenance)
vigov eva run --dataset Data/dataset_v3 --split test --profile qlora --run-id qlora-v3-01 --model-metadata model_metadata.json
```

*Lưu ý cho cấu hình QLoRA:*
File `--model-metadata <json>` bắt buộc phải khai báo `base_model`, `model_revision` và ít nhất một trong `adapter_revision` hoặc `checkpoint_revision`.

### Bước 3: Chấm điểm Offline (`score`)
Đọc `predictions.jsonl` và đối chiếu với Golden nhãn chuẩn để tính toán toàn bộ metric:

```powershell
vigov eva score --run-id rag-v3-01 --extended-metrics --bertscore
```

- Nhóm Lexical: Exact Match, Normalized EM, Token Precision/Recall/F1, ROUGE-1/2/L.
- Nhóm Retrieval ($k \in \{1, 3, 5, 10, 15\}$): Hit@K, Recall@K, Precision@K, MRR@K, NDCG@K, MAP@10.
- Nhóm Routing: `route_accuracy` (so khớp canonical route).
- Nhóm Robustness: `format_compliance`, `negative_constraint_pass`, `action_accuracy`, `abstention_correct`.
- Nhóm Extended (khi bật cờ): SacreBLEU, chrF/chrF++, CER, WER, METEOR, BERTScore, Embedding Cosine Similarity.
- Nhóm Judge (tùy chọn với Ollama): `--judge-model qwen2.5:7b` cho Faithfulness và Context Relevance.

### Tái chấm điểm mà không cần gọi lại model (`--rescore`)
Nếu chỉ cần cập nhật hoặc tính thêm các metric bổ sung từ file `predictions.jsonl` có sẵn:

```powershell
vigov eva score --run-id rag-v3-01 --extended-metrics --bertscore --rescore
```

### Bước 4: Báo cáo và So sánh Đối đầu
```powershell
# Xem báo cáo tổng hợp
vigov eva report --run-id rag-v3-01

# So sánh trực tiếp hai cấu hình (Pairwise Comparison)
vigov eva compare --run-id rag-v3-01 --other-run-id base-v3-01
```

---

## 3. Benchmark Truy hồi Độc lập (Retrieval-Only Scope)

Khi cần đo riêng hiệu năng retriever (BGE-M3 + FAISS/SQLite) mà không gọi LLM sinh văn bản:

```powershell
vigov eva run --dataset Data/dataset_v3 --split test --profile rag --scope retrieval --top-k 15 --run-id retrieval-test-01
vigov eva score --run-id retrieval-test-01
```

---

## 4. Nguyên tắc Đo lường và Báo cáo

1. **Bảo toàn dữ liệu đo:** Không bịa đặt hoặc suy diễn các measurement còn thiếu; nếu provider không trả về token/TTFT/VRAM, ghi `null` kèm lý do cụ thể trong `measurements` với trạng thái `unavailable`.
2. **Tách biệt nhóm điểm:** Không gộp điểm Retrieval và Generation thành một con số duy nhất. Groundedness phản ánh mức bám vào ngữ cảnh cung cấp; Semantic Correctness phản ánh độ chính xác so với đáp án chuẩn.
3. **Bảo toàn nguồn gốc (Provenance):** Mọi artifact đều gắn mã băm SHA-256 của tập dữ liệu và tệp dự đoán để đảm bảo tính bất biến và khả năng kiểm chứng.
