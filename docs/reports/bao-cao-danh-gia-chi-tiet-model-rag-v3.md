# Báo cáo kết quả đánh giá mô hình RAG v3

> Run `eval-rag-v3` · mô hình `qwen-rag` · kiến trúc `rag` · rà soát ngày 02/11/2026

## Mục tiêu

Đánh giá pipeline routing, retrieval và sinh câu trả lời bằng Qwen2.5-7B-Instruct. Retrieval, routing và generation được báo cáo riêng, không gộp thành một “điểm tổng”.

## Thiết lập đánh giá

| Hạng mục | Giá trị |
|---|---|
| Tập test | `Data/dataset_v3/test_rag/test_rag_pa1.jsonl` |
| Quy mô | 638 mẫu; SHA-256 `f62867a7a0af3cba543c9602392a82e7c4f5912fe1e97b0b22e3c7b4bf1b3583` |
| Endpoint | `http://127.0.0.1:8000/api/chat` |
| Sinh | `qwen2.5:7b`, temperature 0, seed 42, `num_ctx=8192`, `num_predict=512`, `top_k=15` |
| Pipeline | Routing + hybrid retrieval + reranking + generation |
| Độ phủ file prediction | 638 dòng / 638 ID duy nhất |
| Kết quả thực thi trong file | 611 success / 27 error |

File `predictions.jsonl` thực sự có đủ 638 case. Trong đó 611 dòng chứa prediction thành công; 27 dòng còn lại là bản ghi giữ chỗ có `execution.status=error`, `generation=null` và telemetry không khả dụng. Vì vậy tập ID hoàn chỉnh 638/638 nhưng tập câu trả lời dùng được là 611/638.

## Cấu hình máy và phạm vi chứng cứ

Preflight cùng đợt output ghi Windows 10 build 19045, Python 3.11.9, PyTorch 2.9.1+cu130, CUDA 13.0 và RTX 5060 Ti 15,90 GiB VRAM, hỗ trợ BF16. Run ghi phép đo metric trên `cuda`, nhưng không ghi GPU/CPU/RAM của chính tiến trình inference. CPU, RAM, VRAM đỉnh và GPU utilization là `NOT VERIFIED`; manifest không có machine ID.

## Kết quả

| Nhóm | Chỉ số | Kết quả |
|---|---|---:|
| Retrieval | Recall@5 / nDCG@5 / MRR@5 | 0,8052 / 0,7034 / 0,6695 |
| Routing | Route accuracy | 0,8363 |
| Nội dung | Key-fact coverage | 0,1759 |
| Ngữ nghĩa | BERTScore F1 | 0,8424 |
| Từ vựng | ROUGE-1 / ROUGE-2 / ROUGE-L F1 | 0,3438 / 0,2673 / 0,3050 |
| Ký tự | chrF | 34,8825 |
| Hành vi | Action accuracy / abstention correctness | 0,7103 / 0,0452 |
| Định dạng | Format compliance | 1,0000 |
| Hiệu năng | Tổng độ trễ / retrieval / TTFT | 11.534,37 / 45,70 / 2.957,47 ms |
| Hiệu năng | Tốc độ sinh | 69,90 token/s |
| Độ dài | Prompt / completion trung bình | 3.117,35 / 228,93 token |
| Ổn định | OOM / timeout | 0 / 0 |

METEOR và embedding cosine không có aggregate hợp lệ: trạng thái là `UNAVAILABLE`, không phải 0.

## Kết quả LLM-as-a-Judge

`judgments.jsonl` chứa 638 judgment duy nhất, tương ứng 638 ID của tập test. Judge là `qwen2.5:14b`, model digest `7cdf5a0187d5c58cc5d369b255592f7841d1c4696d45a8c8a9489440385b22f6`, rubric SHA-256 `8310f9bcf483955c402d3148039f2d7e2b0f117f8bafa7abeb1b6686a573fce4`. Artifact judgment có SHA-256 `8be50ea8acfd866b8fba630699af792356e6af7d64a6926eb807146e4fda2e93`.

| Nhóm judge | Chỉ số | Điểm | Số mẫu hợp lệ |
|---|---|---:|---:|
| Đúng nội dung | Semantic correctness | 0,5089 | 564 |
| Liên quan câu hỏi | Answer relevancy | 0,5374 | 629 |
| Bao phủ ý định | Intent coverage | 0,4357 | 622 |
| Bám nguồn Golden | Source groundedness | 0,9086 | 350 |
| Trung thành context dùng để sinh | Retrieved-context faithfulness | 0,8940 | 349 |
| Claim | Unsupported-claim rate | 0,2347 | 363 |
| Claim | Hallucination rate | 0,1092 | 363 |
| Ràng buộc | Negative-constraint pass | 0,8104 | 385 |
| Tiền đề sai | False-premise rejection | 0,9943 | 176 |
| Ngoài phạm vi | OOD correctness | 1,0000 | 167 |
| Hành vi lỗi | False refusal | 0,0679 | 604 |
| Hành vi lỗi | Unsupported answer | 0,1892 | 613 |

Hai điểm groundedness/faithfulness cao cho thấy phần lớn câu trả lời có judgment hợp lệ bám nguồn/context được cung cấp. Kết quả này không phủ toàn bộ 638 mẫu: chỉ 350 và 349 mẫu đủ điều kiện tương ứng. Semantic correctness và intent coverage thấp hơn đáng kể, cho thấy một câu trả lời có thể trung thành với context nhưng vẫn chưa trả lời đúng hoặc đủ yêu cầu.

## Citation

| Chỉ số | Điểm | Số mẫu hợp lệ |
|---|---:|---:|
| Citation precision | 0,1939 | 570 |
| Citation recall | 0,1991 | 570 |
| Invalid-citation rate | 0,1114 | 570 |

Citation precision/recall còn thấp dù groundedness cao. Do đó không được dùng “có trích dẫn” làm đại diện cho việc trích đúng nguồn.

## Nhận định

RAG tăng ROUGE-1 F1 và key-fact coverage so với Base, đồng thời đạt Recall@5 0,8052. Judge bổ sung bằng chứng trực tiếp hơn similarity: groundedness 0,9086 và faithfulness 0,8940 trên các tập con hợp lệ, nhưng semantic correctness chỉ 0,5089 và citation precision 0,1939. Đổi lại, prompt vượt 3.100 token và tổng độ trễ trung bình lên 11,53 giây. Route accuracy 0,8363 và 27 lỗi thực thi trong prediction contract cho thấy pipeline chưa đạt độ hoàn chỉnh vận hành.

## Hạn chế

- Metric retrieval dùng denominator hợp lệ do scorer xác định, không đồng nhất với toàn bộ 638 mẫu.
- Judge chỉ có cho RAG; không dùng các điểm này để xếp hạng đủ bốn mô hình.
- Denominator thay đổi theo metric judge và được ghi riêng; không quy điểm trên tập con thành tỷ lệ của toàn bộ 638 mẫu.
- Artifact được bổ sung vẫn ghi 27 lỗi trong `predictions.jsonl` và sidecar. Cần một prediction artifact mới xác nhận 638 success trước khi công bố inference hoàn tất.
- Nguồn: `outputs/evaluation/eval-rag-v3`, gồm `judgments.jsonl` và file failed-attempt hiện có.

