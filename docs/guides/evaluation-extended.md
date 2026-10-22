# Evaluation mở rộng

Luồng: `run-v2` → `judge-v2` (Ollama local, tùy chọn) → `export-v2 --judgments`.
Chạy trên máy inference riêng; không dùng train để báo cáo khả năng tổng quát.
Không chạy model hoặc judge tự động khi export.

Trong config inference của máy chạy, thêm:

```yaml
llm:
  measure_ttft: true
retrieval:
  top_k: 10
conversation:
  routing_enabled: true
  citations_enabled: true
  decompose_queries: true
```

Ghép các khóa vào section hiện có, không tạo section YAML trùng. Khởi động lại web
để nạp config. Decomposition là một bước inference mới, tối đa 5 query; fusion RRF
với hằng số 60. Context thực sự đưa vào prompt vẫn chịu giới hạn token và nằm trong
context_used. Run mới thay đổi hành vi; không so sánh như thể cùng config với run cũ.

```powershell
vigov eva judge-v2 --split test --predictions outputs/new-run/predictions.jsonl --judge-model TEN_MODEL_DA_CAI --out outputs/new-run/judgments.jsonl
vigov eva export-v2 --split test --architecture rag_base --model-name TEN_MODEL --run-id new-run --predictions outputs/new-run/predictions.jsonl --judgments outputs/new-run/judgments.jsonl --out outputs/new-run/results.jsonl
```

Judge chạy ở localhost mặc định; Docker dùng `--judge-endpoint http://ollama:11434`.
Không tải model tự động. Output tạo mới, không ghi đè; judge có `--limit` để smoke.
Judgment có hash nội dung, rubric, tên/digest model, thời điểm và lý do. Partial
judgments được export với n riêng cho từng metric; không coi là toàn benchmark.
Claim extraction là suy luận của judge: exact substring được kiểm tra, verdict
`hallucination_rate` có hợp đồng hẹp: số claim bị judge đánh dấu contradicted chia
tổng claim được trích xuất; đây là evidence-contradiction rate, không đo mọi dạng
bịa. `unsupported_claim_rate` gồm contradicted và unknown. Không có claim thì null.
Verdict
supported/contradicted/unknown cần human calibration trước khi dùng kết luận factuality.
Human có thể cung cấp cùng schema judgment với reviewer_kind=human và hash đúng.

MAP@10 yêu cầu trace retrieval_top_k >= 10. Sub-query P/R dùng normalized exact-set
matching, không phải semantic matching; câu diễn đạt khác có thể bị tính không khớp.
Multi-intent coverage dùng mapping query text → danh sách chunk ID đã gán nhãn.
Token usage/tokens/s là final generation call của Ollama; không phải tổng mọi retry,
router và decomposition. TTFT đo tới content đầu tiên ở client, có network overhead.
GPU/VRAM/cost/rerank vẫn null khi backend không có phép đo; không gán số giả.
Giữ 5 action hiện có: answer, partial, abstain, clarify, correct_premise.

## Pairwise có người đánh giá

```powershell
vigov eva pairwise-v2 --predictions outputs/run-a/predictions.jsonl --other-predictions outputs/run-b/predictions.jsonl --out outputs/pairwise-packets.jsonl
vigov eva pairwise-v2 --predictions outputs/run-a/predictions.jsonl --other-predictions outputs/run-b/predictions.jsonl --judgments outputs/pairwise-reviewed.jsonl --out outputs/pairwise-summary.json
```

Điền winner A/B/tie, reviewer và reason trong bản sao packet. Không sửa input/hash.
Thứ tự A/B đảo xác định theo ID; reviewer không thấy tên model. Báo cáo tính win
rate và tie-adjusted rate trên số ca đã review; không tự chọn model theo test set.
