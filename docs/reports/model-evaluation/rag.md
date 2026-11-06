# Báo cáo đánh giá RAG

> **Nguồn:** `result/eval-rag/` · **Trạng thái:** Baseline RAG · **638/638 prediction cuối**

## Nhận định nhanh

RAG có recall truy xuất cao và Judge correctness/relevancy tốt nhất trong ba hệ RAG, nhưng ngữ cảnh nhiễu, EM/citation thấp và độ trễ cao. Giữ làm baseline và phương án rollback.

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
| Độ liên quan câu trả lời (Judge) | 54,55% | 627 |
| BERTScore F1 | 87,90% | 638 |
| BERTScore precision | 86,62% | 638 |
| BERTScore recall | 89,39% | 638 |
| Character Error Rate | 4,29 | 638 |
| chrF | 36,20 | 638 |
| chrF++ | 35,20 | 638 |
| Tương đồng embedding | 58,52% | 638 |
| Khớp chính xác | 1,25% | 638 |
| Tỷ lệ hallucination | 10,68% | 369 |
| Bao phủ ý định (Judge) | 44,98% | 618 |
| Bao phủ dữ kiện chính | 17,65% | 597 |
| METEOR | 40,35% | 638 |
| Khớp chính xác sau chuẩn hóa | 1,41% | 638 |
| ROUGE-1 F1 | 33,99% | 638 |
| ROUGE-1 precision | 33,92% | 638 |
| ROUGE-1 recall | 52,51% | 638 |
| ROUGE-2 F1 | 26,42% | 638 |
| ROUGE-2 precision | 25,90% | 638 |
| ROUGE-2 recall | 40,17% | 638 |
| ROUGE-L F1 | 30,01% | 638 |
| ROUGE-L precision | 29,59% | 638 |
| ROUGE-L recall | 46,83% | 638 |
| SacreBLEU | 15,57 | 638 |
| Độ đúng ngữ nghĩa (Judge) | 52,86% | 560 |
| Token F1 | 33,99% | 638 |
| Token precision | 33,92% | 638 |
| Token recall | 52,51% | 638 |
| Tỷ lệ luận điểm thiếu căn cứ | 23,24% | 369 |
| Word Error Rate | 4,24 | 638 |

### Trích dẫn

| Chỉ số | Kết quả | Số mẫu |
| :--- | ---: | ---: |
| Độ chính xác trích dẫn | 18,68% | 597 |
| Độ bao phủ trích dẫn | 19,37% | 597 |
| Tỷ lệ trích dẫn không hợp lệ | 11,47% | 597 |

### Độ bền và an toàn hành vi

| Chỉ số | Kết quả | Số mẫu |
| :--- | ---: | ---: |
| Từ chối đúng | 4,19% | 167 |
| Độ chính xác hành động | 71,79% | 638 |
| Bác bỏ tiền đề sai | 99,47% | 188 |
| Từ chối nhầm | 7,42% | 593 |
| Tuân thủ định dạng | 100,00% | 523 |
| Tuân thủ ràng buộc phủ định | 80,94% | 404 |
| Nhận diện ngoài miền | 100,00% | 179 |
| Câu trả lời thiếu căn cứ | 14,90% | 604 |

### Hiệu năng

| Chỉ số | Kết quả | Số mẫu |
| :--- | ---: | ---: |
| Token đầu ra | 270,90 | 533 |
| Lượt lỗi | 0,00 | 638 |
| Độ trễ sinh | 11,94 giây | 638 |
| Tốc độ sinh | 70,26 token/s | 533 |
| Lượt OOM | 0,00 | 638 |
| Token prompt | 3298,30 | 533 |
| Độ trễ truy xuất | 0,05 giây | 638 |
| Lượt timeout | 0,00 | 638 |
| Độ trễ toàn trình | 12,83 giây | 638 |
| Tổng token | 3569,20 | 533 |
| Thời gian tới token đầu | 3,00 giây | 533 |

## So sánh cohort quan trọng

| Cohort | Route accuracy | Exact Match | Key-fact coverage | Tổng độ trễ |
| :--- | ---: | ---: | ---: | ---: |
| answerable | 84,59% | 1,34% | 17,65% | 13,30 giây |
| turn_type:follow_up | 87,42% | 0,31% | 9,07% | 15,84 giây |
| turn_type:new_question | 80,31% | 2,19% | 26,73% | 9,84 giây |
| unanswerable | 73,17% | 0,00% | N/A | 6,03 giây |

## Kết luận

RAG có recall truy xuất cao và Judge correctness/relevancy tốt nhất trong ba hệ RAG, nhưng ngữ cảnh nhiễu, EM/citation thấp và độ trễ cao. Giữ làm baseline và phương án rollback.

Các metric được đọc trực tiếp từ `scores.json`; tỷ lệ hiển thị theo %, latency theo giây. Metric không áp dụng hiển thị `N/A`, không thay bằng 0.
