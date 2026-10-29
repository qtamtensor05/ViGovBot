# Benchmark độ trễ reranker ngày 2026-10-29

## Mục tiêu và phạm vi

So sánh truy xuất FAISS top 3 với luồng FAISS top 10 rồi dùng
`BAAI/bge-reranker-v2-m3` chọn top 3. Benchmark chỉ đo query embedding, FAISS/SQLite
và reranker; không gọi model sinh câu trả lời. Chạy tuần tự trên web container CPU,
batch size 4, max length 512, revision `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`.

Dùng 1 câu warm-up, sau đó đo 10 câu cố định; thứ tự baseline/reranker luân phiên.
Thời gian tải model được loại khỏi latency từng câu và ghi riêng. Đây là phép đo
độ trễ truy xuất, không phải tải đồng thời hay benchmark chất lượng.

## Kết quả

| Luồng | Trung bình | Median | P95 | Tổng 10 câu |
|---|---:|---:|---:|---:|
| FAISS top 3 | 258.7 ms | 170.7 ms | 1,031.8 ms | 2.59 s |
| FAISS top 10 + reranker top 3 | 12,474.8 ms | 12,378.2 ms | 14,488.1 ms | 124.75 s |
| Riêng FAISS top 10 | 192.3 ms | 181.9 ms | 306.0 ms | 1.92 s |
| Riêng reranker | 12,282.5 ms | 12,203.0 ms | 14,328.2 ms | 122.82 s |

Luồng có reranker mất trung bình **48.2 lần thời gian** của FAISS top 3, tăng
khoảng **4,722.7% latency** (xấp xỉ 12.22 giây mỗi câu). Model load mất 2.72 giây,
không nằm trong con số trên. Trên cấu hình CPU đã đo, reranker không cải thiện tốc độ;
nó thêm độ trễ đáng kể để xếp hạng lại ứng viên. Kết quả không kết luận về GPU hoặc
chất lượng thứ hạng.

## Tái chạy

```powershell
docker compose exec -T web python -m vigovbot.evaluation.reranker_latency `
  --config /app/configs/rag/inference-docker-ollama.yaml `
  --output /tmp/reranker_latency.json
```

Script chứa đúng 10 câu benchmark và từ chối chạy nếu cấu hình không phải top 10 →
top 3 hoặc reranker bị tắt. Artifact JSON của lần chạy này:
`outputs/benchmarks/reranker_latency_10_20261029.json`.
