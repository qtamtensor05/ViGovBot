# Quy trình đánh giá RAG có kiểm chứng - QA v4.2

## Evaluation Run v2 offline trên Golden dataset

Golden canonical mới nằm tại `Data/golden_dataset` với ba split
`train_golden.jsonl`, `val_golden.jsonl` và `test_golden.jsonl`. Dùng
hai lệnh chạy từ môi trường Python trên host: `run-v2` hỏi model qua API web
Docker, sau đó `export-v2` chấm offline và xuất schema v2. Ví dụ đánh giá Base
trên toàn bộ split test:

Trước khi chạy, cài và kích hoạt môi trường evaluation theo
[tài liệu môi trường](../setup/environments.md); lệnh `vigov` dưới đây là console
script của package đã cài editable. Web Docker phải đang healthy tại cổng 8001.

```powershell
vigov eva run-v2 `
  --architecture base `
  --split test `
  --out outputs/evaluation_v2/base-test/predictions.jsonl

vigov eva export-v2 `
  --architecture base `
  --model-name qwen2.5:7b `
  --run-id base-test `
  --split test `
  --predictions outputs/evaluation_v2/base-test/predictions.jsonl `
  --out outputs/evaluation_v2/base-test/results.jsonl
```

Mặc định `run-v2` gọi `http://localhost:8001/api/chat` và ánh xạ
`base -> qwen-base`, `finetuned -> qwen-qlora`, `rag_base -> qwen-rag` theo
`configs/rag/inference-docker.yaml`. Dùng `--model-id` nếu cần ghi đè;
`rag_finetuned` bắt buộc chỉ định model ID vì Docker chưa có profile
mặc định. Request model chỉ gồm question/history, không có ground truth.

`run-v2` gửi thêm `evaluation_trace=true` tới Web Chat. Đây là cờ quan sát
ở API, không truyền vào prompt/model và không thay đổi inference settings.
Chat thông thường không có cờ này vẫn nhận response như trước.
Response opt-in chứa `evaluation_trace.schema_version="1.0"`; prediction giữ
trace gốc cùng các trường dành cho scorer: actual_route, routing, retrieval_query,
context_used, citations, citations_status, telemetry.

- Actual route ghi quyết định thực thi: `rag_search` khi đã đi vào retrieval
  (kể cả không có context), `clarify`, `out_of_scope`, hoặc `routing_error`
  khi router fallback. Base/QLoRA không có router nên giữ null.
- Citation đã được pipeline validate được chuyển `chunk_id` sang `source_id`
  và giữ claim. Không coi retrieved source là citation. Cờ trace không bật
  `citations_enabled`; nếu citation đang disabled/không có trace thì score
  citation là null/missing_input. Danh sách rỗng được quan sát khi citation
  bật vẫn có recall/precision 0 nếu Golden yêu cầu citation.
- Ghi timing routing/retrieval/generation thực có. Rewrite chỉ có timing riêng
  khi pipeline chạy lượt rewrite riêng; không lấy routing time thay rewrite time.
  Token estimate được giữ riêng, không điền vào token usage thực.
  TTFT, rerank time, token usage/throughput, VRAM, GPU utilization và cost chưa
  được đo trong response này nên giữ null.
- Server cũ không trả trace vẫn được chạy; prediction/report ghi
  `evaluation_trace_status=unavailable` (report là bảng đếm). Trace version chưa
  hỗ trợ được ghi `unsupported_version`, không tự suy đoán schema.
- Scorer offline version 2 phân biệt citation thiếu trace với citation rỗng.
  Prediction Web v2 cũ có `web_model_id`, citations rỗng và không có status sẽ
  được coi là thiếu trace. Kết quả scoring lịch sử không bị ghi đè; export lại
  sang đường dẫn mới để áp dụng chính sách mới.

Trace có thể chứa context đã truy hồi; không bao gồm raw provider response,
raw router hay secrets. Cờ debug_routing hiện có hoạt động độc lập.

