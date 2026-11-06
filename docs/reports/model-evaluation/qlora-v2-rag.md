# Báo cáo đánh giá QLoRA v2 + RAG

> Nguồn: `result_final/eval-qlora_v2-rag/` · Dataset PA1: 638 case · Thực thi: 637 thành công, 1 lỗi.

## Kết luận nhanh

QLoRA v2 + RAG vẫn dẫn đầu phần lớn chỉ số tương đồng đáp án và citation trong nhóm RAG, đồng thời nhanh hơn RAG thuần và QLoRA v1 + RAG. Tuy nhiên lần predict lại chưa xác nhận bản sửa hồi quy đã đạt: một case lỗi HTTP 502, 97/97 case mất ý định lựa chọn không truy xuất trúng context chuẩn, và 9/13 case thiếu bằng chứng vẫn trả `action=answer`. Model chưa production-ready.

## Kiểm tra 107 case hồi quy

| Nhóm lỗi | Tổng | Chạy thành công | Kết quả kiểm tra assertion |
| :--- | ---: | ---: | :--- |
| Mất ý định sau khi chọn thủ tục | 97 | 97 | 0/97 truy xuất trúng context chuẩn; chỉ 1 output thay đổi |
| Bị cắt do hết token | 3 | 2 | 0/2 case thành công còn `finish_reason=length`; 1 case HTTP 502 |
| `answer` khi nội dung thiếu thông tin | 13 | 13 | Còn 9/13 case vi phạm; chỉ 3 output thay đổi |

Case chưa chạy thành công là `GOLDEN_V3_001616`: `HTTPError: HTTP Error 502: Bad Gateway`. `status=success` chỉ chứng minh request hoàn tất, không chứng minh hành vi đúng.

## Chỉ số tổng thể

### Định tuyến và truy vấn

| Chỉ số | Kết quả | Số mẫu |
| :--- | ---: | ---: |
| Route accuracy | 83,83% | 637 |
| Query rewrite similarity | 62,50% | 637 |
| Sub-query precision / recall | 0,00% / 0,00% | 107 |
| Multi-intent retrieval coverage | 0,00% | 107 |

### Truy xuất

| Chỉ số | Kết quả | Số mẫu |
| :--- | ---: | ---: |
| Context precision / noise | 42,90% / 57,10% | 503 |
| Context recall | 86,75% | 503 |
| Hit@1 / @3 / @5 / @10 / @15 | 55,47% / 72,56% / 78,33% / 87,08% / 90,66% | 503 |
| Precision@1 / @3 / @5 / @10 / @15 | 55,47% / 46,02% / 44,28% / 42,90% / 42,65% | 503 |
| Recall@1 / @3 / @5 / @10 / @15 | 53,02% / 72,02% / 78,20% / 86,75% / 90,33% | 503 |
| MRR@5 / @10 / @15 | 64,67% / 65,78% / 66,07% | 503 |
| nDCG@5 / @10 / @15 | 68,05% / 70,85% / 71,86% | 503 |
| MAP@10 | 65,70% | 503 |
| MAP@5 | 54,39% | 597 |

### Sinh câu trả lời

| Chỉ số | Kết quả | Số mẫu |
| :--- | ---: | ---: |
| Exact Match / normalized EM | 20,41% / 21,51% | 637 |
| Key-fact coverage | 38,78% | 596 |
| BERTScore P / R / F1 | 90,88% / 90,40% / 90,53% | 638 |
| ROUGE-1 P / R / F1 | 52,62% / 54,42% / 47,15% | 637 |
| ROUGE-2 P / R / F1 | 45,78% / 48,69% / 43,06% | 637 |
| ROUGE-L P / R / F1 | 50,41% / 52,37% / 45,69% | 637 |
| Token precision / recall / F1 | 52,62% / 54,42% / 47,15% | 637 |
| Embedding cosine | 64,94% | 638 |
| METEOR / chrF / chrF++ / SacreBLEU | 48,94% / 47,71 / 47,23 / 36,28 | 638 |
| Character Error Rate / Word Error Rate | 2,54 / 2,48 | 638 |

