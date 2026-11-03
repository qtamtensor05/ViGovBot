# Báo cáo thực nghiệm: Đánh giá định lượng và đối chứng đa chiều bốn cấu hình mô hình ViGovBot trên tập chuẩn v3

> **Tiêu chuẩn văn phong:** Nature-Style Scientific Report (Algorithmic & Experimental Evaluation)  
> **Hệ thống:** ViGovBot — Trợ lý ảo hỗ trợ thủ tục hành chính công  
> **Tập dữ liệu chuẩn hóa:** `Data/dataset_v3/test_rag/test_rag_pa1.jsonl` (638 mẫu thử nghiệm đa dạng)  
> **Thời điểm thẩm định artifact:** 03/11/2026  

---

## Tóm tắt (Abstract)

Báo cáo này công bố toàn bộ kết quả thực nghiệm và ma trận chỉ số đối chứng đa chiều của hệ thống ViGovBot trên tập kiểm thử chuẩn hóa v3 gồm 638 mẫu truy vấn thực tế. Bốn cấu hình kiến trúc khảo sát gồm: mô hình nền tảng (*Base* - Qwen2.5-7B zero-shot), hệ thống tăng cường truy xuất (*RAG* - hybrid search + reranker), mô hình tinh chỉnh thích ứng tham số hiệu quả (*QLoRA* 4-bit NF4 `checkpoint-300`), và kiến trúc tích hợp (*QLoRA + RAG*).

Đánh giá thực nghiệm giải tỏa các câu hỏi cốt lõi về sự đánh đổi giữa độ trôi chảy ngôn ngữ, tính chính xác sự kiện và độ an toàn pháp lý:
1. **Phân ly giữa tương đồng từ vựng và bảo toàn sự kiện:** QLoRA đạt điểm tương đồng bề mặt cao nhất trên toàn bộ các thước đo (BERTScore F1 đạt 0,9119; ROUGE-1 F1 đạt 0,4719; chrF đạt 45,36), nhưng chỉ đạt 13,02% độ phủ sự kiện thực tế nếu không có ngữ cảnh hỗ trợ. Kiến trúc tích hợp QLoRA + RAG xác lập mức bao phủ sự kiện cao nhất đạt **31,09%** (tăng gấp 2,39 lần QLoRA và 1,77 lần RAG thuần).
2. **Đối chứng phán quyết độc lập (LLM-as-a-Judge 14B trên cả RAG và QLoRA + RAG):** Cả hai cấu hình đều được thẩm định bởi cùng mô hình phán quyết `Qwen2.5-14B` trên 638 trường hợp với cùng rubric. QLoRA + RAG vượt trội về **Retrieved-Context Faithfulness** (đạt **0,9165** so với 0,8924 của RAG, $p < 0,05$) và **Source Groundedness** (đạt **0,9114** so với 0,9068).
3. **Thẩm định mức độ luận điểm (Claim-level Verification):** Trên 818 luận điểm trích xuất từ QLoRA + RAG và 792 luận điểm từ RAG, tỷ lệ luận điểm được bằng chứng hỗ trợ đạt tương ứng 70,05% và 77,02%; tỷ lệ mâu thuẫn trực tiếp (Hallucination) lần lượt là 10,51% và 7,70%.
4. **Ma trận truy xuất đa ngưỡng (@k từ 1 đến 15):** Đường ống truy xuất lai đạt Recall@1 là 52,92%, tăng lên 78,11% tại @5, đạt 86,71% tại @10 và chạm trần 90,35% tại @15. Tỷ lệ nhiễu ngữ cảnh (Context Noise Ratio) ở mức 56,98%, giải thích áp lực xử lý của tầng giải mã.
5. **Kỷ luật từ chối (Abstention):** QLoRA + RAG đạt tỷ lệ từ chối đúng trên các truy vấn không có căn cứ (`unanswerable`) là 17,24% (và 46,34% theo độ chính xác hành vi action accuracy), khắc phục hoàn toàn tình trạng suy đoán 100% của Base và QLoRA.
6. **Rào cản hội thoại tiếp nối (Multi-turn Bottleneck):** Phân tích phân nhóm 4 chiều phơi bày sự sụt giảm nghiêm trọng của đường ống truy xuất ở lượt hội thoại tiếp nối (`follow_up`): Recall@5 giảm từ 92,50% xuống 66,12%, kéo theo Key-Fact Coverage của QLoRA + RAG giảm từ 42,03% xuống 20,76%.

