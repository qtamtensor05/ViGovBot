# Tổng hợp đánh giá các model ViGovBot

> Nguồn: artifact canonical trong `result/`; benchmark PA1 gồm 638 case. Các tỷ lệ luôn đi cùng mẫu số vì không phải metric nào cũng áp dụng cho toàn bộ case.

## Tổng quan sáu cấu hình

| Model | Thực thi | EM | EM chuẩn hóa | Key facts | BERTScore F1 | SacreBLEU | Action accuracy | Latency |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Base | 638/638 | 0,00% | 0,00% | 1,45% (`n=597`) | 84,85% | 2,69 | 93,57% | 7,02 s |
| RAG | 638/638 | 1,25% | 1,41% | 17,65% (`n=597`) | 87,90% | 15,57 | 71,79% | 12,83 s |
| QLoRA v1 | 638/638 | 4,23% | 4,86% | 13,02% (`n=597`) | **91,19%** | 27,24 | 93,57% | **5,72 s** |
| QLoRA v1 + RAG | 638/638 | 12,54% | 13,32% | 31,09% (`n=597`) | 89,65% | 27,27 | 79,00% | 9,76 s |
| QLoRA v2 | 638/638 | 0,00% | 0,00% | 2,10% (`n=597`) | 86,47% | 6,78 | 93,57% | 7,65 s |
| QLoRA v2 + RAG | 637/638 | **20,41%** (`n=637`) | **21,51%** (`n=637`) | **38,78%** (`n=596`) | 90,53% | **36,28** | **80,85%** (`n=637`) | 7,02 s |

`Action accuracy` 93,57% của ba model không dùng RAG không đồng nghĩa với khả năng từ chối tốt: cả Base, QLoRA v1 và QLoRA v2 đều đạt 0% `abstention_correct` và 100% `unsupported_answer` trên 41 ca unanswerable. QLoRA v2 + RAG có một prediction lỗi HTTP 502; BERTScore/SacreBLEU vẫn có `n=638`, còn các metric phụ thuộc prediction hợp lệ dùng mẫu số nhỏ hơn.

## So sánh ba hệ RAG

### Truy xuất và trích dẫn

| Metric | RAG | QLoRA v1 + RAG | QLoRA v2 + RAG |
| :--- | ---: | ---: | ---: |
| Route accuracy | 83,86% (`n=638`) | 83,86% (`n=638`) | 83,83% (`n=637`) |
| Context precision | 43,02% (`n=504`) | 43,02% (`n=504`) | 42,90% (`n=503`) |
| Context recall | 86,71% (`n=504`) | 86,71% (`n=504`) | 86,75% (`n=503`) |
| Recall@15 | 90,35% (`n=504`) | 90,35% (`n=504`) | 90,33% (`n=503`) |
| Context noise | 56,98% (`n=504`) | 56,98% (`n=504`) | 57,10% (`n=503`) |
| Citation precision | 18,68% (`n=597`) | 33,25% (`n=597`) | **50,52%** (`n=596`) |
| Citation recall | 19,37% (`n=597`) | 33,89% (`n=597`) | **53,43%** (`n=596`) |
| Invalid citation | **11,47%** (`n=597`) | 13,32% (`n=597`) | 30,35% (`n=596`) |

Ba hệ dùng retrieval gần như tương đương; khác biệt lớn chủ yếu xuất hiện ở cách model sử dụng context và sinh citation. QLoRA v2 + RAG tăng mạnh độ phủ citation nhưng cũng có tỷ lệ citation không hợp lệ cao nhất. Vì vậy không nên đọc citation recall riêng lẻ như bằng chứng trích dẫn đáng tin cậy.

### LLM-as-a-Judge

Cả ba cấu hình được Judge bằng `qwen2.5:14b` trên đủ 638 case. Mẫu số dưới đây khác nhau theo điều kiện áp dụng của từng rubric.

| Metric Judge | RAG | QLoRA v1 + RAG | QLoRA v2 + RAG |
| :--- | ---: | ---: | ---: |
| Semantic correctness | **52,86%** (`n=560`) | 49,74% (`n=571`) | 48,43% (`n=574`) |
| Answer relevancy | **54,55%** (`n=627`) | 51,44% (`n=624`) | 49,76% (`n=631`) |
| Intent coverage | 44,98% (`n=618`) | 43,94% (`n=619`) | **45,20%** (`n=615`) |
| Source groundedness | 90,68% (`n=354`) | **91,14%** (`n=395`) | 90,10% (`n=404`) |
| Retrieved-context faithfulness | 89,24% (`n=353`) | **91,65%** (`n=395`) | 91,09% (`n=404`) |
| Negative-constraint pass | 80,94% (`n=404`) | **84,77%** (`n=394`) | 83,42% (`n=404`) |
| False-premise rejection | 99,47% (`n=188`) | **99,53%** (`n=212`) | 99,12% (`n=227`) |
| OOD correctness | 100,00% (`n=179`) | 100,00% (`n=208`) | 100,00% (`n=213`) |
| False refusal ↓ | 7,42% (`n=593`) | 10,54% (`n=607`) | **7,13%** (`n=603`) |
| Unsupported answer ↓ | **14,90%** (`n=604`) | 16,05% (`n=623`) | 20,49% (`n=615`) |
| Abstention correct | **4,19%** (`n=167`) | 3,21% (`n=187`) | 1,50% (`n=200`) |

Judge cho thấy QLoRA v2 + RAG không thắng toàn bộ: model dẫn nhẹ về intent coverage và có false-refusal thấp nhất, nhưng RAG thuần cao nhất về semantic correctness, answer relevancy và abstention; QLoRA v1 + RAG cao nhất về groundedness/faithfulness. Dù vậy, ba hệ đều có `abstention_correct` rất thấp, nên xử lý câu hỏi thiếu bằng chứng vẫn là điểm yếu chung.

