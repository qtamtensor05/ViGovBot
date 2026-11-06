# Kết luận chung đánh giá các model ViGovBot

> Nguồn duy nhất: artifact canonical trong `result_final/`; cùng bộ PA1 gồm 638 case. Không dùng kết luận Markdown cũ làm nguồn điểm.

## So sánh chính

| Model | Thành công | EM | Key facts | BERTScore F1 | Citation P/R | Invalid citation | Latency |
| :--- | ---: | ---: | ---: | ---: | :---: | ---: | ---: |
| Base | 638/638 | 0,00% | 1,45% | 84,85% | N/A | N/A | 7,02 s |
| RAG | 638/638 | 1,25% | 17,65% | 87,90% | 18,68% / 19,37% | 11,47% | 12,83 s |
| QLoRA v1 | 638/638 | 4,23% | 13,02% | 91,19% | N/A | N/A | 5,72 s |
| QLoRA v1 + RAG | 638/638 | 12,54% | 31,09% | 89,65% | 33,25% / 33,89% | 13,32% | 9,76 s |
| QLoRA v2 | 638/638 | 0,00% | 2,10% | 86,47% | N/A | N/A | 7,65 s |
| QLoRA v2 + RAG | 637/638 | 20,41% | 38,78% | 90,53% | 50,52% / 53,43% | 30,35% | 7,02 s |

`N/A` nghĩa là kiến trúc không sinh citation/retrieval tương ứng, không phải điểm 0. QLoRA v2 + RAG có mẫu số khác vì một prediction lỗi HTTP 502; BERTScore vẫn có `n=638`, EM có `n=637`, key facts và citation có `n=596`.

## Kết luận từng model

### Base

Chỉ phù hợp làm mốc zero-shot. EM bằng 0, key-fact coverage 1,45% và không có căn cứ retrieval/citation; không phù hợp vận hành độc lập.

### RAG

Retrieval recall cao nhưng câu trả lời bám đáp án tham chiếu và citation còn thấp, latency cao nhất. Giữ làm baseline và phương án rollback; Judge correctness/relevancy hiện cao hơn hai cấu hình QLoRA + RAG.

### QLoRA v1

BERTScore cao nhất, cho thấy học tốt phong cách và miền ngôn ngữ, nhưng EM/key facts thấp và không có retrieval/citation. Chỉ nên giữ làm baseline fine-tuning.

### QLoRA v1 + RAG

Cải thiện rõ EM, key facts và citation so với RAG thuần nhưng vẫn thấp hơn QLoRA v2 + RAG. Là baseline trung gian, chưa phải ứng viên production.

### QLoRA v2

Khi tách khỏi RAG, model có EM 0% và key facts 2,10%. Checkpoint v2 phụ thuộc mạnh vào hợp đồng context RAG; không nên triển khai như plain SFT độc lập.

### QLoRA v2 + RAG

Dẫn đầu EM, key facts và citation precision/recall, đồng thời nhanh hơn RAG và QLoRA v1 + RAG. Tuy nhiên lần predict lại chưa vượt regression manifest: 0/97 case lựa chọn truy xuất trúng context chuẩn, 9/13 case thiếu bằng chứng vẫn dùng `action=answer`, và 1/638 case lỗi HTTP 502. Chưa production-ready.

## Top-15 có phải nguyên nhân model yếu?

Chưa thể kết luận nhân quả. QLoRA v2 + RAG có Recall@15 90,33%, Precision@15 42,65% và context noise 57,10%: Top-15 đem lại recall cao nhưng nhiều nhiễu. Tuy vậy các cấu hình dùng cùng retrieval vẫn cho chất lượng sinh khác nhau; routing/state, prompt, SFT và decoder cũng ảnh hưởng. Cần ablation cố định mọi biến và chỉ đổi Top-5/10/15.

## Kết luận lựa chọn chung

QLoRA v2 + RAG vẫn là nhánh hợp lý nhất để tiếp tục hardening, nhưng commit kết quả mới không chứng minh bản sửa đã chạy đúng. Cần đồng bộ runtime predict với commit sửa section intent, chạy bù case 502 và chấm assertion cho 107 case, không chỉ đếm `execution.status=success`. RAG thuần tiếp tục giữ vai trò baseline/rollback. Chưa model nào đủ bằng chứng production-ready.

## Báo cáo chi tiết

- [Base](base.md)
- [RAG](rag.md)
- [QLoRA v1](qlora-v1.md)
- [QLoRA v1 + RAG](qlora-v1-rag.md)
- [QLoRA v2](qlora-v2.md)
- [QLoRA v2 + RAG](qlora-v2-rag.md)
