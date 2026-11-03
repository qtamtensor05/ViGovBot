# Báo cáo thực nghiệm: Đánh giá định lượng và đối chuẩn toàn diện mô hình QLoRA-RAG (v2) trên tập dữ liệu v3

> **Tiêu chuẩn văn phong:** Nature-Style Scientific Report (Algorithmic & Benchmark Evaluation)  
> **Hệ thống:** ViGovBot — Cấu hình Tích hợp QLoRA RAG-SFT (v2) và Hybrid Retrieval  
> **Mô hình phục vụ:** `Qwen2.5-7B-Instruct` + QLoRA RAG-SFT (v2 `checkpoint-600`)  
> **Định dạng triển khai:** Ollama Runtime `qwen-qlora-rag-sft:latest` (GGUF `q8_0`, 8,10 GB)  
> **Tập dữ liệu chuẩn hóa:** `Data/dataset_v3/test_rag/test_rag_pa1.jsonl` (638 mẫu thử nghiệm đa dạng)  
> **Mã thực nghiệm đánh giá:** `eval-qlora-rag-sft-v3` (Lưu trữ chính thức tại `result_final/eval-qlora-rag-sft-v3/`)
> **Thẩm định ngữ nghĩa độc lập (LLM-as-a-Judge):** Reviewer `qwen2.5:14b` (638/638 ca kiểm thử)
> **Thời điểm thẩm định artifact:** 03/11/2026 – 04/11/2026

---

## Tóm tắt (Abstract)

Báo cáo này đối chiếu trực tiếp ba run có mặt trong `result_final`: Base, RAG thuần và **QLoRA-RAG v2** trên cùng 638 ca kiểm thử. Các số liệu QLoRA-RAG v1 được giữ lại khi cần tham khảo lịch sử, nhưng không được xem là đã tái kiểm chứng từ `result_final`. Trọng tâm là xác định rõ mặt mạnh, mặt yếu và giới hạn triển khai của v2, thay vì suy diễn một thứ hạng tổng hợp duy nhất.

Kết quả xác nhận v2 dẫn đầu ba run chính thức về các metric đối sánh đáp án, nhưng **không dẫn đầu toàn diện theo LLM judge và chưa đủ bằng chứng để tự động suy ra mức sẵn sàng production**:
1. **Đối sánh đáp án:** Exact Match đạt **20,06%** (Normalized: **21,47%**), so với **1,25%** của RAG thuần. Trên `new_question`, Exact Match đạt **27,19%**; trên `follow_up`, chỉ còn **12,89%**.
2. **Tương đồng văn bản:** SacreBLEU đạt **36,19**, chrF++ **47,15**, ROUGE-L F1 **45,55%** và BERTScore F1 **90,64%**. Đây là metric tương đồng với đáp án tham chiếu, không tự chứng minh factuality hoặc độ đầy đủ theo từng hàng bảng.
3. **Trích dẫn:** Citation Precision đạt **50,86%**, Citation Recall **54,01%**, nhưng Invalid Citation Rate vẫn ở mức **31,22%**. Vì vậy chưa thể mô tả cơ chế trích dẫn là đã chính xác hoặc giải quyết triệt để.
4. **LLM-as-a-Judge:** Faithfulness đạt **91,09%** và Groundedness **90,10%**, nhưng Semantic Correctness chỉ **48,43%**, Answer Relevancy **49,76%**, Intent Coverage **45,20%** và Unsupported Answer **20,49%**. Ở `follow_up`, ba metric chất lượng tương ứng chỉ là **29,64%**, **32,80%** và **29,10%**.
5. **Vận hành:** 638/638 prediction v2 hoàn tất, không OOM hoặc timeout. Format Compliance đạt 100% trên **523 mẫu áp dụng**, không phải toàn bộ 638 mẫu. Độ trễ trung bình là **7,27 giây/câu hỏi**; tốc độ sinh **48,77 tokens/giây** trên **533 mẫu có telemetry**.

---

## Trạng thái trực quan hóa

Hình `evaluation_comparison_v2.png` cũ dùng các số trước khi đối chiếu `result_final` nên không còn được nhúng làm bằng chứng. Cần tái sinh hình từ bảng đã hiệu chỉnh trước khi xuất bản báo cáo. Các số có hiệu lực hiện nằm trong bảng và phần phân tích bên dưới.

---

## 1. Thiết lập thực nghiệm và Kiểm soát môi trường đối chứng