`run-v2` ghi `<predictions>.run.json` với coverage, endpoint, model ID và
`gold_labels_sent_to_model=false`. Nếu một request lỗi/timeout, record vẫn
được lưu với `execution_status=error`; lệnh trả exit code khác 0 để
người chạy nhận biết.

Trong khi chạy, `run-v2` in tiến trình tối đa mỗi 10 giây và khi hoàn tất;
`export-v2` in mỗi 100 record và khi hoàn tất. Dòng tiến trình gồm số record,
phần trăm, thời gian đã chạy và ETA, được ghi ra stderr để không trộn với JSON
summary trên stdout và không cần thêm dependency progress bar.

Prediction phải có `id` hoặc `test_id` trùng `TC_*` trong split Golden.
Mặc định lệnh yêu cầu đủ coverage và từ chối ID ngoài benchmark;
`--allow-partial` chỉ dùng cho smoke/cached run chưa đủ. Prediction lịch sử
`qa2_*` thuộc benchmark khác nên không được ghép vào Golden này.

Không truyền `--predictions` sẽ tạo skeleton `not_run` cho việc kiểm tra
schema/coverage, không tạo kết quả model. Bốn giá trị architecture hợp lệ
là `base`, `finetuned`, `rag_base`, `rag_finetuned`. Base/fine-tuned có metric
retrieval `null` + `not_applicable`; RAG chỉ có retrieval score khi prediction
chứa trace ID và Golden có relevance label. Metric semantic, groundedness,
BERTScore hoặc constraint không đủ bằng chứng được giữ `null` kèm
`metric_details`, không thay bằng 0.

`export-v2` không khởi tạo model, retriever, BERTScore hay judge. File
`<results.jsonl>.summary.json` ghi coverage, execution status, hash đầu vào
và `inference_performed=false`. Cả hai lệnh không ghi đè artifact cũ.

## Phạm vi và trạng thái

Tách kiểm chứng nguồn, duyệt ngữ nghĩa và chất lượng mô hình. Script tìm thấy nguyên văn trong PDF không phải là người/AI đã xác nhận câu hỏi và đáp án đúng, đủ. AI review không thay thế hai người duyệt theo rubric dataset. Không tự chuyển `gold_status` sang approved.

Bộ `rag_tthc_three_1500` là evaluation-only, có chứa ca từ dev cũ. Không tuyên bố unseen test nếu đã dùng các ca này để chỉnh hệ thống. Giữ PDF/corpus/dataset theo snapshot và SHA-256. Không xác minh hiệu lực pháp luật hiện tại từ điểm benchmark.

## 1. Kiểm tra nguồn và duyệt case

Chạy từ gốc repository; trên Colab thay `.venv/Scripts/python.exe` bằng `python`.

```powershell
.venv/Scripts/python.exe -m vigovbot.evaluation.audit --dataset Data/qa_test_v4/rag_tthc_three_1500 --out outputs/qa_audit_new
```

Audit đọc PDF bằng PyMuPDF, đối chiếu hash/trang/nội dung. Dùng thứ tự text gốc để tránh trộn cột bảng và nối khoảng trắng trước khi chuẩn hóa dấu tiếng Việt. Phép kiểm vẫn không kiểm chứng liên hệ hàng/cột hay toàn bộ ngữ nghĩa. Output từ chối ghi đè JSONL đã có; chọn thư mục mới cho lần chạy mới.

- `case_source_audit.jsonl`: trạng thái kiểm chứng nguồn từng ca.
- `review_packets.jsonl`: câu hỏi, reference, bằng chứng và các ý bắt buộc đề xuất.
- `pdf_text_cache.json`: text PDF để kiểm tra lại, không thay cho trang render khi bảng có nhiều cột.
- `source_audit_summary.json`: số ca, số PDF, lỗi và hash dataset.

