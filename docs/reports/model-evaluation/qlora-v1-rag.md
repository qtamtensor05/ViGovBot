# Báo cáo đánh giá QLoRA v1 + RAG

> **Nguồn:** `result/eval-qlora_v1-rag/` · **Trạng thái:** Baseline tích hợp lịch sử · **638/638 prediction cuối**

## Nhận định nhanh

QLoRA v1 + RAG cải thiện EM, dữ kiện và citation so với RAG, nhưng Judge correctness/relevancy không vượt RAG. Đây là baseline trung gian, không phải ứng viên production.

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
| Độ liên quan câu trả lời (Judge) | 51,44% | 624 |
| BERTScore F1 | 89,65% | 638 |
| BERTScore precision | 90,03% | 638 |
| BERTScore recall | 89,46% | 638 |
| Character Error Rate | 2,54 | 638 |
| chrF | 41,27 | 638 |
| chrF++ | 40,55 | 638 |
| Tương đồng embedding | 64,90% | 638 |
| Khớp chính xác | 12,54% | 638 |
| Tỷ lệ hallucination | 12,58% | 436 |
| Bao phủ ý định (Judge) | 43,94% | 619 |
| Bao phủ dữ kiện chính | 31,09% | 597 |
| METEOR | 41,31% | 638 |
| Khớp chính xác sau chuẩn hóa | 13,32% | 638 |
| ROUGE-1 F1 | 42,80% | 638 |
| ROUGE-1 precision | 53,26% | 638 |
| ROUGE-1 recall | 46,16% | 638 |
| ROUGE-2 F1 | 37,39% | 638 |
| ROUGE-2 precision | 45,43% | 638 |
| ROUGE-2 recall | 39,00% | 638 |
| ROUGE-L F1 | 40,96% | 638 |
| ROUGE-L precision | 50,60% | 638 |
| ROUGE-L recall | 43,85% | 638 |
| SacreBLEU | 27,27 | 638 |
| Độ đúng ngữ nghĩa (Judge) | 49,74% | 571 |
| Token F1 | 42,80% | 638 |
| Token precision | 53,26% | 638 |
| Token recall | 46,16% | 638 |
| Tỷ lệ luận điểm thiếu căn cứ | 28,05% | 436 |
| Word Error Rate | 2,51 | 638 |

### Trích dẫn

| Chỉ số | Kết quả | Số mẫu |
| :--- | ---: | ---: |
| Độ chính xác trích dẫn | 33,25% | 597 |
| Độ bao phủ trích dẫn | 33,89% | 597 |
| Tỷ lệ trích dẫn không hợp lệ | 13,32% | 597 |

### Độ bền và an toàn hành vi

| Chỉ số | Kết quả | Số mẫu |
| :--- | ---: | ---: |
| Từ chối đúng | 3,21% | 187 |
| Độ chính xác hành động | 79,00% | 638 |
| Bác bỏ tiền đề sai | 99,53% | 212 |
| Từ chối nhầm | 10,54% | 607 |
| Tuân thủ định dạng | 100,00% | 523 |
| Tuân thủ ràng buộc phủ định | 84,77% | 394 |
| Nhận diện ngoài miền | 100,00% | 208 |
| Câu trả lời thiếu căn cứ | 16,05% | 623 |

### Hiệu năng

| Chỉ số | Kết quả | Số mẫu |
| :--- | ---: | ---: |
| Token đầu ra | 218,39 | 533 |
| Lượt lỗi | 0,00 | 638 |
| Độ trễ sinh | 8,90 giây | 638 |
| Tốc độ sinh | 45,24 token/s | 533 |
| Lượt OOM | 0,00 | 638 |
| Token prompt | 3252,56 | 533 |
| Độ trễ truy xuất | 0,05 giây | 638 |
| Lượt timeout | 0,00 | 638 |
| Độ trễ toàn trình | 9,76 giây | 638 |
| Tổng token | 3470,95 | 533 |
| Thời gian tới token đầu | 2,89 giây | 533 |

## So sánh cohort quan trọng

| Cohort | Route accuracy | Exact Match | Key-fact coverage | Tổng độ trễ |
| :--- | ---: | ---: | ---: | ---: |
| answerable | 84,59% | 13,40% | 31,09% | 10,07 giây |
| turn_type:follow_up | 87,42% | 9,12% | 20,76% | 12,49 giây |
| turn_type:new_question | 80,31% | 15,94% | 42,03% | 7,05 giây |
| unanswerable | 73,17% | 0,00% | N/A | 5,24 giây |

## Kết luận

QLoRA v1 + RAG cải thiện EM, dữ kiện và citation so với RAG, nhưng Judge correctness/relevancy không vượt RAG. Đây là baseline trung gian, không phải ứng viên production.

Các metric được đọc trực tiếp từ `scores.json`; tỷ lệ hiển thị theo %, latency theo giây. Metric không áp dụng hiển thị `N/A`, không thay bằng 0.
