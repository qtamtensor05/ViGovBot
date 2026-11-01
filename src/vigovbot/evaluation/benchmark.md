# Quy trình Benchmark Đánh giá trong `vigovbot.evaluation`

Tài liệu hướng dẫn thực hiện benchmark đánh giá hiệu năng và chất lượng các mô hình (Base, RAG, QLoRA) trên bộ dữ liệu chuẩn **`Data/dataset_v3`**.

## 1. Dữ liệu Benchmark Chuẩn (`Data/dataset_v3`)

1. **Phương án 1 (`test_rag/test_rag_pa1.jsonl`) — Cân bằng đa tỉ lệ**:
   - 638 mẫu thử nghiệm đại diện.
   - Cân bằng 6 tỉ lệ cốt lõi: Single-turn/Multi-turn 50/50, Đất đai ~23%, 5 core sections (16–24%), Hard ~23%, Unanswerable ~6.4%, phủ 406 thủ tục.
   - Thích hợp cho benchmark định kỳ, kiểm thử hồi quy và so sánh model.

2. **Phương án 2 (`test_rag/test_rag_pa2.jsonl`) — Phủ cực đại thủ tục**:
   - 874 mẫu thử nghiệm.
   - Phủ 100% (808/808) thủ tục hành chính có trong tập test_rag.
   - Thích hợp cho nghiệm thu toàn diện cấp hệ thống.

3. **Kiểm thử bộ định tuyến (`test_router/test_router.jsonl`)**:
   - 1.246 mẫu kiểm thử định tuyến PhoBERT và phân giải Catalog qua Clarifier.

---

## 2. Quy trình Thực thi Benchmark

### Bước 1: Kiểm tra tính toàn vẹn tập dữ liệu
```powershell
vigov eva validate --dataset Data/dataset_v3 --split test
```

### Bước 2: Chạy Benchmark Thu thập Dự đoán
```powershell
# Chạy với profile RAG
vigov eva run --run-id rag-benchmark-01 --profile rag --dataset Data/dataset_v3 --split test --endpoint http://localhost:8001/api/chat

# Chạy với profile Base (không RAG)
vigov eva run --run-id base-benchmark-01 --profile base --dataset Data/dataset_v3 --split test --endpoint http://localhost:8001/api/chat

# Chạy với profile QLoRA Fine-tuned
vigov eva run --run-id qlora-benchmark-01 --profile qlora --dataset Data/dataset_v3 --split test --endpoint http://localhost:8001/api/chat --model-metadata metadata.json
```

### Bước 3: Chấm điểm Offline (Scoring)
```powershell
vigov eva score --run-id rag-benchmark-01 --extended-metrics --bertscore
```
*Ghi chú:*
- Nếu cần chấm lại các chỉ số mở rộng mà không chạy lại suy luận model, sử dụng cờ `--rescore`:
```powershell
vigov eva score --run-id rag-benchmark-01 --extended-metrics --bertscore --rescore
```

### Bước 4: So sánh Đối đầu (Pairwise Comparison)
```powershell
vigov eva compare --run-id rag-benchmark-01 --other-run-id base-benchmark-01
```

---

## 3. Benchmark Truy hồi Độc lập (Retrieval-Only)

Không cần nạp LLM sinh câu trả lời, chỉ đánh giá độ chính xác và độ trễ của vector search:
```powershell
vigov eva run --run-id retrieval-fast --profile rag --scope retrieval --top-k 15 --dataset Data/dataset_v3 --split test
vigov eva score --run-id retrieval-fast
```
Các chỉ số truy hồi được tính toán gồm: Hit@K, Recall@K, Precision@K, MRR@K, NDCG@K ($K \in \{1, 3, 5, 10, 15\}$).

---

## 4. Ràng buộc Đo lường
- Không gộp các chỉ số không liên quan thành một điểm tổng hợp duy nhất.
- Báo cáo riêng biệt 4 nhóm: **Retrieval**, **Generation**, **Groundedness**, và **Performance/Telemetry**.
- Các giá trị không đo được hoặc không áp dụng bắt buộc ghi `null` kèm lý do cụ thể trong metadata, không được bịa số hoặc gán 0.
