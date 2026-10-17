# Đề xuất triển khai Evaluation Run v2 cho các model

## 1. Kết luận audit hiện trạng

- `examples/evaluation_v2/evaluation_run_v2.schema.json` là hợp đồng kết quả theo
  từng case; hai dòng trong file example chỉ là mẫu `not_run`/`not_scored`, không
  phải kết quả model.
- `examples/QA/golden_test_cases.jsonl` là JSON mẫu mô tả Golden Schema.
  Golden thật đã được bổ sung tại `Data/golden_dataset`: 2.200 train,
  550 val và 1.100 test, tổng 3.850 case.
- Runtime canonical hiện nằm tại `src/vigovbot/evaluation`: đã chạy được Base
  không retrieval, RAG dùng model nền và QLoRA không retrieval. Chưa có adapter
  QLoRA + RAG dùng chung retriever với RAG Base.
- Prediction/scorer hiện tại dùng contract QA-v4 (`id`, `answer`, `action`,
  `citations`, telemetry...). Nó chưa sinh trực tiếp đầy đủ Evaluation Run v2.

Không nên sửa tay file example hoặc điền `0` cho metric thiếu. Lớp
chuyển đổi offline hiện được cung cấp bởi `vigov eva export-v2`; nó
ghép Golden với prediction đã có theo ID và không chạy model.

## 2. Ma trận model đề xuất

| Run | `architecture_type` | Context đưa vào model | Retrieval metric | Groundedness/citation |
|---|---|---|---|---|
| Base | `base` | Chỉ question + history | `null`, `not_applicable` | Chấm theo nguồn Golden nếu có judge/evidence; không giả lập citation |
| QLoRA | `finetuned` | Chỉ question + history | `null`, `not_applicable` | Như Base; ghi adapter revision/hash |
| RAG Base | `rag_base` | Context do retriever thực tế trả về | Chấm khi ID index ánh xạ được sang relevance label | Chấm claim trên context đã retrieve và citation thực tế |
| QLoRA + RAG | `rag_finetuned` | Cùng retriever/prompt/context với RAG Base, chỉ đổi generator | Chấm như RAG Base | Chấm như RAG Base; ghi cả corpus/index và adapter revision |

Nên có thêm `oracle_evidence` như run chẩn đoán upper-bound, nhưng không xếp nó
vào bảng thắng/thua của bốn kiến trúc production.

## 3. Nội dung cần ghi cho mỗi case

### Trước khi chạy

- Sao chép bất biến `test_id`, `version`, `taxonomy`, `input`, `ground_truth` từ
  Golden thật; thêm `split` từ manifest chính thức, không suy ra từ tên file.
- Tạo `run_id` riêng cho từng tổ hợp model/checkpoint/prompt/corpus/index/seed.
- Ghi hash/revision thật cho model, adapter, prompt, corpus, index và decoding.
- `golden_metadata_filters_used` chỉ là `true` khi filter đó hợp lệ ở production
  và được áp dụng công bằng; không truyền Golden answer, expected route, context
  ID hay label vào model.

### Trong khi chạy

- Thu query rewrite, route, sub-query; danh sách retrieved ID/score/context theo
  đúng thứ tự; output/citation/finish reason; latency theo từng stage; token và
  GPU telemetry từ nguồn đo thật.
- Lỗi/timeout/OOM vẫn tạo một record có `execution_status` tương ứng. Không loại
  im lặng case lỗi khỏi denominator.
- Multi-turn phải tách hai cohort: `reference_history` để so model ổn định và
  `free_running` để đo lỗi tích lũy hội thoại; không gộp hai mode trong một run.

### Sau khi chạy

- Metric không đủ input/dependency là `null`; `metric_details.<metric>.status`
  phải là `computed`, `not_applicable`, `unavailable` hoặc `failed` kèm lý do.
- Reference metric chỉ phản ánh độ giống đáp án. Factuality/groundedness cần
  key fact, evidence span hoặc judge có model, revision, prompt và provenance.
- Unanswerable chấm abstention/unsupported answer riêng; không dùng retrieval
  recall/citation recall khi Golden cố ý không có relevance/citation label.
- Pairwise bootstrap, slice summary và human calibration là artifact tổng hợp,
  không lặp một kết quả aggregate vào từng case.

## 4. Các phase triển khai

### Phase 0 - Chốt dữ liệu và contract

1. Đưa Golden thật vào `Data/` cùng manifest/hash; giữ file schema mẫu trong
   `examples/QA` và đổi mô tả để tránh nhầm nó là dataset chạy được.
