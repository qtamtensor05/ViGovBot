# Báo cáo đánh giá QLoRA v2 + RAG

> **Nguồn:** `result_final/eval-qlora_v2-rag/` · **Trạng thái:** Ứng viên tiếp tục hardening · **638/638 prediction cuối**

## Nhận định nhanh

QLoRA v2 + RAG dẫn đầu phần lớn metric đáp án và citation, đồng thời nhanh hơn hai cấu hình RAG còn lại. Tuy nhiên follow-up và trích dẫn không hợp lệ còn yếu; ưu tiên hardening, chưa production-ready.

## Bảng điểm theo nhóm

### Định tuyến

| Chỉ số | Kết quả | Số mẫu |
| :--- | ---: | ---: |
| Độ chính xác định tuyến | 83,86% | 638 |

### Xử lý truy vấn

| Chỉ số | Kết quả | Số mẫu |
| :--- | ---: | ---: |
| Độ tương đồng câu viết lại | 62,51% | 638 |
| Độ chính xác truy vấn con | 0,00% | 107 |
| Độ bao phủ truy vấn con | 0,00% | 107 |

### Truy xuất

| Chỉ số | Kết quả | Số mẫu |
| :--- | ---: | ---: |
| Tỷ lệ nhiễu ngữ cảnh | 56,98% | 504 |
| Độ chính xác ngữ cảnh | 43,02% | 504 |
| Độ bao phủ ngữ cảnh | 86,71% | 504 |
| Hit@1 | 55,56% | 504 |
| Hit@10 | 87,10% | 504 |
| Hit@15 | 90,67% | 504 |
| Hit@3 | 72,62% | 504 |
| Hit@5 | 78,37% | 504 |
| MAP@10 | 65,77% | 504 |
| MAP@5 | 54,56% | 597 |
| MRR@10 | 65,85% | 504 |
| MRR@15 | 66,14% | 504 |
| MRR@5 | 64,74% | 504 |
| Bao phủ truy vấn đa ý định | 0,00% | 107 |
| nDCG@10 | 70,91% | 504 |
| nDCG@15 | 71,92% | 504 |
| nDCG@5 | 68,12% | 504 |
| Precision@1 | 55,56% | 504 |
| Precision@10 | 43,02% | 504 |
| Precision@15 | 42,76% | 504 |
| Precision@3 | 46,13% | 504 |
| Precision@5 | 44,39% | 504 |
| Recall@1 | 52,92% | 504 |
| Recall@10 | 86,71% | 504 |
| Recall@15 | 90,35% | 504 |
| Recall@3 | 71,91% | 504 |
| Recall@5 | 78,11% | 504 |

### Sinh câu trả lời và chất lượng nội dung

| Chỉ số | Kết quả | Số mẫu |
| :--- | ---: | ---: |
| BERTScore F1 | 90,64% | 638 |
| BERTScore precision | 90,98% | 638 |
| BERTScore recall | 90,51% | 638 |
| Character Error Rate | 2,62 | 638 |
| chrF | 47,62 | 638 |
| chrF++ | 47,15 | 638 |
| Tương đồng embedding | 65,00% | 638 |
| Khớp chính xác | 20,06% | 638 |
| Bao phủ dữ kiện chính | 38,72% | 597 |
| METEOR | 48,88% | 638 |
| Khớp chính xác sau chuẩn hóa | 21,47% | 638 |
| ROUGE-1 F1 | 47,00% | 638 |
| ROUGE-1 precision | 52,60% | 638 |
| ROUGE-1 recall | 54,34% | 638 |
| ROUGE-2 F1 | 42,93% | 638 |
| ROUGE-2 precision | 45,77% | 638 |
| ROUGE-2 recall | 48,62% | 638 |
| ROUGE-L F1 | 45,55% | 638 |
| ROUGE-L precision | 50,39% | 638 |
| ROUGE-L recall | 52,29% | 638 |
| SacreBLEU | 36,19 | 638 |
| Token F1 | 47,00% | 638 |
| Token precision | 52,60% | 638 |
| Token recall | 54,34% | 638 |
| Word Error Rate | 2,51 | 638 |

### Trích dẫn

| Chỉ số | Kết quả | Số mẫu |
| :--- | ---: | ---: |
| Độ chính xác trích dẫn | 50,86% | 597 |
| Độ bao phủ trích dẫn | 54,01% | 597 |
| Tỷ lệ trích dẫn không hợp lệ | 31,22% | 597 |

### Độ bền và an toàn hành vi

| Chỉ số | Kết quả | Số mẫu |
| :--- | ---: | ---: |
| Từ chối đúng | 36,59% | 41 |
| Độ chính xác hành động | 80,88% | 638 |
| Từ chối nhầm | 14,89% | 638 |
| Tuân thủ định dạng | 100,00% | 523 |
| Câu trả lời thiếu căn cứ | 36,59% | 41 |

### Hiệu năng

| Chỉ số | Kết quả | Số mẫu |
| :--- | ---: | ---: |
| Token đầu ra | 230,24 | 533 |
| Lượt lỗi | 0,00 | 638 |
| Độ trễ sinh | 6,49 giây | 638 |
| Tốc độ sinh | 48,77 token/s | 533 |
| Lượt OOM | 0,00 | 638 |
| Token prompt | 3277,90 | 533 |
| Độ trễ truy xuất | 0,05 giây | 638 |
| Lượt timeout | 0,00 | 638 |
| Độ trễ toàn trình | 7,27 giây | 638 |
| Tổng token | 3508,14 | 533 |
| Thời gian tới token đầu | 2,92 giây | 533 |

## So sánh cohort quan trọng

| Cohort | Route accuracy | Exact Match | Key-fact coverage | Tổng độ trễ |
| :--- | ---: | ---: | ---: | ---: |
| answerable | 84,59% | 21,44% | 38,72% | 7,39 giây |
| turn_type:follow_up | 87,42% | 12,89% | 23,53% | 7,59 giây |
| turn_type:new_question | 80,31% | 27,19% | 54,80% | 6,96 giây |
| unanswerable | 73,17% | 0,00% | N/A | 5,64 giây |

## LLM-as-a-Judge

| Phạm vi | Correctness | Relevancy | Intent coverage | Groundedness | Faithfulness |
| :--- | ---: | ---: | ---: | ---: | ---: |
| Toàn bộ | 48,43% | 49,76% | 45,20% | 90,10% | 91,09% |
| follow_up | 29,64% | 32,80% | 29,10% | 91,96% | 93,47% |
| new_question | 66,33% | 66,56% | 60,44% | 88,29% | 88,78% |

## Kết luận

QLoRA v2 + RAG dẫn đầu phần lớn metric đáp án và citation, đồng thời nhanh hơn hai cấu hình RAG còn lại. Tuy nhiên follow-up và trích dẫn không hợp lệ còn yếu; ưu tiên hardening, chưa production-ready.

Các metric được đọc trực tiếp từ `scores.json`; tỷ lệ hiển thị theo %, latency theo giây. Metric không áp dụng hiển thị `N/A`, không thay bằng 0.