Các ý đề xuất chỉ tách theo hàng bảng, giữ nguyên điều kiện; chưa tự tách mọi câu/ý nhỏ và chưa được duyệt. Người/AI đọc PDF phải kiểm tra điều kiện, ngoại lệ, đơn vị, số lượng, câu hỏi phủ định và phạm vi thủ tục. Ghi ID ca, reviewer_kind, lý do, hash case và trang đã xem. Chỉ sửa dataset bằng phiên bản mới sau khi xác nhận lỗi; không sửa dữ liệu gốc để tăng điểm.

## 2. Mapping và retrieval

```powershell
.venv/Scripts/python.exe -m vigovbot.evaluation.mapping --dataset Data/qa_test_v4/rag_tthc_three_1500 --predictions outputs/result_qa/three1500_single_smoke_rag_1/predictions.jsonl --out outputs/mapping_candidates_new.json
```

Chỉ sinh **ứng viên**, không phải mapping được duyệt. So cùng hash PDF, đúng tiêu đề và đủ phần nội dung của unit. Duyệt từng chunk và giữ `status=candidate` khi chưa xác định. Chunk rỗng ứng viên không phải đoạn không liên quan. Đoạn chứa một phần unit dài không được coi là bao phủ toàn unit; đây là giới hạn của granularity và cần xem cùng fact/context coverage khi đã có judgment.

Mapping được chấp nhận lúc chấm có dạng:

```json
{
  "schema_version": 1,
  "review_kind": "ai_partial",
  "chunks": {
    "chunk-id": {
      "status": "reviewed",
      "unit_ids": ["document#unit"],
      "source_sha256": "PDF hash khớp knowledge_units",
      "chunk_sha256": "SHA-256 của included_text UTF-8",
      "reviewer": "tên hoặc ID người/AI duyệt",
      "reviewer_kind": "ai",
      "reason": "Các trang/đoạn và lý do ánh xạ"
    }
  }
}
```

`unit_ids=[]` chỉ hợp lệ sau khi reviewer xác nhận không có unit nào được bao phủ đầy đủ; không đồng nghĩa relevance=0. Nếu cùng chunk_id có nhiều context bị cắt khác nhau, phải xử lý từng biến thể trước khi duyệt. Không gán mapping theo mã thủ tục đơn thuần.

Trong v4.2, **@k là k chunk duy nhất theo thứ tự truy hồi ban đầu**. Một chunk có thể chứa nhiều unit; không flatten rồi cắt còn k unit. MRR tính hạng chunk đầu tiên chứa bằng chứng chuẩn. Qrels chưa exhaustive nên không công bố Precision/MAP/nDCG làm kết luận chính.

- `retrieval_evaluation.states`: ca có mapping, routing không truy hồi, lỗi, chưa xác định, không áp dụng.
- `eligible_cases`: ca có gold evidence.
- `end_to_end_all_eligible`: chỉ có khi mọi ca hợp lệ có mapping top-k. Lỗi/missing và routing bỏ qua được tính 0 trong mẫu số này.
- Nếu thiếu mapping, không xuất điểm tổng retrieval trong `overall_available`. Điểm từng ca đã xác minh vẫn được lưu để chẩn đoán; không dùng trung bình các ca này làm điểm toàn bộ benchmark.
- Dữ liệu chỉ có `retrieved_unit_ids` phẳng cũ không đủ tái tạo hạng chunk, nên không chấm bằng giả định ngầm.

`--unit-map` lúc `score` dùng schema duyệt ở trên. Lúc `run`, adapter cũ vẫn hỗ trợ dictionary chunk→list unit để ghi lại các nhóm; đây là mapping do caller cung cấp, chưa tự trở thành human-reviewed. Ưu tiên duyệt và chấm lại với schema đầy đủ.

## 3. Chấm lexical và BERTScore

