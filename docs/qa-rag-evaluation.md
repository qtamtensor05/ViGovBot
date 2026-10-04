# Quy trình đánh giá RAG có kiểm chứng — QA v4.2

## Phạm vi và trạng thái

Tách kiểm chứng nguồn, duyệt ngữ nghĩa và chất lượng mô hình. Script tìm thấy nguyên văn trong PDF không phải là người/AI đã xác nhận câu hỏi và đáp án đúng, đủ. AI review không thay thế hai người duyệt theo rubric dataset. Không tự chuyển `gold_status` sang approved.

Bộ `rag_tthc_three_1500` là evaluation-only, có chứa ca từ dev cũ. Không tuyên bố unseen test nếu đã dùng các ca này để chỉnh hệ thống. Giữ PDF/corpus/dataset theo snapshot và SHA-256. Không xác minh hiệu lực pháp luật hiện tại từ điểm benchmark.

## 1. Kiểm tra nguồn và duyệt case

Chạy từ gốc repository; trên Colab thay `env/Scripts/python.exe` bằng `python`.

```powershell
env/Scripts/python.exe -m vigovbot.qa_v4.audit --dataset Data/qa_test_v4/rag_tthc_three_1500 --out outputs/qa_audit_new
```

Audit đọc PDF bằng PyMuPDF, đối chiếu hash/trang/nội dung. Dùng thứ tự text gốc để tránh trộn cột bảng và nối khoảng trắng trước khi chuẩn hóa dấu tiếng Việt. Phép kiểm vẫn không kiểm chứng liên hệ hàng/cột hay toàn bộ ngữ nghĩa. Output từ chối ghi đè JSONL đã có; chọn thư mục mới cho lần chạy mới.

- `case_source_audit.jsonl`: trạng thái kiểm chứng nguồn từng ca.
- `review_packets.jsonl`: câu hỏi, reference, bằng chứng và các ý bắt buộc đề xuất.
- `pdf_text_cache.json`: text PDF để kiểm tra lại, không thay cho trang render khi bảng có nhiều cột.
- `source_audit_summary.json`: số ca, số PDF, lỗi và hash dataset.

Các ý đề xuất chỉ tách theo hàng bảng, giữ nguyên điều kiện; chưa tự tách mọi câu/ý nhỏ và chưa được duyệt. Người/AI đọc PDF phải kiểm tra điều kiện, ngoại lệ, đơn vị, số lượng, câu hỏi phủ định và phạm vi thủ tục. Ghi ID ca, reviewer_kind, lý do, hash case và trang đã xem. Chỉ sửa dataset bằng phiên bản mới sau khi xác nhận lỗi; không sửa dữ liệu gốc để tăng điểm.

## 2. Mapping và retrieval

```powershell
env/Scripts/python.exe -m vigovbot.qa_v4.mapping --dataset Data/qa_test_v4/rag_tthc_three_1500 --predictions outputs/result_qa/three1500_single_smoke_rag_1/predictions.jsonl --out outputs/mapping_candidates_new.json
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
env/Scripts/python.exe -m vigovbot.qa_v4 score --dataset rag_tthc_three_1500 --view views_single_1500.json --split test --predictions outputs/new_run/predictions.jsonl --unit-map outputs/mapping_reviewed.json --lexical --bertscore --bert-model xlm-roberta-large --bert-device cpu --bert-batch-size 1 --out outputs/new_run/scores.json
```

Không có mapping thì bỏ `--unit-map`; bộ chấm ghi rõ retrieval chưa đầy đủ. Cài extras evaluation (gồm sacrebleu, ROUGE, BERTScore). Model BERT có thể cần tải riêng.

`--bert-cache` thay cho `--bertscore` nhận cache có `input_sha256` của danh sách `(id, answer, reference)` theo thứ tự case, `configuration` và `per_case` gồm precision/recall/f1. Bộ chấm từ chối cache khác input, thiếu ca hoặc NaN/Inf. Cache đã chuyển đổi, kiểm tra từ lần chấm hiện tại: `outputs/result_qa/evaluation_upgrade/bertscore_validated_cache.json`.

Similarity áp dụng cho answer/partial/correct_premise có phản hồi hợp lệ; action accuracy toàn tập tính cả lỗi. BERTScore là tương đồng, không phải tỷ lệ trả lời đúng. Khóa model/hash, baseline rescaling và giới hạn tokenizer khi so sánh. Báo rõ 5 reference bị cắt trong lần chấm bổ sung hiện tại.

## 4. Duyệt/chấm ngữ nghĩa

```powershell
env/Scripts/python.exe -m vigovbot.qa_v4.review --dataset Data/qa_test_v4/rag_tthc_three_1500 --predictions outputs/new_run/predictions.jsonl --out outputs/new_run/review_packets.jsonl
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
env/Scripts/python.exe -m vigovbot.qa_v4 run --dataset rag_tthc_three_1500 --view views_single_1500.json --split test --config configs/rag.yaml --no-retrieval --out outputs/compare/base.jsonl
env/Scripts/python.exe -m vigovbot.qa_v4 run --dataset rag_tthc_three_1500 --view views_single_1500.json --split test --config configs/rag.yaml --out outputs/compare/rag.jsonl
env/Scripts/python.exe -m vigovbot.qa_v4 run --dataset rag_tthc_three_1500 --view views_single_1500.json --split test --config configs/rag.yaml --oracle-evidence --out outputs/compare/oracle.jsonl
```

Chấm từng run bằng cùng lệnh score/cấu hình metric. Oracle/base không dùng để báo chất lượng retriever. Nếu bật citations cho RAG/oracle thì nêu đây là thay đổi prompt/cấu hình so với lần chạy cũ; baseline không có nguồn để dẫn.

```powershell
env/Scripts/python.exe -m vigovbot.qa_v4.compare --left outputs/compare/base_scores.json --right outputs/compare/rag_scores.json --out outputs/compare/base_vs_rag.json
```

Comparison từ chối khác dataset, tập ID, nhóm hoặc history mode; điểm ngữ nghĩa chỉ so sánh nếu cùng tập judgment. Bootstrap theo procedure_family/conversation, seed 42, 2.000 lần; chênh lệch right-minus-left. Lỗi tính 0 cho action accuracy. Công cụ không tự xác nhận cấu hình model tương đương; phải kiểm tra provenance. Tránh dùng tập test để chọn cấu hình.

## Artifact triển khai hiện tại

Xem [báo cáo triển khai và giới hạn](../outputs/result_qa/evaluation_upgrade/README.md). PDF/data và kết quả model gốc được giữ nguyên. Chưa có runtime Ollama hoạt động trong phiên triển khai, nên các kiểm thử adapter/oracle/citations là offline; chưa có ba lần chạy model thật để so sánh.
