# Báo cáo đánh giá QLoRA v2

> **Nguồn:** `result/eval-qlora_v2/` · **Trạng thái:** RAG-SFT chạy độc lập, không có retrieval · **638/638 prediction cuối**

## Nhận định nhanh

QLoRA v2 chạy độc lập không phát huy được hợp đồng huấn luyện dựa trên evidence: EM bằng 0, độ phủ dữ kiện chính 2,10% và không có retrieval/citation. `action_accuracy` cao phản ánh phần lớn benchmark là ca answerable, không chứng minh khả năng từ chối an toàn; model trả lời thiếu căn cứ ở 100% trong 41 ca unanswerable.

## Bảng điểm theo nhóm

### Định tuyến

| Chỉ số | Kết quả | Số mẫu |
| :--- | ---: | ---: |
| Độ chính xác định tuyến | 0,00% | 638 |

### Sinh câu trả lời và chất lượng nội dung

| Chỉ số | Kết quả | Số mẫu |
| :--- | ---: | ---: |
| BERTScore F1 | 86,47% | 638 |
| BERTScore precision | 84,90% | 638 |
| BERTScore recall | 88,27% | 638 |
| Character Error Rate | 8,20 | 638 |
| chrF | 26,21 | 638 |
| chrF++ | 25,67 | 638 |
| Tương đồng embedding | 57,03% | 638 |
| Khớp chính xác | 0,00% | 638 |
| Bao phủ dữ kiện chính | 2,10% | 597 |
| METEOR | 30,51% | 638 |
| Khớp chính xác sau chuẩn hóa | 0,00% | 638 |
| ROUGE-1 F1 | 25,36% | 638 |
| ROUGE-1 precision | 24,16% | 638 |
| ROUGE-1 recall | 46,14% | 638 |
| ROUGE-2 F1 | 14,94% | 638 |
| ROUGE-2 precision | 14,10% | 638 |
| ROUGE-2 recall | 28,24% | 638 |
| ROUGE-L F1 | 19,89% | 638 |
| ROUGE-L precision | 18,65% | 638 |
| ROUGE-L recall | 37,68% | 638 |
| SacreBLEU | 6,78 | 638 |
| Token F1 | 25,36% | 638 |
| Token precision | 24,16% | 638 |
| Token recall | 46,14% | 638 |
| Word Error Rate | 7,59 | 638 |

### Độ bền và an toàn hành vi

| Chỉ số | Kết quả | Số mẫu |
| :--- | ---: | ---: |
| Từ chối đúng | 0,00% | 41 |
| Độ chính xác hành động | 93,57% | 638 |
| Từ chối nhầm | 0,00% | 638 |
| Tuân thủ định dạng | 100,00% | 523 |
| Câu trả lời thiếu căn cứ | 100,00% | 41 |

`action_accuracy` 93,57% bằng đúng tỷ lệ 597/638 ca answerable. Kết quả cohort cho thấy 597 ca answerable đạt 100% nhưng 41 ca unanswerable đạt 0%; do đó không được dùng chỉ số tổng này để kết luận model biết từ chối.

### Hiệu năng

| Chỉ số | Kết quả | Số mẫu |
| :--- | ---: | ---: |
| Token đầu ra | 267,01 | 638 |
| Lượt lỗi | 0,00 | 638 |
| Độ trễ sinh | 7,55 giây | 638 |
| Tốc độ sinh | 48,65 token/s | 638 |
| Lượt OOM | 0,00 | 638 |
| Token prompt | 151,52 | 638 |
| Lượt timeout | 0,00 | 638 |
| Độ trễ toàn trình | 7,65 giây | 638 |
| Tổng token | 418,53 | 638 |
| Thời gian tới token đầu | 2,20 giây | 638 |

## So sánh cohort quan trọng

| Cohort | Route accuracy | Exact Match | Key-fact coverage | Tổng độ trễ |
| :--- | ---: | ---: | ---: | ---: |
| answerable | 0,00% | 0,00% | 2,10% | 7,89 giây |
| turn_type:follow_up | 0,00% | 0,00% | 2,12% | 7,43 giây |
| turn_type:new_question | 0,00% | 0,00% | 2,07% | 7,88 giây |
| unanswerable | 0,00% | 0,00% | N/A | 4,18 giây |

## Kết luận

QLoRA v2 không nên được triển khai độc lập. Kết quả này cho thấy checkpoint cần context/evidence từ pipeline RAG, nhưng không tự chứng minh chất lượng của cấu hình kết hợp. BERTScore và các metric tương đồng không thay thế kiểm chứng factuality hoặc groundedness.

Các metric được đọc trực tiếp từ `scores.json`; tỷ lệ hiển thị theo %, latency theo giây. Metric không áp dụng hiển thị `N/A`, không thay bằng 0.