```powershell
.venv/Scripts/python.exe -m vigovbot eva score --dataset rag_tthc_three_1500 --view views_single_1500.json --split test --predictions outputs/new_run/predictions.jsonl --unit-map outputs/mapping_reviewed.json --lexical --bertscore --bert-model xlm-roberta-large --bert-device cpu --bert-batch-size 1 --out outputs/new_run/scores.json
```

Không có mapping thì bỏ `--unit-map`; bộ chấm ghi rõ retrieval chưa đầy đủ. Cài extras evaluation (gồm sacrebleu, ROUGE, BERTScore). Model BERT có thể cần tải riêng.

`--bert-cache` thay cho `--bertscore` nhận cache có `input_sha256` của danh sách `(id, answer, reference)` theo thứ tự case, `configuration` và `per_case` gồm precision/recall/f1. Bộ chấm từ chối cache khác input, thiếu ca hoặc NaN/Inf. Cache đã chuyển đổi, kiểm tra từ lần chấm hiện tại: `outputs/result_qa/evaluation_upgrade/bertscore_validated_cache.json`.

Similarity áp dụng cho answer/partial/correct_premise có phản hồi hợp lệ; action accuracy toàn tập tính cả lỗi. BERTScore là tương đồng, không phải tỷ lệ trả lời đúng. Khóa model/hash, baseline rescaling và giới hạn tokenizer khi so sánh. Báo rõ 5 reference bị cắt trong lần chấm bổ sung hiện tại.

## 4. Duyệt/chấm ngữ nghĩa

```powershell
.venv/Scripts/python.exe -m vigovbot.evaluation.review --dataset Data/qa_test_v4/rag_tthc_three_1500 --predictions outputs/new_run/predictions.jsonl --out outputs/new_run/review_packets.jsonl
```

Packet chứa case, history, reference, nguồn, câu trả lời, context và citations. Người/AI chấm theo `judge_rubric.md`: correctness, completeness, faithfulness, citation_support, behavior_correct là **0/1/null**. Không suy từ keyword, action hoặc BERTScore. Null nghĩa chưa chấm/không áp dụng, không phải 0.

Mỗi JSONL judgment phải có `id`, `reviewer`, `reviewer_kind=ai|human`, `reason`, `input_sha256` từ packet và đủ 5 trường metric. AI nên ghi model/prompt/phương pháp và loại mẫu trong metadata; chỉ được gọi là calibrated sau khi đối chiếu mẫu độc lập do người duyệt. Script từ chối hash cũ, ID lạ/trùng, ca lỗi và judgment hoàn toàn null.

Truyền `--judgments judgments.jsonl` khi score. Report ghi reviewer kind và số ca thực chấm từng metric. Mẫu chọn để tìm lỗi không đại diện toàn tập. Hiện có 5 judgment AI chẩn đoán, chưa có điểm chất lượng ngữ nghĩa toàn bộ 1.500 ca và chưa có hiệu chỉnh với người duyệt.

## 5. Trích dẫn và provenance của lần chạy mới

Trong cấu hình RAG, bật riêng:

```yaml
conversation:
  routing_enabled: true
  citations_enabled: true
```

Model trả citations gồm chunk_id và claim nguyên văn trong answer. Validator kiểm tra ID thuộc context đã dùng và claim xuất hiện trong câu trả lời; sai định dạng đi qua retry giới hạn của generation. Đây **không** phải tự động kiểm chứng claim được nguồn hỗ trợ. Citation support phải được chấm ngữ nghĩa. Cấu hình mặc định false để không thay đổi âm thầm các thí nghiệm cũ.

Context giữ pages/source_sha256 nếu corpus cung cấp. Adapter giữ thứ hạng retrieval, context và generation metadata. Runner ghi hash query/view/config và mode; scorer ghi hash dataset/predictions/mapping/judgments/cache. Hash không thay thế lưu model/corpus revision; cần lưu cùng corpus_manifest và commit khi chạy Colab như quy trình notebook hiện hành.