2. Viết validator cho JSON/JSONL, ID duy nhất, enum, split, context/citation ID,
   answerable/unanswerable và leakage ở cấp thủ tục.
3. Rút gọn schema v2 nếu cần: metric per-case chỉ giữ metric thực sự có nghĩa;
   metric corpus như SacreBLEU và paired CI chuyển sang summary schema.
4. Pin tokenizer/segmenter tiếng Việt, BERTScore model revision, embedding model,
   judge contract và quality gate trong config versioned.

Điều kiện đạt: toàn bộ Golden thật parse/schema pass; manifest ghi số case theo
split/cohort và SHA-256; example hai case vẫn validate nhưng không mang điểm giả.

### Phase 1 - Builder và trace v2

Thêm module dưới `src/vigovbot/evaluation/` để:

1. tạo skeleton v2 từ Golden;
2. chuyển prediction hiện tại sang `system_execution_output`;
3. validate từng record trước khi append JSONL;
4. hỗ trợ resume theo khóa `(run_id, test_id)` nhưng từ chối trộn cấu hình;
5. ghi run manifest và summary riêng dưới `outputs/evaluation_v2/<run_id>/`.

Điều kiện đạt: fixture Base/RAG/QLoRA sinh đúng schema; lỗi, timeout và metric N/A
được biểu diễn rõ; không ghi đè artifact cũ.

### Phase 2 - Bốn adapter model công bằng

Giữ `vigov eva` làm CLI duy nhất. Mở rộng adapter hiện có thành bốn profile; bổ
sung QLoRA + RAG bằng cách tái sử dụng cùng query processor/retriever/reranker và
chỉ thay generator. RAG Base và QLoRA + RAG phải khóa cùng corpus/index/top-k,
prompt context và decoding khi so sánh tác động của fine-tuning.

Điều kiện đạt: smoke cùng tập ID, không lộ Golden, provenance đầy đủ; Base/QLoRA
không có retrieval trace giả; RAG Base/QLoRA+RAG trả trace ID có thể đối chiếu.

### Phase 3 - Scorer v2

Ưu tiên triển khai theo thứ tự:

1. coverage, execution status, normalized EM/token F1, ROUGE, corpus BLEU/chrF;
2. route/rewrite/sub-query và retrieval Hit/Recall/MRR/nDCG khi qrels đủ;
3. key-fact, format, negative constraint, abstention và adversarial cohorts;
4. groundedness/citation bằng rule + human/judge calibration;
5. BERTScore/embedding, telemetry, paired bootstrap và slice report.

Không triển khai MAP/precision/nDCG nếu relevance label không đầy đủ; khi đó ghi
`unavailable` thay vì trả về một con số dễ gây hiểu nhầm.

### Phase 4 - Báo cáo và nghiệm thu

- Báo bốn nhóm tách biệt: generation, retrieval, groundedness và performance.
- Mỗi bảng có `n`, denominator, số missing/failed và khoảng tin cậy khi so cặp.
- Slice tối thiểu: domain, difficulty, complexity, turn type, in/OOD,
  answerable/unanswerable và adversarial type.
- Chỉ so model trên giao ID thành công đồng thời, đồng thời vẫn báo coverage trên
  toàn bộ expected IDs để không che giấu failure.

## 5. Phạm vi pull request đề xuất

Nên tách thành ba PR để dễ kiểm chứng:

1. **Contract/data:** Golden loader, validator, schema/config v2 và fixtures.
2. **Execution:** v2 trace writer, bốn model profile, QLoRA + RAG và CLI.
3. **Scoring/report:** metric registry, aggregate/slice/pairwise report và docs.

Không chạy full 3.850 case ở PR đầu. Mỗi PR dùng fixture CPU/mocked telemetry;
sau đó chạy smoke nhỏ trên model thật, rồi mới chạy benchmark đầy đủ bằng workflow
lệnh dài và lưu rõ trạng thái chưa chạy/chạy lỗi/chạy xong.

## 6. Quyết định cần chốt trước khi code

1. Vị trí và manifest của Golden 3.850 case thật.
2. QLoRA + RAG dùng prompt format nào và có yêu cầu citation bắt buộc hay không.
3. ID relevance ở cấp chunk hay knowledge unit; đây là denominator của retrieval.
4. Judge/human rubric cho factuality, faithfulness và unsupported claim.
5. Metric bắt buộc cho quality gate; không dùng một điểm tổng hợp duy nhất.