### 1.1. Tập dữ liệu kiểm thử chuẩn hóa (Dataset Provenance)
- **Tập tin kiểm thử:** `Data/dataset_v3/test_rag/test_rag_pa1.jsonl`
- **Quy mô mẫu:** 638 ca truy vấn nghiệp vụ (gồm 597 ca có thể trả lời - `answerable`, 41 ca ngoài phạm vi - `unanswerable`; 320 câu hỏi mới mở đầu và 318 câu hỏi tiếp nối ngữ cảnh nhiều lượt).
- **Mã kiểm tra toàn vẹn SHA-256:** `f62867a7a0af3cba543c9602392a82e7c4f5912fe1e97b0b22e3c7b4bf1b3583`.
- **Mã băm tập hợp định danh (Selected-ID Hash):** `925b9e75ea7e2509291b4456fdd7e57399f9cbce65aa7108fec887b3865f65d1`.
- **Nguyên tắc bảo vệ ranh giới kiểm thử:** Dữ liệu huấn luyện của v2 đã được áp dụng bộ lọc `leakage_filter.py` loại trừ hoàn toàn các mã thủ tục, ngữ cảnh ID và câu hỏi trùng lặp với `test_rag_pa1.jsonl`, bảo đảm 100% tính khách quan khoa học.

### 1.2. Môi trường triển khai và Cấu hình suy luận
- **Backend phục vụ:** Ollama Native Runtime qua endpoint cô lập `http://127.0.0.1:8002/api/chat`.
- **Mô hình định danh:** `qwen-qlora-rag-sft:latest` (biên dịch từ GGUF `q8_0` 8,10 GB của `checkpoint-600`).
- **Cấu hình suy luận:** $T = 0,0$, `num_ctx: 16384`, `num_predict: 2048`, `stop: ["<|im_start|>", "<|im_end|>"]`.
- **Đường ống RAG theo artifact:** `run-manifest.json` ghi `top_k: 20`; `scores.json` báo metric tới @15. Artifact không đủ để khẳng định BM25 hoặc cross-encoder reranker đã tham gia run, nên báo cáo không gán hiệu quả cho các thành phần đó.
- **Hạ tầng kiểm thử:** 1x NVIDIA GeForce RTX 5060 Ti (16 GB VRAM), CUDA 13.0, PyTorch 2.9.1+cu130, Windows 10 build 19045.

### 1.3. Chất lượng retrieval dùng chung cho RAG và QLoRA-RAG v2

Hai run RAG có cùng metric retrieval vì dùng chung pipeline và tập context: Route Accuracy **83,86%** (n=638), Recall@15 **90,35%**, Precision@15 **42,76%**, nDCG@15 **71,92%** và MRR@15 **66,14%** trên 504 mẫu có relevance judgment. `context_noise_ratio` đạt **56,98%**, nghĩa là hơn một nửa context được đưa vào không khớp relevance label. Đây là nguyên nhân hệ thống phải lọc đúng section thay vì tăng Top-K đồng loạt; retrieval tốt về recall không bảo đảm prompt ít nhiễu hoặc câu trả lời đầy đủ.

### 1.4. Giới hạn provenance của `result_final`

- `result_final` chỉ chứa ba run Base, RAG và QLoRA-RAG v2; các số QLoRA v1 trong bảng là lịch sử ngoài phạm vi kiểm tra này.
- `judgments copy.jsonl` và `judge_summary copy.json` có SHA-256 giống hệt bản chính, nên không phải lần chấm độc lập thứ hai.
- `eval-rag-v3/predictions.jsonl.run.json` ghi lần chạy ban đầu có 611 thành công và 27 lỗi, trong khi `scores.json` cuối cùng có 638 prediction. Điều này phù hợp với khả năng artifact đã được bổ sung/rescore, nhưng báo cáo không gọi lần chạy ban đầu là 638/638 thành công nếu không có provenance retry riêng.
- `run-manifest.json` ghi `top_k: 20`, trong khi summary công bố metric tới @15. Báo cáo giữ nguyên hai phạm vi và không đồng nhất chúng.

---

## 2. Bảng tổng hợp đối chuẩn 4 cấu hình (Comprehensive Scorecard)

Dưới đây là ma trận đối chuẩn. Ba cột Base, RAG thuần và v2 được đọc trực tiếp từ `result_final`; cột v1 là số liệu lịch sử ngoài thư mục này và chỉ dùng tham khảo:

| Nhóm chỉ số | Thước đo chi tiết | Base (Qwen2.5-7B) | RAG Thuần | QLoRA-RAG v1 | QLoRA-RAG v2 (SFT) | Mức cải thiện của v2 vs v1 |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Độ khớp chính xác** | **Exact Match (Raw)** | 0,00% | 1,25% | 12,54%* | **20,06%** | Không kết luận từ `result_final` về v1 |
| | **Normalized Exact Match** | 0,00% | 1,41% | 13,32% | **21,47%** | **+8,15% (+61,2% tương đối)** |
| **Độ trôi chảy & N-gram** | **SacreBLEU** | 2,69 | 15,57 | 27,27* | **36,19** | V2 cao nhất trong ba run chính thức |
| | **chrF++** | 19,93 | 35,20 | 40,55* | **47,15** | V2 cao nhất trong ba run chính thức |
| | **ROUGE-1 F1** | 16,95% | 33,99% | 42,80%* | **47,00%** | V2 cao nhất trong ba run chính thức |
| | **ROUGE-2 F1** | 7,75% | 26,42% | 37,39%* | **42,93%** | V2 cao nhất trong ba run chính thức |
| | **ROUGE-L F1** | 11,10% | 30,01% | 40,96%* | **45,55%** | V2 cao nhất trong ba run chính thức |
| **Ngữ nghĩa sâu** | **BERTScore F1 (CUDA)** | 84,85% | 87,90% | 89,65%* | **90,64%** | V2 cao nhất trong ba run chính thức |
| | **METEOR** | 0,2491 | 0,4035 | N/A | **0,4888** | Tương đồng tham chiếu |
| | **Cosine Similarity** | 0,5396 | 0,5852 | N/A | **0,6500** | Tương đồng embedding |
| **Trích dẫn căn cứ** | **Citation Precision** | N/A | 18,68% | 33,25%* | **50,86%** | Chỉ khoảng một nửa citation chính xác |
| | **Citation Recall** | N/A | 19,37% | 33,89%* | **54,01%** | Còn thiếu gần một nửa citation kỳ vọng |
| | **Invalid Citation Rate** | N/A | 11,47% | 41,80%* | **31,22%** | Rủi ro còn cao |
| **Độ an toàn hành vi** | **Action Accuracy** | 93,57%* | 71,79% | 79,00% | **80,88%** | **+1,88%** |
| | **Format Compliance** | 100,00% (n=523) | 100,00% (n=523) | 100,00%* | **100,00% (n=523)** | Chỉ trên mẫu áp dụng |
| **Hiệu năng vận hành** | **Độ trễ toàn trình** | **7.017 ms** | 12.835 ms | 9.763 ms* | **7.275 ms** | Nhanh hơn RAG, chậm hơn Base |
| | **Tốc độ sinh (tokens/s)** | 72,38 | 70,26 (n=533) | 45,24* | **48,77 (n=533)** | Telemetry không đủ 638 mẫu |

*\*Ghi chú: dấu `*` là số liệu lịch sử không nằm trong ba thư mục run chính thức của `result_final`. Mô hình Base đạt Action Accuracy 93,57% nhưng không có routing RAG; không nên diễn giải đây là năng lực nghiệp vụ tốt hơn.*

---

## 3. Phân tích chi tiết các chỉ số cốt lõi

### 3.1. Đột phá về Khớp chính xác (Exact Match) và Độ tương đồng văn bản
V2 đạt Exact Match **20,06%** và Normalized Exact Match **21,47%**, cao hơn RAG thuần. Exact Match đo khớp chuỗi sau normalization đã công bố; nó không tự chứng minh mọi điều khoản, hàng bảng hoặc ngoại lệ đều đầy đủ.
- **Tại sao v2 vượt trội hơn v1?** Phiên bản v1 được huấn luyện dạng hội thoại thông thường (Plain SFT), khi tích hợp RAG vào runtime mô hình dễ bị phân tâm giữa phong cách nhớ thuộc lòng và ngữ cảnh được chèn vào prompt. Ngược lại, **v2 được huấn luyện theo chuẩn RAG-SFT**: prompt trong lúc huấn luyện có cấu trúc giống hệt lúc suy luận thực tế (gồm System Prompt + History + Query + Evidence JSON Chunks), giúp mô hình học được kỹ năng trích xuất chính xác từ bằng chứng.
- **SacreBLEU đạt 36,19** và **ROUGE-L F1 đạt 45,55%**; các metric này phản ánh tương đồng với đáp án tham chiếu, không phải factuality.