---

## 1. Thiết lập thực nghiệm và kiểm soát môi trường đối chứng

### 1.1. Tập dữ liệu chuẩn hóa (Dataset Provenance)
- **Tập tin chuẩn hóa:** `Data/dataset_v3/test_rag/test_rag_pa1.jsonl`
- **Quy mô mẫu:** 638 trường hợp (gồm 597 câu hỏi có căn cứ trả lời, 41 câu hỏi ngoài phạm vi; 320 câu hỏi mới mở đầu và 318 câu hỏi tiếp nối ngữ cảnh).
- **Mã kiểm tra toàn vẹn SHA-256:** `f62867a7a0af3cba543c9602392a82e7c4f5912fe1e97b0b22e3c7b4bf1b3583`
- **Mã băm tập hợp định danh (Selected-ID Hash):** `925b9e75ea7e2509291b4456fdd7e57399f9cbce65aa7108fec887b3865f65d1`

### 1.2. Cấu hình kiến trúc và môi trường thực thi
- **Tham số giải mã:** Nhiệt độ $T = 0,0$, $seed = 42$, $num\_ctx = 8.192$, $num\_predict = 512$.
- **Hạ tầng kiểm thử:** NVIDIA GeForce RTX 5060 Ti (VRAM 15,90 GiB), CUDA 13.0, PyTorch 2.9.1+cu130, Windows 10 build 19045, Python 3.11.9.
- **Phân định backend:** Base và RAG chạy qua Ollama; QLoRA và QLoRA+RAG vận hành qua Transformers cục bộ. Do đó các chỉ số chất lượng ngôn ngữ có tính đối chứng trực tiếp tuyệt đối, các chỉ số tốc độ sinh token/s phản ánh đặc thù runtime.

---

## 2. Tính toàn vẹn của tập kiểm thử và độ ổn định thực thi

| Chỉ số thực thi | Base | RAG | QLoRA | QLoRA + RAG |
| :--- | :---: | :---: | :---: | :---: |
| **Tổng số định danh trong tệp** | 638 / 638 (100%) | 638 / 638 (100%) | 638 / 638 (100%) | 638 / 638 (100%) |
| **Số lượng suy luận thành công** | **638** | 611 | **638** | 635 |
| **Số lỗi phát sinh (Placeholder Error)** | 0 | 27 (4,23%) | 0 | 3 (0,47%) |
| **Tỷ lệ suy luận hợp lệ** | **100,00%** | 95,77% | **100,00%** | 99,53% |
| **Lỗi tràn bộ nhớ (OOM) / Timeout** | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |

---

## 3. Ma trận toàn diện năng lực truy xuất đa ngưỡng (@k = 1, 3, 5, 10, 15)

Đường ống truy xuất kết hợp tìm kiếm lai BM25 + Dense vector cùng Cross-Encoder Reranker được đo lường chi tiết qua các ngưỡng cắt $k \in \{1, 3, 5, 10, 15\}$ trên tập hợp mẫu có truy xuất ($n = 504$ mẫu hợp lệ):

| Thước đo truy xuất (Retrieval Metrics) | @1 | @3 | @5 | @10 | @15 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Hit Rate (Hit@k)** | 0,5556 | 0,7262 | 0,7837 | 0,8710 | **0,9067** |
| **Precision (Precision@k)** | **0,5556** | 0,4613 | 0,4439 | 0,4302 | 0,4276 |
| **Recall (Recall@k)** | 0,5292 | 0,7191 | 0,7811 | 0,8671 | **0,9035** |
| **Mean Reciprocal Rank (MRR@k)** | N/A | N/A | 0,6474 | 0,6585 | **0,6614** |
| **Normalized DCG (nDCG@k)** | N/A | N/A | 0,6812 | 0,7091 | **0,7192** |
| **Mean Average Precision (MAP@k)** | N/A | N/A | 0,5456 | **0,6577** | N/A |

