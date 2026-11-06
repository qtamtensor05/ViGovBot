# Báo cáo đánh giá Base

> **Nguồn:** `result/eval-base/` · **Trạng thái:** Baseline zero-shot · **638/638 prediction cuối**

## Nhận định nhanh

Base chỉ phù hợp làm mốc zero-shot. Tốc độ tốt nhưng EM bằng 0 và độ phủ dữ kiện chính rất thấp; không phù hợp vận hành độc lập.

## Bảng điểm theo nhóm

### Định tuyến

| Chỉ số | Kết quả | Số mẫu |
| :--- | ---: | ---: |
| Độ chính xác định tuyến | 0,00% | 638 |

### Sinh câu trả lời và chất lượng nội dung

| Chỉ số | Kết quả | Số mẫu |
| :--- | ---: | ---: |
| BERTScore F1 | 84,85% | 638 |
| BERTScore precision | 82,16% | 638 |
| BERTScore recall | 87,83% | 638 |
| Character Error Rate | 11,76 | 638 |
| chrF | 20,86 | 638 |
| chrF++ | 19,93 | 638 |
| Tương đồng embedding | 53,96% | 638 |
| Khớp chính xác | 0,00% | 638 |
| Bao phủ dữ kiện chính | 1,45% | 597 |
| METEOR | 24,91% | 638 |
| Khớp chính xác sau chuẩn hóa | 0,00% | 638 |
| ROUGE-1 F1 | 16,95% | 638 |
| ROUGE-1 precision | 12,57% | 638 |
| ROUGE-1 recall | 52,30% | 638 |
| ROUGE-2 F1 | 7,75% | 638 |
| ROUGE-2 precision | 5,66% | 638 |
| ROUGE-2 recall | 26,69% | 638 |
| ROUGE-L F1 | 11,10% | 638 |
| ROUGE-L precision | 7,91% | 638 |
| ROUGE-L recall | 39,25% | 638 |
| SacreBLEU | 2,69 | 638 |
| Token F1 | 16,95% | 638 |
| Token precision | 12,57% | 638 |
| Token recall | 52,30% | 638 |
| Word Error Rate | 11,34 | 638 |

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
| Token đầu ra | 342,28 | 638 |
| Lượt lỗi | 0,00 | 638 |
| Độ trễ sinh | 6,91 giây | 638 |
| Tốc độ sinh | 72,38 token/s | 638 |
| Lượt OOM | 0,00 | 638 |
| Token prompt | 172,52 | 638 |
| Lượt timeout | 0,00 | 638 |
| Độ trễ toàn trình | 7,02 giây | 638 |
| Tổng token | 514,80 | 638 |
| Thời gian tới token đầu | 2,21 giây | 638 |

## So sánh cohort quan trọng

| Cohort | Route accuracy | Exact Match | Key-fact coverage | Tổng độ trễ |
| :--- | ---: | ---: | ---: | ---: |
| answerable | 0,00% | 0,00% | 1,45% | 7,17 giây |
| turn_type:follow_up | 0,00% | 0,00% | 0,42% | 6,77 giây |
| turn_type:new_question | 0,00% | 0,00% | 2,53% | 7,26 giây |
| unanswerable | 0,00% | 0,00% | N/A | 4,85 giây |

## Kết luận

Base chỉ phù hợp làm mốc zero-shot. Tốc độ tốt nhưng EM bằng 0 và độ phủ dữ kiện chính rất thấp; không phù hợp vận hành độc lập.

Các metric được đọc trực tiếp từ `scores.json`; tỷ lệ hiển thị theo %, latency theo giây. Metric không áp dụng hiển thị `N/A`, không thay bằng 0.
