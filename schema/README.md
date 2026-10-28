# Hợp đồng đánh giá bốn cấu hình v3.2

Ba schema độc lập: `golden_dataset.schema.json` mô tả nhãn chuẩn,
`prediction.schema.json` mô tả dữ liệu thực tế phải thu, và
`evaluation_case.schema.json` bổ sung kết quả chấm vào prediction.
Mọi $ref đều nội bộ. Hai file *.example.json là dữ liệu giả lập để xem cấu trúc.

**Phạm vi thay đổi: schema, ví dụ và kiểm thử. Collector/scorer chưa được đổi.**
JSONL cũ không bị ghi lại. Golden mới yêu cầu `evaluation_plan`; dữ liệu cũ chưa
có khối này cần được gán nhãn/bổ sung trong một bước migration được yêu cầu riêng.
Không được tự suy ra các nhãn còn thiếu để làm cho dữ liệu pass.

## Cấu hình và phạm vi chấm

`architecture` bắt buộc là `base | finetuned | rag | finetuned_rag`.
`evaluation_scope` là `end_to_end | retrieval`; retrieval-only chỉ hợp lệ
với rag/finetuned_rag. Golden dùng chung cho cả bốn cấu hình.

| Dữ liệu/điểm | base, finetuned | rag, finetuned_rag |
|---|---|---|
| Câu trả lời, reference metrics, key facts, semantic correctness | Có | Có |
| Retrieval và prompt_contexts | null / [] | Có khi trả lời theo bằng chứng |
| Retrieval metrics, citation, groundedness theo context | Bỏ qua hoặc not_applicable + value:null + reason | Có khi đủ bằng chứng |
| Query processing | Có thể null nếu không tiền xử lý | Bắt buộc khi success |
| Retrieval latency | null, không ghi điểm 0 | Thời gian thực đo |
| Latency sinh/toàn lượt | Bắt buộc khi success end_to_end | Bắt buộc khi success end_to_end |
| Corpus/index revision, requested_cutoffs | null / [] | Giữ thông tin truy hồi |

Fine-tuning phải ghi base_model, model_revision và ít nhất một định danh
adapter_revision hoặc checkpoint_revision không rỗng. Có thể thêm quantization,
decoding. Đây là định danh artifact, không chứng minh model đã được tải.

NEW/FOLLOW_UP lấy từ taxonomy.turn_type để phân nhóm; không chấm router.
Prediction không nhận actual_route; nhóm query_processing không nhận các điểm
route/router/scope/conversation/section accuracy. expected_route còn trong
golden để giữ cấu trúc dataset, nhưng không dùng làm mục tiêu chấm trong phạm vi này.

Groundedness ở đây là mức bám vào context được cấp. Độ đúng so với đáp án chuẩn
của Base/fine-tuning vẫn chấm trong generation.semantic_correctness; không
đánh đồng hai loại điểm. Retrieval-only không chấm token/TTFT/tốc độ sinh hoặc
generation latency, kể cả khi ghi 0.

## Metric và dữ liệu đã quy định phải thu

| Nhóm điểm | Prediction khi thành công | Nhãn đối chiếu trong golden |
|---|---|---|
| Hit, Precision, Recall, RR, AP, nDCG | query, top_k, contexts có rank/ID/score/text | context ID chuẩn, cutoffs, relevance_completeness |
| Query rewrite | standalone_query, rewrite_applied nếu có tiền xử lý | ground_truth_standalone_query |
| Sub-query precision/recall | sub_queries có ID/query, decomposition_applied | sub_query_targets |
| Multi-intent coverage | sub_query_results có query/top_k/contexts riêng từng ý | sub_query_targets.relevant_context_ids |
| EM, token F1, ROUGE, BLEU, chrF, BERTScore | actual_output | expected_answer, reference_answers, normalization_version |
| Key-fact coverage | actual_output | key_facts_required, fact_evidence |
| Citation precision/recall | citations có claim và source_id, [] nếu không trích dẫn | expected_citations |
| Faithfulness, context relevance, semantic correctness, hallucination | prompt_messages, prompt_contexts chính xác sau cắt ngân sách, câu trả lời và toàn bộ retrieved text | đáp án/fact/bằng chứng chuẩn, corpus_revision |
| False refusal, abstention, action accuracy | action: answer/partial_answer/clarify/abstain | expected_action và is_unanswerable |
| Format, negative constraints | actual_output, prompt_messages | expected_format, format_rules, negative_rules |
| Latency | total/query_processing/retrieval/generation_latency_ms bắt buộc là số | không cần nhãn |
| TTFT, token, tốc độ, tài nguyên, chi phí | measurements có value/status/source/reason; chi phí có pricing | không cần nhãn |
| Noise robustness | evaluation_context.robustness_pair và prediction của cả hai nhánh | evaluation_plan.robustness_pair, distractor_injection |

