# Báo cáo đánh giá QLoRA v1

> **Nguồn:** `result_final/eval-qlora_v1/` · **Trạng thái:** Baseline fine-tuning lịch sử · **638/638 prediction cuối**

## Nhận định nhanh

QLoRA v1 học tốt cách diễn đạt nên BERTScore cao, nhưng EM và độ phủ dữ kiện thấp, không có căn cứ retrieval/citation. Chỉ giữ làm baseline fine-tuning.

## Bảng điểm theo nhóm

### Định tuyến

| Chỉ số | Kết quả | Số mẫu |
| :--- | ---: | ---: |
| Độ chính xác định tuyến | 0,00% | 638 |

### Sinh câu trả lời và chất lượng nội dung

| Chỉ số | Kết quả | Số mẫu |
| :--- | ---: | ---: |
| BERTScore F1 | 91,19% | 638 |
| BERTScore precision | 91,22% | 638 |
| BERTScore recall | 91,28% | 638 |
| Character Error Rate | 1,11 | 638 |
| chrF | 45,36 | 638 |
| chrF++ | 45,32 | 638 |
| Tương đồng embedding | 71,66% | 638 |
| Khớp chính xác | 4,23% | 638 |
| Bao phủ dữ kiện chính | 13,02% | 597 |
| METEOR | 47,55% | 638 |
| Khớp chính xác sau chuẩn hóa | 4,86% | 638 |
| ROUGE-1 F1 | 47,19% | 638 |
| ROUGE-1 precision | 52,12% | 638 |
| ROUGE-1 recall | 52,70% | 638 |
| ROUGE-2 F1 | 37,74% | 638 |
| ROUGE-2 precision | 40,91% | 638 |
| ROUGE-2 recall | 42,16% | 638 |
| ROUGE-L F1 | 44,82% | 638 |
| ROUGE-L precision | 48,84% | 638 |
| ROUGE-L recall | 50,27% | 638 |
| SacreBLEU | 27,24 | 638 |
| Token F1 | 47,19% | 638 |
| Token precision | 52,12% | 638 |
| Token recall | 52,70% | 638 |
| Word Error Rate | 1,21 | 638 |

### Độ bền và an toàn hành vi

| Chỉ số | Kết quả | Số mẫu |
| :--- | ---: | ---: |
| Từ chối đúng | 0,00% | 41 |
| Độ chính xác hành động | 93,57% | 638 |
| Từ chối nhầm | 0,00% | 638 |
| Tuân thủ định dạng | 100,00% | 523 |
| Câu trả lời thiếu căn cứ | 100,00% | 41 |

### Hiệu năng

| Chỉ số | Kết quả | Số mẫu |
| :--- | ---: | ---: |
| Token đầu ra | 77,88 | 638 |
| Lượt lỗi | 0,00 | 638 |
| Độ trễ sinh | 5,62 giây | 638 |
| Tốc độ sinh | 13,32 token/s | 638 |
| Lượt OOM | 0,00 | 638 |
| VRAM cực đại | 7,74 GB | 638 |
| Token prompt | 171,53 | 638 |
| Lượt timeout | 0,00 | 638 |
| Độ trễ toàn trình | 5,72 giây | 638 |
| Tổng token | 249,41 | 638 |
| Thời gian tới token đầu | 0,32 giây | 638 |

## So sánh cohort quan trọng

| Cohort | Route accuracy | Exact Match | Key-fact coverage | Tổng độ trễ |
| :--- | ---: | ---: | ---: | ---: |
| answerable | 0,00% | 4,02% | 13,02% | 5,65 giây |
| turn_type:follow_up | 0,00% | 4,09% | 14,38% | 6,03 giây |
| turn_type:new_question | 0,00% | 4,37% | 11,58% | 5,41 giây |
| unanswerable | 0,00% | 7,32% | N/A | 6,69 giây |

## Kết luận

QLoRA v1 học tốt cách diễn đạt nên BERTScore cao, nhưng EM và độ phủ dữ kiện thấp, không có căn cứ retrieval/citation. Chỉ giữ làm baseline fine-tuning.

Các metric được đọc trực tiếp từ `scores.json`; tỷ lệ hiển thị theo %, latency theo giây. Metric không áp dụng hiển thị `N/A`, không thay bằng 0.