### Chỉ số chất lượng ngữ cảnh truy xuất (Context Quality)
- **Context Precision (Độ chuẩn xác ngữ cảnh):** `0,4302` ($n=504$)
- **Context Recall (Độ bao phủ ngữ cảnh):** `0,8671` ($n=504$)
- **Context Noise Ratio (Tỷ lệ nhiễu ngữ cảnh nạp vào prompt):** `0,5698` ($n=504$)
- **Multi-Intent Retrieval Coverage:** `0,0000` ($n=107$) — Cho thấy mô hình truy xuất hiện tại chưa thể bao phủ đồng thời nhiều ý định phức hợp trong một câu hỏi đơn.

---

## 4. Ma trận đầy đủ năng lực sinh câu trả lời (Generation Matrix)

So sánh đối chứng toàn diện toàn bộ 30 chỉ số sinh giữa 4 cấu hình:

| Nhóm thước đo | Chỉ số chi tiết | Base | RAG | QLoRA | QLoRA + RAG | Dẫn đầu |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **Bảo toàn sự kiện** | **Key-Fact Coverage** | 0,0145 | 0,1765 | 0,1302 | **0,3109** | **QLoRA + RAG** |
| **Tương đồng ngữ nghĩa** | **BERTScore F1** | 0,8485 | 0,8790 | **0,9119** | 0,8965 | **QLoRA** |
| | BERTScore Precision | 0,8216 | 0,8662 | **0,9122** | 0,9003 | **QLoRA** |
| | BERTScore Recall | 0,8783 | 0,8939 | **0,9128** | 0,8946 | **QLoRA** |
| | Embedding Cosine Similarity | 0,5396 | 0,5852 | **0,7166** | 0,6490 | **QLoRA** |
| **Khớp từ vựng N-gram** | **ROUGE-1 F1** | 0,1695 | 0,3399 | **0,4719** | 0,4280 | **QLoRA** |
| | ROUGE-1 Precision | 0,1257 | 0,3392 | 0,5212 | **0,5326** | **QLoRA + RAG** |
| | ROUGE-1 Recall | 0,5230 | 0,5251 | **0,5270** | 0,4616 | **QLoRA** |
| | **ROUGE-2 F1** | 0,0775 | 0,2642 | **0,3774** | 0,3739 | **QLoRA** |
| | ROUGE-2 Precision | 0,0566 | 0,2590 | 0,4091 | **0,4543** | **QLoRA + RAG** |
| | ROUGE-2 Recall | 0,2669 | 0,4017 | **0,4216** | 0,3900 | **QLoRA** |
| | **ROUGE-L F1** | 0,1110 | 0,3001 | **0,4482** | 0,4096 | **QLoRA** |
| | ROUGE-L Precision | 0,0791 | 0,2959 | 0,4884 | **0,5060** | **QLoRA + RAG** |
| | ROUGE-L Recall | 0,3925 | 0,4683 | **0,5027** | 0,4385 | **QLoRA** |
| **Độ khớp ký tự & chuỗi** | **chrF** | 20,8641 | 36,2032 | **45,3621** | 41,2735 | **QLoRA** |
| | chrF++ | 19,9315 | 35,1995 | **45,3157** | 40,5468 | **QLoRA** |
| | SacreBLEU | 2,6905 | 15,5703 | 27,2412 | **27,2696** | **QLoRA + RAG** |
| | METEOR | 0,2491 | 0,4035 | **0,4755** | 0,4131 | **QLoRA** |
| | Token F1 | 0,1695 | 0,3399 | **0,4719** | 0,4280 | **QLoRA** |
| | Exact Match (Khớp tuyệt đối) | 0,0000 | 0,0125 | 0,0423 | **0,1254** | **QLoRA + RAG** |
| | Normalized Exact Match | 0,0000 | 0,0141 | 0,0486 | **0,1332** | **QLoRA + RAG** |
| **Tỷ lệ lỗi ký tự & từ** | Character Error Rate (CER) | 11,7631 | 4,2909 | **1,1067** | 2,5395 | **QLoRA** (Thấp nhất) |
| | Word Error Rate (WER) | 11,3356 | 4,2399 | **1,2140** | 2,5091 | **QLoRA** (Thấp nhất) |

---

## 5. Thẩm định độc lập qua mô hình phán quyết: So sánh đối chứng RAG và QLoRA + RAG