## 6. So sánh base/RAG/oracle

Dùng cùng model, seed, temperature, ngân sách sinh, dataset/view và lịch sử; khóa cấu hình trước khi chạy. Oracle chỉ là thí nghiệm chẩn đoán, bỏ routing/retrieval và đưa quote của bằng chứng chuẩn, không truyền reference_answer hay nhãn hành vi. Context oracle vẫn chịu token budget; không coi là mức trần toán học.

```powershell
.venv/Scripts/python.exe -m vigovbot eva run --dataset rag_tthc_three_1500 --view views_single_1500.json --split test --config configs/rag/evaluation.yaml --no-retrieval --out outputs/compare/base.jsonl
.venv/Scripts/python.exe -m vigovbot eva run --dataset rag_tthc_three_1500 --view views_single_1500.json --split test --config configs/rag/evaluation.yaml --out outputs/compare/rag.jsonl
.venv/Scripts/python.exe -m vigovbot eva run --dataset rag_tthc_three_1500 --view views_single_1500.json --split test --config configs/rag/evaluation.yaml --oracle-evidence --out outputs/compare/oracle.jsonl
```

Chấm từng run bằng cùng lệnh score/cấu hình metric. Oracle/base không dùng để báo chất lượng retriever. Nếu bật citations cho RAG/oracle thì nêu đây là thay đổi prompt/cấu hình so với lần chạy cũ; baseline không có nguồn để dẫn.

```powershell
.venv/Scripts/python.exe -m vigovbot.evaluation.compare --left outputs/compare/base_scores.json --right outputs/compare/rag_scores.json --out outputs/compare/base_vs_rag.json
```

Comparison từ chối khác dataset, tập ID, nhóm hoặc history mode; điểm ngữ nghĩa chỉ so sánh nếu cùng tập judgment. Bootstrap theo procedure_family/conversation, seed 42, 2.000 lần; chênh lệch right-minus-left. Lỗi tính 0 cho action accuracy. Công cụ không tự xác nhận cấu hình model tương đương; phải kiểm tra provenance. Tránh dùng tập test để chọn cấu hình.

## Artifact triển khai hiện tại

Xem artifact `outputs/result_qa/evaluation_upgrade/README.md` (không có trong checkout hiện tại). PDF/data và kết quả model gốc được giữ nguyên. Chưa có runtime Ollama hoạt động trong phiên triển khai, nên các kiểm thử adapter/oracle/citations là offline; chưa có ba lần chạy model thật để so sánh.

## Hợp đồng lexical và tương thích kết quả (2026-10-18)

Training evaluation và QA scoring dùng `vi-lexical-v1`: NFC + casefold +
Unicode word tokens (giữ dấu tiếng Việt, chữ số và underscore; không phải tách
 từ tiếng Việt). BLEU dùng SacreBLEU, tokenize=none, smoothing=exp,
effective_order=True, thang 0–100; tổng hợp bằng corpus BLEU, không lấy trung
bình sentence BLEU. ROUGE dùng rouge-score với tokenizer Unicode chung,
không stemming. Normalized EM dùng cùng normalization; raw EM của training
vẫn là so sánh chuỗi strip, khác normalized EM của QA.

Training summary và QA report lưu `metric_contract`; QA còn lưu phiên bản thư
viện và BLEU signature. V2 dùng normalization chung và ghi
`normalization_version` trong summary; không tự tính BLEU/ROUGE còn thiếu.
Đồng nhất công thức chưa đủ để so sánh: phải cùng tập mẫu, reference, cohort,
quy tắc bỏ prediction lỗi/rỗng và denominator. QA chỉ chấm reference similarity
ở cohort nội dung phù hợp, training chấm các hàng được đánh giá; token F1 trên
cặp chuỗi rỗng cũng còn chính sách khác nhau giữa hai luồng.