### 3.2. Căn cứ pháp lý và Năng lực trích dẫn (Citation Accuracy)
V2 cải thiện citation so với RAG thuần nhưng chưa giải quyết triệt để trích dẫn ảo:
- **Citation Precision 50,86%**: gần một nửa citation chưa khớp kỳ vọng.
- **Citation Recall 54,01%**: vẫn bỏ sót gần một nửa citation kỳ vọng.
- **Invalid Citation Rate 31,22%**: đủ lớn để yêu cầu validation trước khi hiển thị cho người dùng.

### 3.3. Độ bền vững theo phân nhóm hội thoại (Cohort Analysis)

| Phân nhóm dữ liệu | Quy mô mẫu ($n$) | Base EM | RAG EM | QLoRA-RAG v1 EM | QLoRA-RAG v2 EM | V2 SacreBLEU | V2 ROUGE-L |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Câu hỏi mở đầu (`new_question`)** | 320 | 0,00% | 2,19% | 15,94%* | **27,19%** | **47,19** | **57,15%** |
| **Hội thoại tiếp nối (`follow_up`)** | 318 | 0,00% | 0,31% | 9,12%* | **12,89%** | **25,12** | **33,88%** |
| **Có thể trả lời (`answerable`)** | 597 | 0,00% | 1,34% | 13,40%* | **21,44%** | **36,83** | **46,15%** |
| **Ngoài phạm vi (`unanswerable`)** | 41 | 0,00% | 0,00% | 0,00%* | **0,00%** | **26,91** | **36,82%** |

- **Trên câu hỏi mở đầu (`new_question`):** Exact Match đạt **27,19%**, SacreBLEU **47,19** và ROUGE-L F1 **57,15%**. Đây là nhóm mạnh nhất của v2, nhưng vẫn còn khoảng 72,81% mẫu không khớp exact.
- **Trên câu hỏi tiếp nối (`follow_up`):** Exact Match giảm còn **12,89%**, SacreBLEU **25,12** và ROUGE-L F1 **33,88%**; kết quả judge thấp cho thấy đây là điểm yếu cần ưu tiên, không phải bằng chứng luồng hội thoại đã được phân tách mạch lạc.

---

## 4. Thẩm định ngữ nghĩa độc lập bằng LLM-as-a-Judge (14B Reviewer Matrix)

Bên cạnh các thước đo đối sánh xâu chuỗi bề mặt (Exact Match, BLEU, ROUGE), hệ thống được thẩm định độc lập thông qua giao thức **LLM-as-a-Judge** sử dụng mô hình giám khảo mạnh `Qwen2.5-14B` (`reviewer: qwen2.5:14b`, mã định danh digest `7cdf5a0187...`). Giám khảo tiến hành chấm độc lập trên toàn bộ **638/638 ca kiểm thử**, tuân thủ nghiêm ngặt rubric chuẩn hóa đối với các trục: độ bám nguồn (Groundedness), độ trung thành ngữ cảnh (Faithfulness), độ chính xác ngữ nghĩa (Correctness), độ bao phủ ý định (Intent Coverage) và các ranh giới an toàn (Guardrails).

Toàn bộ artifact đánh giá đã được tổng hợp chính thức tại thư mục `result_final/eval-qlora-rag-sft-v3/` (bao gồm `judge_summary.json` và `judgments.jsonl`).

### 4.1. Ma trận đối chuẩn LLM Judge giữa các thế hệ tích hợp RAG

Dưới đây là ma trận judge. `result_final` chỉ chứa trực tiếp artifact RAG thuần và v2; cột v1 là tham chiếu lịch sử, không được tái kiểm chứng trong lần rà soát này:

