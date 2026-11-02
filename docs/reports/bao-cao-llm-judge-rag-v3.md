# Báo cáo LLM-as-a-Judge cho mô hình RAG v3

> Run được chấm: `eval-rag-v3`  
> Judge: `qwen2.5:14b` · 638 judgment · ngày artifact 02/11/2026

## Mục tiêu và hợp đồng chấm

Báo cáo tách riêng kết quả LLM-as-a-Judge khỏi các metric tương đồng đáp án. Judge đánh giá correctness, relevancy, intent, groundedness, faithfulness, hành vi từ chối và các claim dựa trên evidence được cung cấp. Mỗi metric chỉ được tổng hợp trên mẫu có judgment áp dụng; giá trị `null` không được thay bằng 0.

| Provenance | Giá trị |
|---|---|
| Judge model | `qwen2.5:14b` |
| Model digest | `7cdf5a0187d5c58cc5d369b255592f7841d1c4696d45a8c8a9489440385b22f6` |
| Reviewer kind | `ai` |
| Rubric SHA-256 | `8310f9bcf483955c402d3148039f2d7e2b0f117f8bafa7abeb1b6686a573fce4` |
| Judgment SHA-256 | `8be50ea8acfd866b8fba630699af792356e6af7d64a6926eb807146e4fda2e93` |
| Số judgment | 638/638 ID |

## Hai kết quả bám nguồn chính

| Chỉ số | Định nghĩa trong run | Điểm | n |
|---|---|---:|---:|
| Source groundedness | Câu trả lời có được hỗ trợ bởi nguồn Golden cung cấp | 0,9086 | 350 |
| Retrieved-context faithfulness | Câu trả lời có trung thành với context thực dùng để sinh | 0,8940 | 349 |

Hai điểm đều cao nhưng không áp dụng cho mọi mẫu. Chúng trả lời hai câu hỏi khác nhau: groundedness dùng nguồn chuẩn, còn faithfulness dùng context retrieval thực tế. Không lấy trung bình hai điểm thành một chỉ số tổng.

## Correctness, relevancy và hành vi

| Chỉ số | Điểm | n |
|---|---:|---:|
| Semantic correctness | 0,5089 | 564 |
| Answer relevancy | 0,5374 | 629 |
| Intent coverage | 0,4357 | 622 |
| Negative-constraint pass | 0,8104 | 385 |
| False-premise rejection | 0,9943 | 176 |
| OOD correctness | 1,0000 | 167 |
| Abstention correctness | 0,0452 | 155 |
| False refusal | 0,0679 | 604 |
| Unsupported answer | 0,1892 | 613 |

Groundedness cao không kéo theo correctness cao: mô hình có thể bám context nhưng chọn sai phần, thiếu ý định hoặc trả lời chưa đủ. Điểm abstention thấp cho thấy xử lý các trường hợp cần từ chối vẫn là điểm yếu.

## Phân tích claim và citation

| Chỉ số | Điểm | n |
|---|---:|---:|
| Unsupported-claim rate | 0,2347 | 363 |
| Hallucination rate | 0,1092 | 363 |
| Citation precision | 0,1939 | 570 |
| Citation recall | 0,1991 | 570 |
| Invalid-citation rate | 0,1114 | 570 |

Unsupported claim không đồng nghĩa claim sai: đó là claim không đủ bằng chứng trong evidence judge nhận được. Hallucination rate chỉ tính claim bị đánh dấu contradicted. Citation precision/recall thấp cho thấy cần cải thiện liên kết claim–nguồn ngay cả khi nội dung tổng thể tương đối bám context.

## Kết luận

Judge xác nhận RAG có mức bám nguồn/context cao trên các mẫu đủ điều kiện, nhưng correctness, relevancy, intent coverage, abstention và citation còn hạn chế. Kết quả judge này chỉ áp dụng cho RAG; Base, QLoRA và QLoRA+RAG chưa có judgment tương đương nên chưa thể so sánh trực tiếp theo groundedness.

## Ranh giới áp dụng

- `retrieved_context_faithfulness` không áp dụng cho Base/QLoRA thuần vì không có retrieved context.
- `source_groundedness` vẫn có thể chấm Base/QLoRA bằng Golden evidence; hiện thiếu điểm vì chưa chạy cùng judge, không phải vì metric mặc nhiên vô nghĩa.
- QLoRA+RAG đủ điều kiện chấm cả hai metric nhưng artifact hiện không có `judgments.jsonl` tương ứng.
- Judge là AI reviewer, không thay thế xác nhận của chuyên gia pháp lý và không tự phân loại mức độ hậu quả của lỗi.

Nguồn: `outputs/evaluation/eval-rag-v3/judgments.jsonl` và `scores.json`.