### Hiệu năng

| Metric | RAG | QLoRA v1 + RAG | QLoRA v2 + RAG |
| :--- | ---: | ---: | ---: |
| Tổng độ trễ | 12,83 s (`n=638`) | 9,76 s (`n=638`) | **7,02 s** (`n=637`) |
| Độ trễ sinh | 11,94 s (`n=638`) | 8,90 s (`n=638`) | **6,24 s** (`n=637`) |
| TTFT | 3,00 s (`n=533`) | **2,89 s** (`n=533`) | 2,90 s (`n=532`) |
| Tốc độ sinh | **70,26 token/s** (`n=533`) | 45,24 token/s (`n=533`) | 48,81 token/s (`n=532`) |
| Tổng token | 3569,20 (`n=533`) | 3470,95 (`n=533`) | 3493,98 (`n=532`) |

QLoRA v2 + RAG có tổng latency thấp nhất dù tốc độ token không cao nhất; điều này phản ánh khác biệt về độ dài output và thời gian sinh toàn trình, không chỉ throughput decoder.

## So sánh trực tiếp QLoRA v1 + RAG và QLoRA v2 + RAG

- V2 tăng EM từ 12,54% lên 20,41%, key-fact coverage từ 31,09% lên 38,78%, citation precision từ 33,25% lên 50,52% và citation recall từ 33,89% lên 53,43%.
- V2 giảm tổng latency từ 9,76 giây xuống 7,02 giây.
- Đổi lại, invalid citation tăng từ 13,32% lên 30,35%; Judge semantic correctness giảm từ 49,74% xuống 48,43%, answer relevancy giảm từ 51,44% xuống 49,76%, và unsupported answer tăng từ 16,05% lên 20,49%.
- V1 + RAG nhỉnh hơn về source groundedness (91,14% so với 90,10%) và context faithfulness (91,65% so với 91,09%), nhưng v2 có intent coverage cao hơn (45,20% so với 43,94%).

## Kết luận từng model

### Base

Chỉ phù hợp làm mốc zero-shot. EM bằng 0, key-fact coverage 1,45%, không có retrieval/citation và không từ chối đúng các ca unanswerable.

### RAG

Là baseline retrieval/rollback: recall cao, invalid citation thấp nhất và Judge correctness/relevancy tốt nhất trong ba hệ RAG. Điểm yếu là EM, key facts, citation coverage thấp và latency cao nhất.

### QLoRA v1

Có BERTScore cao nhất và latency thấp nhất, cho thấy lợi thế về tương đồng cách diễn đạt và tốc độ. Tuy nhiên EM/key facts thấp, không có căn cứ retrieval/citation và không xử lý đúng ca unanswerable; chỉ nên giữ làm baseline fine-tuning.

### QLoRA v1 + RAG

Là cấu hình cân bằng trung gian: cải thiện rõ EM/citation so với RAG, đồng thời đạt groundedness và faithfulness Judge cao nhất. Tuy nhiên vẫn thua v2 về EM, key facts, citation coverage và latency.

### QLoRA v2

Không phù hợp chạy độc lập: EM bằng 0, key-fact coverage 2,10% và không từ chối đúng ca unanswerable. Kết quả xác nhận checkpoint cần context/evidence của pipeline RAG.

### QLoRA v2 + RAG

Là ứng viên tốt nhất để tiếp tục hardening nhờ dẫn đầu EM, key facts, citation precision/recall và tổng latency trong nhóm RAG. Judge đã chấm đủ 638 case và xác nhận groundedness/faithfulness quanh 90–91%, nhưng model chưa thắng RAG thuần về correctness/relevancy, chưa thắng v1 + RAG về groundedness/faithfulness, đồng thời invalid citation và unsupported answer còn cao. Lần rerun prediction chỉ khôi phục artifact bị mất, model không thay đổi.

## Kết luận lựa chọn chung

Không có một model thắng trên mọi tiêu chí. Nếu ưu tiên khớp đáp án, dữ kiện, độ phủ citation và latency, QLoRA v2 + RAG là lựa chọn tốt nhất. Nếu ưu tiên Judge correctness/relevancy và citation hợp lệ, RAG thuần vẫn là baseline quan trọng; QLoRA v1 + RAG cho điểm cân bằng tốt hơn về groundedness/faithfulness. Trước khi production, QLoRA v2 + RAG cần giảm invalid citation, cải thiện abstention/unsupported answer, chạy bù case HTTP 502 và xác nhận các assertion hồi quy. Việc này không yêu cầu chấm lại Judge vì model không thay đổi và bộ Judge hiện tại đã đủ 638 case.

## Top-15 có phải nguyên nhân model yếu?

Chưa thể kết luận nhân quả. QLoRA v2 + RAG có Recall@15 90,33%, Precision@15 42,65% và context noise 57,10%: Top-15 tăng recall nhưng đưa nhiều nhiễu. Vì ba cấu hình RAG dùng retrieval gần tương đương mà chất lượng sinh khác nhau, routing/state, prompt, SFT và decoder cũng ảnh hưởng. Cần ablation cố định các biến khác và chỉ đổi Top-5/10/15.

## Báo cáo chi tiết

- [Base](base.md)
- [RAG](rag.md)
- [QLoRA v1](qlora-v1.md)
- [QLoRA v1 + RAG](qlora-v1-rag.md)
- [QLoRA v2](qlora-v2.md)
- [QLoRA v2 + RAG](qlora-v2-rag.md)