Schema đủ đầu vào để các scorer tương ứng chạy; không có nghĩa scorer đã được
cài/chạy. Các điểm judge được tạo ở bước chấm, lưu `evaluation_results.judgments`
kèm claim/verdict/context IDs, tên/phiên bản judge và hash input/prompt.
Không đo faithfulness bằng việc chỉ đối chiếu citation ID.

Ở cấp case dùng reciprocal rank/AP; trung bình nhiều case mới là MRR/MAP.
Chỉ báo @k trong requested_cutoffs và không vượt độ sâu truy hồi. Relevance là
nhị phân, không bịa grade 0–3. `known_positives_only` có nghĩa kết quả được đối
chiếu với bằng chứng đã biết; chunk chưa gán nhãn không chứng minh tuyệt đối
là không liên quan. Precision chia số item thực trả về; nDCG dùng binary gain,
log2(rank+1); AP@k chia min(k, số relevant chuẩn đã biết).

## Prediction thành công không được để rỗng tùy ý

- Với RAG, `query_processing` bắt buộc có standalone query, cờ rewrite/decompose
  và sub-query; không yêu cầu route. Base/fine-tuning có thể để null.
- Khi decomposition=true: có ít nhất hai sub-query và hai kết quả truy hồi riêng.
- Context truy hồi phải có text; trả lời RAG phải lưu prompt_messages và ít nhất
  một prompt_context có chính xác phần văn bản đưa vào model.
- `citations` bắt buộc là danh sách; không có citation là [] để chấm thiếu citation,
  không dùng null để che việc không trích dẫn.
- Nếu không truy hồi vì clarify/abstain: ghi retrieval=null và retrieval_skip_reason.
- Khi success, latency toàn lượt bắt buộc có số; end_to_end cần generation latency,
  cấu hình RAG cần query/retrieval latency. Base/fine-tuning ghi retrieval latency
  null vì không áp dụng, không tự tạo điểm 0.
- Measurements của provider/tài nguyên phải có trạng thái. Không hỗ trợ đo thì
  unavailable + reason; không bịa token/TTFT/VRAM hoặc coi chúng bằng 0.
- Retrieval-only không có generation; ca lỗi có error và không có actual_output
  hoàn tất. Partial output không được chấm như câu trả lời hoàn tất.

Các measurement giả lập trong ví dụ có source=`synthetic-example-only`.
Chúng không phải số đo model thật.

## Golden bổ sung evaluation_plan

Khối này bắt buộc chứa cutoffs, expected_action, reference_answers, fact_evidence,
sub_query_targets, format_rules, negative_rules, robustness_pair,
relevance_completeness, normalization_version và corpus_revision.

Ca multi_intent yêu cầu ít nhất hai sub_query_targets. Ca không trả lời được có
fact_evidence rỗng và hành động clarify/abstain. Ca answerable có ít nhất một
fact_evidence. Khi có injected_noise_ratio > 0, phải chỉ ra counterpart clean
để có thể thiết kế phép so sánh; gắn ID cặp chưa thay cho việc chạy đủ hai nhánh.
Rule literal_absence phải có forbidden_text; rule judge dùng rubric mô tả.

Không truyền ground_truth/evaluation_plan vào model trả lời; chúng chỉ dùng cho
bộ chấm. Prediction chỉ giữ cutoffs và thông tin cặp thử nghiệm trong
evaluation_context, không chứa đáp án hoặc nhãn hành động kỳ vọng.

## Kiểm tra liên kết khi triển khai collector/scorer

JSON Schema kiểm tra cấu trúc và điều kiện, không so sánh được các giá trị tùy ý
ở nhiều trường. Validator ngữ nghĩa khi nối runtime cần kiểm tra:

- test_id/input/dataset_version khớp golden; hash và corpus/index đúng artifact.
- fact/citation/context IDs tham chiếu nguồn hợp lệ; reference_answers chứa
  expected_answer; fact_evidence bao phủ key_facts_required.
- sub_query_id duy nhất, liên kết đúng query và nhóm context.
- rank liên tục, context ID không lặp, số kết quả và cutoff phù hợp top_k.
- prompt_contexts đúng văn bản đã đưa vào prompt, không nhầm toàn bộ context
  trước truncation; metric/judgment gắn đúng prediction.
- cặp clean/noisy có đủ hai bản ghi, cùng cấu hình và chỉ khác nhiễu được kiểm soát.
- measurement thời gian/token/chi phí tự nhất quán; metric theo run kèm n,
  danh sách loại mẫu, warm-up và concurrency nếu chấm throughput.

Những kiểm tra liên kết này chưa được thêm vào runtime trong phạm vi schema-only.