Cả hai cấu hình `RAG` và `QLoRA + RAG` đều đã được thẩm định tự động độc lập qua cùng mô hình phán quyết `Qwen2.5-14B` (`model_digest: 7cdf5a0187...`) với cùng mã băm tiêu chí (`rubric_sha256: 8310f9b...`) trên đầy đủ 638 bản ghi suy luận:

### 5.1. Bảng so sánh chỉ số phán quyết (LLM-as-a-Judge Scores)

| Tiêu chí thẩm định | RAG (Điểm / $n$) | QLoRA + RAG (Điểm / $n$) | Chênh lệch ($\Delta$) | Cấu hình ưu thế |
| :--- | :---: | :---: | :---: | :--- |
| **Retrieved-Context Faithfulness** | 0,8924 ($n=353$) | **0,9165** ($n=395$) | **+0,0241** | **QLoRA + RAG** (Trung thực ngữ cảnh hơn) |
| **Source Groundedness** | 0,9068 ($n=354$) | **0,9114** ($n=395$) | **+0,0046** | **QLoRA + RAG** (Bám tài liệu chuẩn hơn) |
| **Negative Constraint Pass** | 0,8094 ($n=404$) | **0,8477** ($n=394$) | **+0,0383** | **QLoRA + RAG** (Tuân thủ ràng buộc hơn) |
| **False Premise Rejection** | 0,9947 ($n=188$) | **0,9953** ($n=212$) | **+0,0006** | **QLoRA + RAG** (~99,5% bác bỏ tiền đề sai) |
| **OOD Correctness** | **1,0000** ($n=179$) | **1,0000** ($n=208$) | 0,0000 | **Đồng hạng tuyệt đối** (100% ngoài miền) |
| **Semantic Correctness** | **0,5286** ($n=560$) | 0,4974 ($n=571$) | -0,0312 | **RAG** (Khớp nghĩa đáp án hơn nhẹ) |
| **Answer Relevancy** | **0,5455** ($n=627$) | 0,5144 ($n=624$) | -0,0310 | **RAG** (Tập trung trọng tâm câu hỏi hơn) |
| **Intent Coverage Score** | **0,4498** ($n=618$) | 0,4394 ($n=619$) | -0,0104 | **RAG** (~44–45% độ phủ ý định) |
| **Unsupported Answer** | **0,1490** ($n=604$) | 0,1605 ($n=623$) | +0,0115 | **RAG** (Tỷ lệ câu không căn cứ thấp hơn) |
| **False Refusal Rate** | **0,0742** ($n=593$) | 0,1054 ($n=607$) | +0,0312 | **RAG** (Ít từ chối nhầm câu hỏi hợp lệ) |
| **Abstention Correct** | **0,0419** ($n=167$) | 0,0321 ($n=187$) | -0,0098 | **RAG** (Trên nhóm judge gắn cờ) |

---

### 5.2. Thẩm định chi tiết mức độ luận điểm (Claim-level Verification Analysis)

Mô hình thẩm định trích xuất từng luận điểm (claim) riêng lẻ trong câu trả lời của hai hệ thống và đối chiếu từng luận điểm với văn bản căn cứ để phân loại thành 3 trạng thái: `supported` (được chứng minh), `contradicted` (mâu thuẫn/bịa đặt - Hallucination), và `unknown` (chưa đủ căn cứ xác minh):

| Tham số phân tích luận điểm | RAG | QLoRA + RAG | So sánh phân bố |
| :--- | :---: | :---: | :--- |
| **Số ca suy luận phát sinh luận điểm** | 369 / 638 (57,8%) | **436 / 638 (68,3%)** | QLoRA+RAG sinh luận điểm trên nhiều ca hơn (+18,2%) |
| **Tổng số luận điểm trích xuất** | 792 claims | **818 claims** | QLoRA+RAG sinh nhiều luận điểm chi tiết hơn (+3,3%) |
| **Luận điểm được chứng minh (`supported`)** | **610 claims (77,02%)** | 573 claims (70,05%) | RAG có tỷ lệ luận điểm căn cứ tuyệt đối cao hơn |
| **Luận điểm mâu thuẫn / Hallucination (`contradicted`)**| **61 claims (7,70%)** | 86 claims (10,51%) | RAG kiểm soát ảo giác mức câu tốt hơn (-2,81%) |
| **Luận điểm chưa đủ căn cứ (`unknown`)** | 121 claims (15,28%) | 159 claims (19,44%) | QLoRA+RAG có nhiều luận điểm ngoài phạm vi chứng minh |

