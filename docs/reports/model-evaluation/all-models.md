# Kết luận chung đánh giá các model ViGovBot

> Nguồn duy nhất: năm thư mục canonical trong `result_final/`; cùng 638 mẫu PA1.

## Bảng so sánh dễ đọc

| Model | EM | Key facts | BERTScore | Citation P/R | Invalid citation | Judge correctness / relevancy | Latency |
| :--- | ---: | ---: | ---: | :---: | ---: | :---: | ---: |
| Base | 0,00% | 1,45% | 84,85% | N/A / N/A | N/A | N/A / N/A | 7,02 giây |
| RAG | 1,25% | 17,65% | 87,90% | 18,68% / 19,37% | 11,47% | 52,86% / 54,55% | 12,83 giây |
| QLoRA v1 | 4,23% | 13,02% | 91,19% | N/A / N/A | N/A | N/A / N/A | 5,72 giây |
| QLoRA v1 + RAG | 12,54% | 31,09% | 89,65% | 33,25% / 33,89% | 13,32% | 49,74% / 51,44% | 9,76 giây |
| QLoRA v2 + RAG | 20,06% | 38,72% | 90,64% | 50,86% / 54,01% | 31,22% | 48,43% / 49,76% | 7,27 giây |

## Kết luận từng model

### Base

Base chỉ phù hợp làm mốc zero-shot. Tốc độ tốt nhưng EM bằng 0 và độ phủ dữ kiện chính rất thấp; không phù hợp vận hành độc lập.

### RAG

RAG có recall truy xuất cao và Judge correctness/relevancy tốt nhất trong ba hệ RAG, nhưng ngữ cảnh nhiễu, EM/citation thấp và độ trễ cao. Giữ làm baseline và phương án rollback.

### QLoRA v1

QLoRA v1 học tốt cách diễn đạt nên BERTScore cao, nhưng EM và độ phủ dữ kiện thấp, không có căn cứ retrieval/citation. Chỉ giữ làm baseline fine-tuning.

### QLoRA v1 + RAG

QLoRA v1 + RAG cải thiện EM, dữ kiện và citation so với RAG, nhưng Judge correctness/relevancy không vượt RAG. Đây là baseline trung gian, không phải ứng viên production.

### QLoRA v2 + RAG

QLoRA v2 + RAG dẫn đầu phần lớn metric đáp án và citation, đồng thời nhanh hơn hai cấu hình RAG còn lại. Tuy nhiên follow-up và trích dẫn không hợp lệ còn yếu; ưu tiên hardening, chưa production-ready.

## Top-15 có phải nguyên nhân model yếu?

Chưa thể kết luận. Ba hệ RAG cùng đạt Recall@15 90,35%, Precision@15 42,76% và Context Noise 56,98%. Top-15 rõ ràng tạo đánh đổi: recall cao nhưng nhiều nhiễu. Tuy nhiên ba model dùng cùng retrieval lại cho chất lượng sinh khác nhau, nên SFT, prompt, decoder và state/routing cũng ảnh hưởng. Cần ablation cố định mọi biến và chỉ đổi Top-5/10/15 mới xác định được quan hệ nhân quả.

## Kết luận lựa chọn chung

QLoRA v2 + RAG là nhánh hợp lý nhất để tiếp tục hardening vì dẫn đầu EM, key facts và citation precision/recall, đồng thời có latency tốt hơn RAG và v1 + RAG. RAG thuần vẫn cần giữ làm baseline/rollback vì Judge correctness và relevancy cao hơn. Chưa model nào đủ bằng chứng production-ready; ưu tiên tiếp theo là follow-up, citation validation, routing regression và ablation Top-K.

## Báo cáo chi tiết

- [Base](base.md)
- [RAG](rag.md)
- [QLoRA v1](qlora-v1.md)
- [QLoRA v1 + RAG](qlora-v1-rag.md)
- [QLoRA v2 + RAG](qlora-v2-rag.md)