BERTScore, BLEU, ROUGE và embedding chỉ đo độ tương đồng với đáp án tham chiếu; không tự chứng minh factuality hoặc groundedness.

### Citation và hành vi

| Chỉ số | Kết quả | Số mẫu |
| :--- | ---: | ---: |
| Citation precision / recall | 50,52% / 53,43% | 596 |
| Invalid citation rate | 30,35% | 596 |
| Action accuracy | 80,85% | 637 |
| False refusal | 14,91% | 637 |
| Abstention correct / unsupported answer | 36,59% / 36,59% | 41 |
| Format compliance | 100,00% | 522 |

### Hiệu năng

| Chỉ số | Kết quả | Số mẫu |
| :--- | ---: | ---: |
| Tổng độ trễ / sinh / truy xuất | 7,02 s / 6,24 s / 0,05 s | 637 |
| TTFT | 2,90 s | 532 |
| Prompt / completion / tổng token | 3269,15 / 224,83 / 3493,98 | 532 |
| Tốc độ sinh | 48,81 token/s | 532 |
| Execution failure | 0,16% | 638 |
| Timeout / OOM | 0,00% / 0,00% | 638 |

## So sánh trước và sau predict lại

| Chỉ số | Trước | Mới | Thay đổi |
| :--- | ---: | ---: | ---: |
| Exact Match | 20,06% | 20,41% | +0,35 điểm % |
| Key-fact coverage | 38,72% | 38,78% | +0,06 điểm % |
| BERTScore F1 | 90,64% | 90,53% | -0,11 điểm % |
| Citation precision | 50,86% | 50,52% | -0,33 điểm % |
| Citation recall | 54,01% | 53,43% | -0,58 điểm % |
| Invalid citation | 31,22% | 30,35% | tốt hơn 0,87 điểm % |
| Tổng độ trễ | 7,27 s | 7,02 s | nhanh hơn 0,25 s |

Chênh lệch phải đọc cùng thay đổi mẫu số: bản mới có một execution lỗi nên nhiều metric còn `n=637`, retrieval `n=503`, key-fact/citation `n=596`.

## LLM-as-a-Judge

Kết quả Judge dùng `qwen2.5:14b` trên đủ 638 case của QLoRA v2 + RAG.

| Phạm vi | Correctness | Relevancy | Intent coverage | Groundedness | Faithfulness |
| :--- | ---: | ---: | ---: | ---: | ---: |
| Toàn bộ | 48,43% | 49,76% | 45,20% | 90,10% | 91,09% |
| Follow-up | 29,64% | 32,80% | 29,10% | 91,96% | 93,47% |
| New question | 66,33% | 66,56% | 60,44% | 88,29% | 88,78% |

## Kết luận

QLoRA v2 + RAG là cấu hình mạnh nhất về EM, key-fact coverage, citation precision/recall và tổng latency trong nhóm RAG. Judge `qwen2.5:14b` đã chấm đủ 638 case, xác nhận source groundedness 90,10% và retrieved-context faithfulness 91,09%; tuy nhiên semantic correctness 48,43% và answer relevancy 49,76% vẫn thấp hơn RAG thuần, invalid citation 30,35% và unsupported answer 20,49% còn cao. Lần rerun prediction chỉ khôi phục artifact bị mất và model không thay đổi. Trước khi production cần chạy bù `GOLDEN_V3_001616`, giảm citation không hợp lệ, cải thiện abstention/unsupported answer và xác nhận trực tiếp các assertion hồi quy. Top-15 tạo đánh đổi recall cao với nhiễu lớn, nhưng kết quả hiện tại không phải ablation nên chưa chứng minh Top-15 là nguyên nhân duy nhất.