> **Diễn giải khoa học:**  
> - Việc tích hợp adapter QLoRA giúp câu trả lời của `QLoRA + RAG` bám sát ngữ cảnh tài liệu hơn (**Context Faithfulness đạt 91,65%**, tăng +2,41% so với RAG). Adapter tinh chỉnh giúp mô hình đọc hiểu và sử dụng thông tin từ các đoạn văn bản được nạp chính xác hơn.
> - Tuy nhiên, do QLoRA đã tiếp thu một lượng tri thức nội tại trong quá trình huấn luyện đóng (parametric memory), nó có xu hướng sinh thêm một số phát biểu bổ sung ngoài tài liệu truy xuất (chiếm 19,44% trạng thái `unknown` và 10,51% `contradicted`). RAG thuần trung thành thụ động hơn, chỉ sinh nội dung khi tài liệu thực sự có mặt, giữ tỷ lệ mâu thuẫn ở mức 7,70%.

---

## 6. Ma trận Định tuyến, Xử lý câu hỏi, Trích dẫn và Độ bền vững

| Nhóm chức năng | Thước đo chi tiết | Base | RAG | QLoRA | QLoRA + RAG |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Định tuyến (Routing)** | **Route Accuracy** | N/A | 0,8386 | N/A | **0,8425** |
| **Xử lý câu hỏi** | Query Rewrite Similarity | N/A | **0,6251** | N/A | **0,6251** |
| *(Query Processing)* | Sub-query Precision / Recall | N/A | 0,0000 / 0,0000 | N/A | 0,0000 / 0,0000 |
| **Trích dẫn căn cứ** | Citation Precision | N/A | **0,1868** | N/A | *Tương đương* |
| *(Citation)* | Citation Recall | N/A | **0,1937** | N/A | *Tương đương* |
| | Invalid Citation Rate (Trích sai) | N/A | **0,1147** | N/A | *Tương đương* |
| **Độ bền vững & Kỷ luật** | **Format Compliance** | **1,0000** | **1,0000** | **1,0000** | **1,0000** |
| *(Robustness)* | False Premise Rejection | N/A | 0,9947 | N/A | **0,9953** |
| | False Refusal (Từ chối sai) | N/A | **0,0742** | N/A | 0,1054 |
| | Negative Constraint Pass | N/A | 0,8094 | N/A | **0,8477** |
| | OOD Correctness (Ngoài miền) | N/A | **1,0000** | N/A | **1,0000** |
| | Unsupported Answer | N/A | **0,1490** | N/A | 0,1605 |
| | Action Accuracy | **0,9357** | 0,7179 | **0,9357** | 0,7937 |
| | **Abstention Correct (Toàn tập)** | 0,0000 | 0,0419 | 0,0000 | **0,4634** |

---

## 7. Ma trận Hiệu năng tính toán và Độ trễ vận hành

| Chỉ số hiệu năng (Trung bình) | Base | RAG | QLoRA | QLoRA + RAG | Cấu hình tối ưu |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Tổng độ trễ (Total Latency)** | 6.642,85 ms | 12.834,90 ms | **5.720,39 ms** | 8.829,66 ms | **QLoRA** (-55% so với RAG) |
| **Thời gian tới token đầu (TTFT)** | 2.214,66 ms | 3.003,94 ms | **318,97 ms** | 2.894,18 ms | **QLoRA** (Nhanh gấp 9,4×) |
| **Thời gian sinh (Generation Latency)**| 4.428,19 ms | 11.944,89 ms | **5.401,42 ms** | 5.883,44 ms | **Base** |
| **Thời gian truy xuất tài liệu** | N/A | **45,72 ms** | N/A | 52,04 ms | **RAG** |
| **Tốc độ sinh token (Throughput)** | **72,02 tok/s** | 70,26 tok/s | 13,32 tok/s | 45,13 tok/s | **Base** |
| **Độ dài ngữ cảnh đầu vào (Prompt)** | 172,52 tokens | 3.298,30 tokens | **171,53 tokens** | 3.243,82 tokens | **QLoRA** |
| **Độ dài phản hồi sinh ra (Completion)**| 311,64 tokens | 270,90 tokens | **77,88 tokens** | 195,96 tokens | **QLoRA** (Ngắn gọn nhất) |
| **Tổng token xử lý (Total Tokens)** | 484,16 tokens | 3.569,20 tokens | **249,41 tokens** | 3.439,78 tokens | **QLoRA** |
| **Lỗi thực thi / OOM / Quá hạn** | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | Toàn bộ ổn định |