`evaluation/metrics.py` dùng SacreBLEU chung, scale 0–1 và macro sentence
BLEU trong summary (khác corpus BLEU). EM/ROUGE dùng normalization/tokenizer
chung từ `baseline-vi-lexical-v3`, từ chối baseline khác version.
Chấm lại prediction cũ để so sánh; không trộn các số này với
`vi-lexical-v1`. Training BLEU/ROUGE trước thay đổi cũng không cùng contract:
muốn so sánh, chấm lại cached prediction/reference cùng phiên bản. Không sửa
artifact lịch sử hoặc suy ra chất lượng factuality từ similarity.

JSONL dataset dùng parser read-only chung với chính sách tường minh:
evaluation bỏ dòng trắng, training từ chối dòng trắng và vẫn kiểm tra hội
thoại/ID. `experiments.read_results` là recovery log riêng: chỉ khi bật
`repair_tail=True` mới cắt dòng cuối JSON lỗi không có newline; dòng trắng
không bị cắt, lỗi giữa file luôn bị từ chối. Không dùng recovery để đọc dataset.

Hash file dùng duy nhất `artifacts.file_hash` (chunk 1 MiB), các tên cũ là
alias tương thích. Kiểm tra overlap training nay có NFC và version normalization;
kết quả overlap mới có thể khác báo cáo cũ với văn bản Unicode decomposed.

## Chọn runner và xử lý output đã tồn tại

| Entry point | Input/output và lịch sử | Resume |
|---|---|---|
| `evaluation.runner.evaluate_cases` | Case baseline có question.text/ground_truth; raw_predictions trong run dir | Có, manifest phải khớp, writer lock, tail recovery |
| `evaluation.benchmark_runner.run_queries` | Query QA; reference_history hoặc free_running; thread theo job/conversation, file prediction riêng | Không; output mới bắt buộc, lỗi chỉ rõ phải chọn --out khác |
| `evaluation.multiturn` | Query hội thoại có sequence validation, run directory và manifest | Có theo hợp đồng history/run của module |

Ba entry point phục vụ schema và cơ chế thực thi khác nhau. Không đổi từ runner
này sang runner khác để nối file prediction đang dở; cần chọn workflow trước
khi chạy. Benchmark threaded dùng exclusive create có chủ đích để bảo vệ kết
quả; kiểm tra sớm output trước khi gọi model và vẫn giữ mode x để tránh race.
Không triển khai resume bằng cách bỏ qua ID đơn thuần vì free-running phải
khôi phục history, trạng thái lỗi và provenance trước khi tiếp tục.

`judgment_scoring.py` cung cấp phần chấm judgment/evidence cho scorer hiện
đại. Module cũ `scoring_legacy.py` đã được đổi tên; công thức và schema kết quả
giữ nguyên. Entry point công khai vẫn là `vigov eva`.

## HTTP và concurrency (2026-10-18)

`/api/chat` là API comparison riêng, không phải endpoint chat-completions OpenAI.
Request không hợp lệ trả 400; tất cả model lỗi trả 502 với `status=failed`,
`error` và lỗi từng model trong `results`. Có cả thành công/lỗi trả 200 với
`status=partial`; client phải kiểm tra từng result. Tất cả thành công trả 200
với `status=success`. Health/models không sử dụng khóa inference.

Provider `openai_compatible` chạy ngoài khóa GPU; Ollama và local Transformers
vẫn tuần tự hóa switching/inference trên GPU dùng chung. Không tuyên bố tăng
throughput GPU từ thay đổi này. Batch Transformers giữ khóa cache đến hết
inference và dùng bản sao tokenizer riêng, không sửa padding của tokenizer cache.
Retrieval đọc metadata bằng IN theo batch tối đa 900 ID, sau đó khôi phục thứ tự
FAISS; top-k thông thường chỉ dùng một SELECT. Cleanup unload lỗi ghi warning
loại exception, không nuốt im lặng và không che exception generation ban đầu.
