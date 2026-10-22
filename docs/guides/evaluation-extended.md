# Evaluation mở rộng

## Tách pha capture và chấm

Khi cần thu toàn bộ inference trước rồi mới chấm, dùng `run-v2
--complete-trace --resume` cho cả bốn kiến trúc. Với hai kiến trúc RAG, chạy
thêm `noise-v2` ngay trong pha capture; lệnh này chỉ replay các ca có distractor
đã gán nhãn và resume theo từng ca. Sau đó có thể dừng web/model sinh đáp án và
chạy `judge-v2`, `score-v2-offline`, `export-v2` hoàn toàn từ prediction đã lưu.

`QLORA_ADAPTER_PATH` áp dụng đồng thời cho `qwen-qlora` và
`qwen-qlora-rag`; profile sau dùng cùng adapter nhưng giữ retrieval/context của
RAG. Ví dụ capture QLoRA + RAG:

```bash
vigov eva run-v2 --architecture rag_finetuned --model-id qwen-qlora-rag \
  --split test --complete-trace --resume \
  --out outputs/evaluation_v2/qlora-rag/predictions.jsonl
vigov eva noise-v2 --model-id qwen-qlora-rag --split test \
  --predictions outputs/evaluation_v2/qlora-rag/predictions.jsonl \
  --out outputs/evaluation_v2/qlora-rag/noise-predictions.jsonl
```

Sau khi judge hai file sạch/nhiễu, tổng hợp robustness hoàn toàn offline:

```bash
vigov eva judge-v2 --judge-model qwen2.5:7b --split test --resume --allow-partial \
  --predictions outputs/evaluation_v2/qlora-rag/noise-predictions.jsonl \
  --out outputs/evaluation_v2/qlora-rag/noise-judgments.jsonl
vigov eva score-noise-v2 \
  --judgments outputs/evaluation_v2/qlora-rag/judgments.jsonl \
  --other-predictions outputs/evaluation_v2/qlora-rag/noise-judgments.jsonl \
  --out outputs/evaluation_v2/qlora-rag/noise-score.json
```

## Một lệnh tự động, human riêng

```powershell
vigov eva complete-v2 --architecture rag_base --model-id qwen-rag --judge-model TEN_MODEL_JUDGE --split test --out outputs/my-complete-run --bert-device cuda --bert-batch-size 16
```

Khởi động lại web trên máy chạy để nạp code mới. Lệnh kiểm tra capability web,
bật top-10/citation/decomposition/TTFT qua payload evaluation riêng, lưu prediction,
chạy judge, BERTScore/lexical bổ sung rồi export. `complete.json` chứa cả aggregate
v2 và supplemental metrics. Human/pairwise không chạy trong lệnh này.
Chạy lại cùng lệnh để resume; các prediction đã ghi không được sinh lại, judge
đã ghi được kiểm tra hash/rubric/model digest trước khi bỏ qua. Không sửa config,
model/index trong lúc resume. runtime-identity.json khóa source/config, Ollama digest,
adapter hash/base snapshot commit và hash corpus/index đang được server sử dụng.
Identity được kiểm tra trước/sau inference. File JSONL hỏng đuôi cần phục hồi trước khi resume.
Một ca prediction lỗi được giữ bản sao failed-attempt, resume chỉ chạy lại ca lỗi;
không phải chạy lại toàn bộ model. Judge lỗi dừng tại ca hiện tại, resume dùng lại
mọi judgment đã ghi. Context judge vượt upper bound 32768 token bị từ chối, không
âm thầm cắt bằng chứng. Prediction vẫn dùng được cho judge có context lớn hơn.

`provider_calls` lưu usage/latency của mọi call (router, rewrite, decomposition,
generation/retry), còn telemetry cũ giữ semantics final generation. chrF++ đã được
thêm. Complete-v2 tự chạy METEOR exact-token tiếng Việt (không English stemming/
WordNet), cosine sentence embedding đa ngữ, BERTScore và các lexical metrics.
Scoring offline riêng dùng `score-v2-offline --extended-metrics` với prediction đã lưu.
Cosine mặc định paraphrase-multilingual-MiniLM-L12-v2, lưu model/revision trong report.

GPU: nvidia-smi lấy mẫu mỗi 250ms và hai đầu mỗi call; lưu raw samples/UUID trong
provider_calls. Peak memory used là toàn GPU, có thể gồm process khác; không đồng
nhất với allocated/reserved của PyTorch. Local Transformers có thêm allocator peak
và TTFT/token usage. Ollama không có allocator telemetry, các trường đó để null.
Complete-v2 kiểm tra collector, dependency và judge model trước inference; thiếu
nguồn đo GPU sẽ dừng sớm. Docker cần nvidia-smi và quyền nhìn GPU trong web container.
Sau prediction, judge và noise replay, complete-v2 tự giải phóng model generation
và judge khỏi GPU trước khi chạy BERTScore/cosine; batch CUDA mặc định là 16.

Noise: chỉ case có distractor_contexts đã gán nhãn và generation context mới áp dụng.
Replay nguyên prompt sạch rồi nối distractor, không đưa expected_answer vào model.
Vượt budget thì dừng và giữ baseline, không cắt sạch context để nhường chỗ cho nhiễu.
noise-predictions.jsonl và noise-judgments.jsonl resume độc lập. Báo cáo tính tỷ lệ
vẫn đúng trên những ca baseline đúng và có judgment cả hai nhánh, kèm số mẫu và
correctness delta. Case không có distractor được ghi not_applicable.
Cost local không có hợp đồng billing nên không gán giá giả; human vẫn riêng.

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