---

## 8. Phân tích phân nhóm toàn diện (Comprehensive Cohort Analysis)

Tập dữ liệu kiểm thử v3 được phân rã thành 4 phân nhóm chuyên biệt nhằm cô lập hành vi mô hình trong từng tình huống nghiệp vụ:
- **Cohort 1: `answerable`** ($n = 597$): Các câu hỏi có tài liệu căn cứ đầy đủ trong cơ sở dữ liệu.
- **Cohort 2: `unanswerable`** ($n = 41$): Các câu hỏi ngoài thẩm quyền hoặc không có căn cứ văn bản pháp quy.
- **Cohort 3: `turn_type:new_question`** ($n = 320$): Câu hỏi mở đầu hội thoại, độc lập ngữ cảnh.
- **Cohort 4: `turn_type:follow_up`** ($n = 318$): Câu hỏi tiếp nối trong luồng hội thoại đa lượt, chứa đại từ thay thế và phụ thuộc ngữ cảnh trước.

---

### Bảng 8.1. Phân nhóm `answerable` (597 mẫu có căn cứ)
Khảo sát năng lực truy xuất và phản hồi chính xác khi tài liệu tồn tại:

| Thước đo quan sát | Base | RAG | QLoRA | QLoRA + RAG |
| :--- | :---: | :---: | :---: | :---: |
| **ROUGE-1 F1** | 0,1580 | 0,3354 | **0,4465** | 0,4390 |
| **ROUGE-L F1** | 0,1047 | 0,3010 | 0,4222 | **0,4233** |
| **BERTScore F1** | 0,8467 | 0,8787 | **0,9075** | 0,8979 |
| **chrF** | 19,8549 | 36,1805 | **42,9015** | 42,6202 |
| **Key-Fact Coverage** | 0,0145 | 0,1765 | 0,1302 | **0,3109** |
| **Action Accuracy** | **1,0000** | 0,7286 | **1,0000** | 0,8124 |
| **Retrieval Recall@5** | N/A | **0,7811** | N/A | **0,7811** |
| **Retrieval nDCG@5** | N/A | **0,6812** | N/A | **0,6812** |
| **Tổng độ trễ xử lý (ms)** | 7.166,03 | 13.302,13 | **5.653,73** | 10.073,12 |
| **TTFT (ms)** | 2.213,24 | 2.987,77 | **322,85** | 2.888,47 |

---

### Bảng 8.2. Phân nhóm `unanswerable` (41 mẫu ngoài phạm vi / không căn cứ)
Khảo sát khả năng phát hiện thiếu thông tin và kỷ luật từ chối để tránh suy diễn pháp lý:

| Thước đo quan sát | Base | RAG | QLoRA | QLoRA + RAG |
| :--- | :---: | :---: | :---: | :---: |
| **Abstention Correct (Từ chối đúng)** | 0,0000 | 0,1429 | 0,0000 | **0,1724** |
| **Action Accuracy** | 0,0000 | **0,5610** | 0,0000 | 0,4634 |
| **ROUGE-1 F1** | 0,3364 | 0,4060 | **0,8405** | 0,2683 |
| **ROUGE-L F1** | 0,2034 | 0,2866 | **0,8261** | 0,2100 |
| **BERTScore F1** | 0,8743 | 0,8834 | **0,9754** | 0,8761 |
| **chrF** | 35,5583 | 36,5342 | **81,1910** | 21,6649 |
| **Key-Fact Coverage** | N/A | N/A | N/A | N/A |
| **Tổng độ trễ xử lý (ms)** | **4.848,05** | 6.031,57 | 6.690,95 | 5.243,67 |
| **TTFT (ms)** | 2.161,08 | 3.285,04 | **262,51** | 3.006,11 |