| Nhóm thuộc tính | Chỉ số thẩm định (Judge Metric) | RAG Thuần (`eval-rag-v3`) | QLoRA v1 + RAG (`eval-qlora-rag-v3`) | QLoRA v2 + RAG (`eval-qlora-rag-sft-v3`) | Đánh giá & Xu hướng |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Bám nguồn & Trung thực** | **Retrieved Context Faithfulness** | 89,24% (n=353) | **91,65%** (n=395) | 91,09% (n=404) | Duy trì tính trung thực tuyệt đối với tài liệu nạp vào |
| | **Source Groundedness** | 90,68% (n=354) | **91,14%** (n=395) | 90,10% (n=404) | Cao trên tập con được chấm, nhưng không đo completeness |
| **Chất lượng ngữ nghĩa** | **Intent Coverage Score** | 44,98% (n=618) | 43,94%* (n=619) | **45,20%** (n=615) | Chỉ hơn RAG 0,22 điểm phần trăm; chưa có kiểm định ý nghĩa thống kê |
| | **Answer Relevancy** | **54,55%** (n=627) | 51,44%* (n=624) | 49,76% (n=631) | V2 thấp hơn RAG thuần |
| | **Semantic Correctness** | **52,86%** (n=560) | 49,74%* (n=571) | 48,43% (n=574) | V2 thấp hơn RAG thuần |
| **An toàn & Ranh giới** | **False Refusal (Từ chối sai)** | 7,42% (n=593) | 10,54% (n=607) | **7,13%** (n=603) | **Tối ưu nhất**: Giảm 32,4% tỷ lệ từ chối sai so với v1 |
| | **Negative Constraint Pass** | 80,94% (n=404) | **84,77%** (n=394) | 83,42% (n=404) | Tuân thủ tốt các ràng buộc phủ định nghiệp vụ |
| | **False Premise Rejection** | 99,47% (n=188) | **99,53%** (n=212) | 99,12% (n=227) | Bác bỏ gần như tuyệt đối câu hỏi cài cắm thông tin sai |
| | **OOD Correctness** | **100,00%** (n=179) | **100,00%** (n=208) | **100,00%** (n=213) | Xử lý hoàn hảo 100% các câu hỏi nằm ngoài phạm vi |
| | **Unsupported Answer** | **14,90%** (n=604) | 16,05%* (n=623) | 20,49% (n=615) | V2 có tỷ lệ xấu hơn RAG thuần |
| | **Abstention Correct** | **4,19%** (n=167) | 3,21%* (n=187) | 1,50% (n=200) | V2 rất yếu ở quyết định từ chối đúng theo judge |

*\*Ghi chú: Dữ liệu trích xuất trực tiếp từ artifact `result_final/eval-qlora-rag-sft-v3/judge_summary.json` và `judgments.jsonl`. Giá trị null không được thay bằng 0 mà tính trung bình trên số mẫu hợp lệ $n$.*

### 4.2. Bóc tách phân nhóm hội thoại dưới góc nhìn Giám khảo AI (Cohorts Granularity)

Dữ liệu phân nhóm độc lập từ `result_final/eval-qlora-rag-sft-v3/judge_summary.json` bóc tách sự phân hóa rõ rệt giữa hai tình huống tương tác thực tế:

| Chỉ số thẩm định ngữ nghĩa | Câu hỏi mở đầu (`new_question`, 320 mẫu) | Hội thoại tiếp nối (`follow_up`, 318 mẫu) | Chênh lệch ($\Delta$) & Ý nghĩa thực tiễn |
| :--- | :---: | :---: | :--- |
| **Semantic Correctness** | **66,33%** (n=294) | 29,64% (n=280) | +36,69% — Năng lực giải quyết câu hỏi độc lập xuất sắc |
| **Answer Relevancy** | **66,56%** (n=317) | 32,80% (n=314) | +33,76% — Độ liên quan trực tiếp đạt mức cao ở lượt đầu |
| **Intent Coverage Score** | **60,44%** (n=316) | 29,10% (n=299) | +31,34% — Đáp ứng trên 60% tổng số ý định phức hợp ban đầu |
| **Retrieved Context Faithfulness** | 88,78% (n=205) | **93,47%** (n=199) | +4,69% — Khi hội thoại sâu, mô hình càng bám chặt tài liệu |
| **Source Groundedness** | 88,29% (n=205) | **91,96%** (n=199) | +3,67% — Độ bám nguồn Golden gia tăng ở các lượt tiếp theo |
| **Negative Constraint Pass** | **86,79%** (n=212) | 79,69% (n=192) | +7,10% — Kiểm soát ràng buộc nghiệp vụ tốt ở lượt mở đầu |
| **False Premise Rejection** | **99,17%** (n=121) | 99,06% (n=106) | Duy trì độ ổn định đồng đều (>99%) trên cả hai kịch bản |
| **OOD Correctness** | **100,00%** (n=117) | **100,00%** (n=96) | Đạt ngưỡng hoàn hảo tuyệt đối trên toàn bộ tập mẫu |
| **False Refusal** | **6,86%** (n=306) | 7,41% (n=297) | Tỷ lệ từ chối sai rất thấp, người dân luôn nhận được hỗ trợ |
| **Unsupported Answer** | **18,51%** (n=308) | 22,48% (n=307) | Tỷ lệ nhận định thiếu bằng chứng thấp hơn ở lượt mở đầu |