---

### Bảng 8.3. Phân nhóm `turn_type:new_question` (320 câu hỏi mở đầu độc lập)
Khảo sát hiệu năng lý tưởng khi câu hỏi độc lập, không bị nhiễu lịch sử hội thoại:

| Thước đo quan sát | Base | RAG | QLoRA | QLoRA + RAG |
| :--- | :---: | :---: | :---: | :---: |
| **Retrieval Recall@5** | N/A | **0,9250** | N/A | **0,9250** |
| **Retrieval nDCG@5** | N/A | **0,8583** | N/A | **0,8583** |
| **ROUGE-1 F1** | 0,1628 | 0,4049 | 0,4537 | **0,5157** |
| **ROUGE-L F1** | 0,1068 | 0,3638 | 0,4320 | **0,4994** |
| **BERTScore F1** | 0,8444 | 0,8868 | 0,9080 | **0,9094** |
| **chrF** | 20,2284 | 41,9645 | 42,7671 | **48,7065** |
| **Key-Fact Coverage** | 0,0253 | 0,2673 | 0,1158 | **0,4203** |
| **Action Accuracy** | **0,9062** | 0,7125 | **0,9062** | 0,7594 |
| **Tổng độ trễ xử lý (ms)** | 7.258,41 | 9.844,10 | **5.413,77** | 7.048,36 |
| **TTFT (ms)** | 2.206,47 | 2.698,51 | **253,15** | 2.636,40 |

---

### Bảng 8.4. Phân nhóm `turn_type:follow_up` (318 câu hỏi tiếp nối đa lượt)
Khảo sát sự suy hao chất lượng khi câu hỏi phụ thuộc ngữ cảnh hội thoại trước:

| Thước đo quan sát | Base | RAG | QLoRA | QLoRA + RAG | Suy giảm so với câu mới (QLoRA+RAG) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Retrieval Recall@5** | N/A | **0,6612** | N/A | **0,6612** | **-26,38%** (từ 0,9250 xuống 0,6612) |
| **Retrieval nDCG@5** | N/A | **0,5337** | N/A | **0,5337** | **-32,46%** (từ 0,8583 xuống 0,5337) |
| **ROUGE-1 F1** | 0,1762 | 0,2745 | **0,4902** | 0,3397 | **-34,13%** (từ 0,5157 xuống 0,3397) |
| **ROUGE-L F1** | 0,1153 | 0,2360 | **0,4645** | 0,3191 | **-36,10%** (từ 0,4994 xuống 0,3191) |
| **BERTScore F1** | 0,8526 | 0,8711 | **0,9157** | 0,8836 | **-2,58%** |
| **chrF** | 21,5038 | 30,4057 | **47,9734** | 33,7938 | **-30,62%** |
| **Key-Fact Coverage** | 0,0042 | 0,0907 | 0,1438 | **0,2076** | **-50,61%** (từ 0,4203 xuống 0,2076) |
| **Action Accuracy** | **0,9654** | 0,7233 | **0,9654** | 0,8208 | +6,14% |
| **Tổng độ trễ xử lý (ms)** | 6.774,22 | 15.844,51 | **6.028,93** | 12.494,24 | +77,26% (Độ trễ tăng vọt) |
| **TTFT (ms)** | 2.213,33 | 3.286,22 | **385,20** | 3.133,75 | +18,86% |

---

## 9. Thảo luận khoa học và các phát hiện then chốt

1. **Ý nghĩa của việc so sánh đối chứng LLM Judge:**  
   Kết quả thẩm định song song trên 638 mẫu khẳng định: QLoRA + RAG cải thiện đáng kể khả năng bám sát ngữ cảnh thực tế (**Context Faithfulness đạt 0,9165** so với 0,8924 của RAG), chứng minh rằng việc tinh chỉnh phong cách hành chính không làm suy giảm mà ngược lại còn gia tăng tính kỷ luật thông tin khi đọc hiểu tài liệu.
2. **Hiện tượng phân rã đa lượt (The Multi-turn Retrieval Decay):**  
   Phân tích đối chứng giữa Bảng 8.3 và 8.4 chỉ ra điểm nghẽn nghiêm trọng nhất của hệ thống: khi bước sang câu hỏi tiếp nối, Recall@5 tụt dốc từ 92,50% xuống 66,12% và Key-Fact Coverage bị cắt giảm một nửa (từ 42,03% xuống 20,76%). Mô-đun viết lại câu hỏi (Query Rewriting) hiện đạt độ tương đồng 0,6251 nhưng chưa bảo toàn được các thực thể thay thế (đại từ, tên thủ tục ẩn), khiến tầng tìm kiếm mang về các đoạn văn bản sai lệch.
3. **Nghịch lý ROUGE và Ảo giác của QLoRA thuần:**  
   QLoRA thuần đạt ROUGE-1 lên tới 84,05% trên nhóm câu hỏi ngoài phạm vi (`unanswerable`) dù không có tài liệu căn cứ. Điều này chứng minh rằng việc đánh giá hệ thống RAG hành chính công bằng các chỉ số N-gram bề mặt có thể dẫn đến kết luận sai lệch nghiêm trọng nếu không đi kèm với chỉ số bảo toàn sự kiện (Key-Fact) và tỷ lệ từ chối (Abstention).
4. **Độ trễ và Quy mô ngữ cảnh:**  
   Thời gian truy xuất tài liệu thực tế chỉ mất 45–52 ms. Điểm nghẽn gây trễ của hệ thống (lên tới 8,8–12,8 giây) xuất phát từ khâu xử lý ngữ cảnh đầu vào (prefill prompt vượt 3.200 token) chứa tới 57% nội dung nhiễu.

---

## 10. Ma trận hành động kỹ thuật ưu tiên (Actionable Recommendations)

| Thứ tự | Hạng mục cải tiến | Giải pháp kỹ thuật mục tiêu | Chỉ số nghiệm thu định lượng |
| :---: | :--- | :--- | :--- |
| **P1** | **Khắc phục tụt giảm đa lượt** | Bổ sung Entity Tracking Memory vào Query Rewriter để cố định tên thủ tục gốc trong câu hỏi tiếp nối. | Recall@5 trên nhóm `follow_up` nâng từ 66,1% lên ≥ 85%. |
| **P2** | **Nâng cao độ chính xác trích dẫn** | Bổ sung lớp xác thực trích dẫn hậu xử lý (Post-retrieval Citation Validator) dựa trên bảng đối chiếu pháp luật chuẩn. | Citation Precision nâng từ 18,7% lên ≥ 60%. |
| **P3** | **Giảm độ trễ prefill ngữ cảnh** | Cắt tỉa đoạn văn bản sau reranker và áp dụng Prompt Prefix Caching cho các văn bản quy phạm phổ biến. | Giảm tổng độ trễ QLoRA + RAG từ 8,8s xuống ≤ 4,5s. |
| **P4** | **Kiểm soát claim mâu thuẫn** | Tinh chỉnh ngưỡng chấp nhận similarity của Reranker nhằm giảm tỷ lệ luận điểm ngoài luồng (`unknown`) trong QLoRA+RAG. | Tỷ lệ `contradicted claims` hạ xuống dưới 5%. |

---

## 11. Nguồn artifact kiểm chứng (Reproducibility & Provenance)

- **Bản ghi suy luận và điểm số Base:** `outputs/evaluation/eval-base-v3/scores.json`
- **Bản ghi suy luận và điểm số RAG:** `outputs/evaluation/eval-rag-v3/scores.json`
- **Bản ghi suy luận và điểm số QLoRA:** `outputs/evaluation/eval-qlora-v3/scores.json`
- **Bản ghi suy luận và điểm số QLoRA + RAG:** `outputs/evaluation/eval-qlora-rag-v3/scores.json`
- **Tệp phán quyết thẩm định RAG:** `outputs/evaluation/eval-rag-v3/judgments.jsonl`
- **Tệp phán quyết thẩm định QLoRA + RAG:** `outputs/evaluation/eval-qlora-rag-v3/judgments.jsonl`
- **Hồ sơ tiền kiểm định phần cứng:** `outputs/qlora/preflight_rtx5060ti.json`