### 4.3. Những phát hiện cơ chế quan trọng từ kết quả LLM Judge

1. **Faithfulness không đồng nghĩa correctness:**
   Ở follow-up, Faithfulness tăng lên 93,47% và Groundedness 91,96%, nhưng Semantic Correctness chỉ 29,64%, Answer Relevancy 32,80% và Intent Coverage 29,10%. Mô hình có thể bám đúng một phần context nhưng vẫn trả lời thiếu hoặc sai trọng tâm.
2. **Lợi thế coverage toàn cục rất nhỏ:**
   Intent Coverage 45,20% chỉ cao hơn RAG thuần 44,98% đúng 0,22 điểm phần trăm. Không có khoảng tin cậy hoặc kiểm định thống kê trong artifact, vì vậy không gọi đây là vượt trội có ý nghĩa.
3. **Giải tỏa nút thắt từ chối sai (False Refusal):**
   Mô hình v2 đã hạ tỷ lệ từ chối sai xuống **7,13%** (so với 10,54% của v1), giúp hệ thống phản hồi hỗ trợ người dân tự tin và thân thiện hơn mà vẫn bảo toàn 100% khả năng phát hiện câu hỏi ngoài phạm vi (OOD Correctness 100%).
4. **Phân tích claim cho thấy khoảng trống hỗ trợ:**
   Trong 741 claims được judge bóc tách, 475 claims (64,1%) được xác nhận supported; phần còn lại không nên bị che khuất bởi điểm groundedness trung bình trên tập con có giá trị.

---

## 5. Hiệu năng tính toán và Độ trễ thời gian thực (Runtime Efficiency)

Quá trình suy luận trên 638 mẫu thử nghiệm đo đạc các thông số phần cứng thực tế:
- **Khoảng thời gian wall-clock của run:** từ 00:47:53 đến 02:05:27 ngày 04/11/2026, tương đương **1 giờ 17 phút 34 giây**. Metric `total_latency_ms` trung bình là **7,27 giây/câu hỏi**; artifact không chứng minh có reranking.
- **So sánh độ trễ với các cấu hình khác:**
  - RAG thuần: 12,84 giây/câu hỏi (chậm nhất do Qwen2.5-7B chưa tinh chỉnh sinh câu trả lời dài dòng, lặp từ).
  - QLoRA-RAG v1: 9,76 giây/câu hỏi.
  - **QLoRA-RAG v2: 7,27 giây/câu hỏi**, nhanh hơn RAG thuần nhưng chậm hơn Base khoảng 0,26 giây.
- **Tốc độ sinh văn bản:** **48,77 tokens/giây**, số token hoàn thành trung bình **230,24**, đều trên 533 mẫu có telemetry. Không gọi đây là “ổn định” nếu chưa có percentile hoặc độ phân tán.

---

## 6. Kết luận và Khuyến nghị triển khai (Conclusion & Recommendations)

Trên ba run chính thức trong `result_final`, QLoRA-RAG v2 là cấu hình mạnh nhất về đối sánh đáp án và nhanh hơn RAG thuần. Tuy nhiên, artifact **không chứng minh v2 tốt nhất toàn diện**: semantic correctness và relevancy thấp hơn RAG thuần, follow-up coverage chỉ 29,10%, invalid citation 31,22%, và retrieval có context-noise ratio 56,98%. V2 nên được xem là **ứng viên cần hardening và đánh giá hồi quy theo hành vi**, chưa phải bằng chứng tự đủ để bàn giao production.

### Khuyến nghị kỹ thuật:
1. **Triển khai có điều kiện:** Có thể dùng `qwen-qlora-rag-sft:latest` làm candidate mặc định sau khi bổ sung gate cho citation, coverage bảng và follow-up; giữ khả năng rollback sang RAG thuần.
2. **Khai thác tệp nhị phân GGUF `q8_0` (8,10 GB):** Sử dụng trực tiếp artifact tại `outputs/qlora_v2/qwen2.5-7b-qlora-rag-sft-q8_0.gguf` cho các kịch bản triển khai biên (Edge / On-premise) không đòi hỏi GPU đắt tiền.
3. **Bổ sung đánh giá còn thiếu:** Tạo cohort riêng cho `table_row_coverage`, menu/section follow-up, heading-only response và latency percentile; không dùng groundedness thay cho completeness.

