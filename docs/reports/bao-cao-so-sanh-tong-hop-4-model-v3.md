# Báo cáo so sánh tổng hợp bốn mô hình trên tập test v3

> Phạm vi: `Base`, `RAG`, `QLoRA`, `QLoRA + RAG`  
> Tập test chung: 638 mẫu · rà soát artifact ngày 02/11/2026

## 1. Mục tiêu

Báo cáo tổng hợp kết quả của bốn cấu hình ViGovBot trên cùng tập test v3, nhằm trả lời ba câu hỏi:

1. Cấu hình nào gần đáp án tham chiếu nhất?
2. Cấu hình nào bao phủ key fact và xử lý tình huống cần từ chối tốt nhất?
3. Chi phí độ trễ, độ dài prompt và độ ổn định của từng cấu hình là bao nhiêu?

Không tạo “điểm tổng” vì retrieval, similarity, hành vi và hiệu năng đo các thuộc tính khác nhau. ROUGE hoặc BERTScore cao không tự chứng minh câu trả lời đúng pháp lý hay grounded vào tài liệu.

## 2. Thiết lập chung và khả năng so sánh

| Hạng mục | Giá trị |
|---|---|
| Tập test | `Data/dataset_v3/test_rag/test_rag_pa1.jsonl` |
| Split / quy mô | `test` / 638 mẫu |
| SHA-256 | `f62867a7a0af3cba543c9602392a82e7c4f5912fe1e97b0b22e3c7b4bf1b3583` |
| Danh sách mẫu | Cùng selected-ID hash `925b9e75ea7e2509291b4456fdd7e57399f9cbce65aa7108fec887b3865f65d1` |
| Endpoint | `http://127.0.0.1:8000/api/chat` |
| Giải mã | Temperature 0, seed 42 |
| Ngữ cảnh / đầu ra tối đa | `num_ctx=8192`, `num_predict=512` |

Base và RAG sử dụng mô hình `qwen2.5:7b`; QLoRA và QLoRA+RAG sử dụng Qwen2.5-7B-Instruct cùng adapter `checkpoint-300`, lượng tử hóa 4-bit NF4. Các run dùng cùng tập mẫu nhưng không hoàn toàn đồng nhất runtime: Base/RAG dùng nhánh Ollama trong khi QLoRA dùng local Transformers. Vì vậy metric chất lượng có thể so sánh trực tiếp hơn metric tốc độ token/s.

## 3. Cấu hình máy đánh giá

Hồ sơ preflight cùng đợt output ghi:

| Thành phần | Cấu hình |
|---|---|
| Hệ điều hành | Windows 10 build 19045 |
| Python | 3.11.9 |
| GPU | NVIDIA GeForce RTX 5060 Ti |
| VRAM | 17.074.421.760 byte, khoảng 15,90 GiB |
| CUDA / PyTorch | CUDA 13.0 / PyTorch 2.9.1+cu130 |
| Compute capability / BF16 | 12.0 / có hỗ trợ |

Run telemetry xác nhận dùng `cuda` cho một số phép đo, nhưng manifest không lưu machine ID, CPU hoặc RAM. Vì vậy CPU, RAM, VRAM đỉnh và GPU utilization theo từng run là `NOT VERIFIED`; cấu hình trên là hồ sơ máy cùng đợt output, không phải phép đo phần cứng ràng buộc với từng request.

## 4. Độ hoàn tất và ổn định

| Mô hình | Dòng/ID trong file | Prediction success | Placeholder error | Tỷ lệ success | OOM | Timeout |
|---|---:|---:|---:|---:|---:|---:|
| Base | 638/638 | 638 | 0 | 100,00% | 0 | 0 |
| RAG | 638/638 | 611 | 27 | 95,77% | 0 | 0 |
| QLoRA | 638/638 | 638 | 0 | 100,00% | 0 | 0 |
| QLoRA + RAG | 638/638 | 635 | 3 | 99,53% | 0 | 0 |

Cả bốn file đều có đủ 638 dòng và 638 ID duy nhất. Khác biệt nằm ở nội dung từng dòng: RAG có 27 placeholder lỗi và QLoRA+RAG có 3 placeholder lỗi không chứa câu trả lời. Vì thế phải báo đồng thời độ phủ ID và số prediction thành công, không được viết tắt thành “chỉ có 611/635 case”.

## 5. So sánh chất lượng sinh

| Chỉ số | Base | RAG | QLoRA | QLoRA + RAG | Cao nhất |
|---|---:|---:|---:|---:|---|
| BERTScore F1 | 0,8479 | 0,8424 | **0,9119** | 0,8914 | QLoRA |
| ROUGE-1 F1 | 0,1700 | 0,3438 | **0,4719** | 0,4278 | QLoRA |
| ROUGE-2 F1 | 0,0779 | 0,2673 | **0,3774** | 0,3736 | QLoRA |
| ROUGE-L F1 | 0,1117 | 0,3050 | **0,4482** | 0,4093 | QLoRA |
| chrF | 20,9224 | 34,8825 | **45,3621** | 41,0177 | QLoRA |
| METEOR | 0,2487 | `UNAVAILABLE` | **0,4755** | 0,4114 | QLoRA* |
| Embedding cosine | 0,5392 | `UNAVAILABLE` | **0,7166** | 0,6476 | QLoRA* |
| Key-fact coverage | 0,0153 | 0,1759 | 0,1302 | **0,3108** | QLoRA + RAG |
| Format compliance | 1,0000 | 1,0000 | 1,0000 | 1,0000 | Đồng hạng |

`*` RAG thiếu aggregate METEOR/cosine nên không xếp hạng đầy đủ bốn mô hình ở hai chỉ số này.

QLoRA dẫn đầu toàn bộ nhóm similarity có dữ liệu đầy đủ. Tuy nhiên QLoRA+RAG đạt key-fact coverage cao gấp khoảng 2,39 lần QLoRA và 1,77 lần RAG. Kết quả cho thấy fine-tuning tối ưu mạnh khả năng khớp đáp án tham chiếu, còn việc bổ sung retrieval giúp đưa thêm các sự kiện đích vào câu trả lời.

## 6. Retrieval, routing và hành vi

| Chỉ số | Base | RAG | QLoRA | QLoRA + RAG |
|---|---:|---:|---:|---:|
| Recall@5 | N/A | **0,8052** | N/A | 0,7811 |
| nDCG@5 | N/A | **0,7034** | N/A | 0,6812 |
| MRR@5 | N/A | **0,6695** | N/A | 0,6474 |
| Route accuracy | N/A | 0,8363 | N/A | **0,8425** |
| Action accuracy | **0,9357** | 0,7103 | **0,9357** | 0,7937 |
| Abstention correctness | 0,0000 | 0,0452 | 0,0000 | **0,4634** |

RAG thuần có Recall@5 và nDCG@5 cao hơn QLoRA+RAG một lượng nhỏ. QLoRA+RAG lại có route accuracy và khả năng abstain tốt hơn đáng kể. Điều này cho thấy chất lượng câu trả lời kết hợp không chỉ phụ thuộc thứ hạng retrieval; routing, prompt, adapter và hành vi sinh cũng tác động đến kết quả cuối.

Giá trị route accuracy bằng 0 trong artifact Base/QLoRA không được đưa vào bảng vì hai kiến trúc bỏ qua routing. Đó là `N/A`, không phải thất bại định tuyến.

## 7. Kết quả LLM-as-a-Judge và citation

Artifact mới chỉ cung cấp judgment cho RAG. Không có judgment tương đương cho Base, QLoRA hoặc QLoRA+RAG, vì vậy bảng dưới đây mô tả RAG chứ không xếp hạng bốn mô hình.

| Chỉ số RAG | Điểm | n | Diễn giải |
|---|---:|---:|---|
| Source groundedness | 0,9086 | 350 | Bám nguồn Golden |
| Retrieved-context faithfulness | 0,8940 | 349 | Trung thành context thực dùng |
| Semantic correctness | 0,5089 | 564 | Đúng nghĩa so với đáp án |
| Answer relevancy | 0,5374 | 629 | Liên quan câu hỏi |
| Intent coverage | 0,4357 | 622 | Bao phủ đủ yêu cầu |
| Unsupported-claim rate | 0,2347 | 363 | Claim chưa được evidence hỗ trợ |
| Hallucination rate | 0,1092 | 363 | Claim bị evidence mâu thuẫn |
| Citation precision | 0,1939 | 570 | Trích dẫn đúng trên trích dẫn sinh ra |
| Citation recall | 0,1991 | 570 | Bao phủ nguồn cần trích |

Judge là `qwen2.5:14b`, có model digest, rubric hash và input hash theo từng judgment. Groundedness/faithfulness cao nhưng correctness, intent coverage và citation thấp hơn nhiều. Điều này củng cố kết luận rằng “bám context” không đồng nghĩa “trả lời đúng, đủ và trích dẫn chính xác”.

## 8. So sánh hiệu năng

| Chỉ số trung bình | Base | RAG | QLoRA | QLoRA + RAG |
|---|---:|---:|---:|---:|
| Tổng độ trễ | 6.642,85 ms | 11.534,37 ms | **5.720,39 ms** | 8.829,66 ms |
| TTFT | 2.214,66 ms | 2.957,47 ms | **318,97 ms** | 2.894,18 ms |
| Retrieval latency | N/A | **45,70 ms** | N/A | 52,04 ms |
| Tốc độ sinh | **72,02 token/s** | 69,90 token/s | 13,32 token/s | 45,13 token/s |
| Prompt token | 172,52 | 3.117,35 | **171,53** | 3.243,82 |
| Completion token | 311,64 | 228,93 | **77,88** | 195,96 |

QLoRA có tổng độ trễ và TTFT thấp nhất, đồng thời tạo câu trả lời ngắn nhất. Base có token/s cao nhất nhưng sinh đầu ra dài, nên tổng thời gian vẫn cao hơn QLoRA. Hai cấu hình RAG phải xử lý prompt hơn 3.100 token và có độ trễ lớn hơn. Không nên dùng token/s để xếp hạng tuyệt đối vì runtime và chiều dài đầu ra khác nhau; báo cáo cũng chưa có percentile, concurrency hay warm-up contract.

## 9. Phân tích theo mục tiêu sử dụng

| Mục tiêu | Lựa chọn phù hợp nhất theo artifact | Lý do | Rủi ro chính |
|---|---|---|---|
| Baseline đối chứng | Base | Không fine-tuning, không retrieval | Key fact và abstention rất thấp |
| Khớp đáp án, phản hồi ngắn | QLoRA | Dẫn đầu similarity; TTFT và tổng độ trễ thấp nhất | Không grounded; abstention bằng 0 |
| Kiểm tra retrieval và groundedness đã có judge | RAG | Recall@5, nDCG@5, MRR@5 cao nhất; có 638 judgment | Prediction contract vẫn ghi 27 lỗi; citation thấp |
| Trợ lý thủ tục cần key fact và từ chối hợp lý | QLoRA + RAG | Key fact và abstention cao nhất; 3 lỗi | Similarity thấp hơn QLoRA; retrieval thấp hơn RAG nhẹ |

Nếu mục tiêu triển khai là trả lời thủ tục hành chính có căn cứ, QLoRA+RAG vẫn là ứng viên theo key-fact và abstention, nhưng chưa có judge để xác nhận groundedness. RAG đã có judge và đạt groundedness/faithfulness cao trên tập con hợp lệ, song correctness và citation còn thấp. Cần chấm cùng một rubric cho QLoRA+RAG trước khi quyết định giữa hai cấu hình.

## 10. Kết luận tổng hợp

Không có một cấu hình thắng tuyệt đối:

- **QLoRA** tốt nhất về độ gần đáp án tham chiếu và độ trễ trung bình, phù hợp khi ưu tiên câu trả lời ngắn và ổn định.
- **QLoRA + RAG** tốt nhất về key-fact coverage và abstention, là ứng viên chính cho luồng trả lời thủ tục có truy xuất.
- **RAG** có retrieval tốt nhất nhẹ và đã có bằng chứng judge về groundedness/faithfulness, nhưng correctness/citation còn hạn chế và prediction contract vẫn ghi 27 lỗi.
- **Base** cung cấp baseline sạch nhưng thiếu tri thức miền và khả năng từ chối.

Khuyến nghị kỹ thuật là giữ QLoRA làm nhánh đối chứng không retrieval; chấm QLoRA+RAG bằng đúng judge/rubric của RAG; điều tra vì sao retrieval của cấu hình kết hợp thấp hơn RAG thuần; và tạo prediction artifact mới xác nhận trạng thái các case đã chạy bù.

## 11. Phân tích đầy đủ các hạn chế

### 11.1. Groundedness và faithfulness chưa so sánh đủ bốn cấu hình

Hai khái niệm cần được tách riêng:

- `retrieved_context_faithfulness` kiểm tra claim trong câu trả lời có được hỗ trợ bởi context thực tế đã truy xuất và đưa vào prompt hay không. Chỉ số này thực sự **không áp dụng** cho Base và QLoRA thuần vì hai cấu hình không có retrieval và `context_used` không tồn tại. Nó có thể so sánh trực tiếp RAG với QLoRA+RAG nếu cả hai được chấm bằng cùng judge/rubric.
- `source_groundedness` kiểm tra câu trả lời có được Golden evidence hỗ trợ hay không. Về nguyên tắc, chỉ số này **vẫn có thể chấm** Base và QLoRA bằng cách đối chiếu câu trả lời closed-book với nguồn chuẩn. Việc hai cấu hình chưa có điểm là do chưa chạy judge tương ứng, không phải vì mẫu số toán học bắt buộc không tồn tại.

Artifact hiện chỉ có `judgments.jsonl` cho RAG. QLoRA+RAG có retrieval nhưng không có judgment file; Base và QLoRA cũng chưa được đối chiếu với Golden evidence bằng cùng rubric. Vì thế kết luận “RAG grounded hơn các mô hình khác” chưa hợp lệ. Việc cần làm là chạy cùng `qwen2.5:14b`, model digest và rubric hash trên cả bốn prediction artifact; báo `retrieved_context_faithfulness=N/A` cho hai cấu hình closed-book nhưng vẫn báo `source_groundedness` nếu Golden evidence đủ.

### 11.2. Judge tự động chưa thay thế thẩm định pháp lý thủ công

Judge 14B có thể tách claim, kiểm tra claim được hỗ trợ, mâu thuẫn hoặc không có bằng chứng, nhưng không có thẩm quyền xác nhận giá trị pháp lý và chưa định lượng hậu quả của từng lỗi. Một claim sai về cách diễn đạt có mức rủi ro khác với hướng dẫn sai cơ quan tiếp nhận, thời hạn bắt buộc, lệ phí hoặc thành phần hồ sơ làm người dân mất quyền thực hiện thủ tục.

Do đó `hallucination_rate=0,1092` chỉ cho biết tỷ lệ claim bị evidence mâu thuẫn trên 363 mẫu claim-eligible, không phải “10,92% câu trả lời gây hậu quả pháp lý”. Báo cáo production cần một đợt human review có rubric mức độ nghiêm trọng, tối thiểu gồm: không ảnh hưởng, gây bất tiện, có thể làm hồ sơ bị trả lại, có thể làm mất thời hạn/quyền, và lỗi an toàn nghiêm trọng. Nên lấy mẫu phân tầng theo loại trường thủ tục, chấm mù bởi ít nhất hai chuyên gia, công bố mức đồng thuận và cơ chế phân xử bất đồng.

### 11.3. Benchmark chất lượng không phải benchmark tải

Run 638 mẫu hiện tại là functional/quality benchmark ở concurrency 1. Mục tiêu của nó là cô lập từng câu hỏi để đo retrieval, generation và độ trễ per-sample; nó không mô phỏng nhiều người dùng đồng thời. Mean latency và TTFT vì vậy không trả lời được tail latency hoặc năng lực phục vụ.

Các chỉ số p50/p95/p99 cần được tính trên phép đo có quy ước warm-up, thời điểm bắt đầu/kết thúc và số request hợp lệ. Concurrency, throughput và saturation cần một benchmark riêng theo các mức tải cố định, chẳng hạn 1/2/5/10 request đồng thời, kèm thời lượng, error rate và queueing. Không nên trộn kết quả load test vào điểm chất lượng vì nghẽn GPU có thể thay đổi cả độ trễ lẫn khả năng hoàn tất generation.

### 11.4. Trạng thái case chạy bù chưa được artifact hiện tại chứng minh

Nội dung bổ sung cho biết ba case QLoRA+RAG đã được chạy bù và chấm lại. Kiểm tra trực tiếp xác nhận file có 638 dòng/638 ID, nhưng ba dòng `GOLDEN_V3_005699`, `GOLDEN_V3_006086`, `GOLDEN_V3_006644` vẫn ghi lỗi HTTP 502, `generation=null`, telemetry `unavailable` và metric generation `null`. Sidecar vẫn ghi `success:635,error:3`; RAG có cấu trúc tương tự với 27 placeholder lỗi. `scores.json` hoặc judgment đủ 638 ID không tự chứng minh 638 câu trả lời thành công, vì scorer vẫn tạo một dòng kết quả với giá trị `null` cho case lỗi.

Để bảo toàn provenance, không nên sửa tay vài dòng trong run lịch sử. Cách hoàn thiện hợp lệ là tạo run revision hoặc thay thế có kiểm soát ba placeholder bằng prediction chạy bù, rồi cập nhật sidecar/manifest/checksum. Cho đến khi artifact đó xuất hiện, kết luận chính xác là: **độ phủ ID 638/638; prediction thành công 635/638 đối với QLoRA+RAG và 611/638 đối với RAG**. Tuyên bố “638 case có mặt” là `VERIFIED`; tuyên bố “638 inference đều thành công” là `NOT VERIFIED`.

### 11.5. Thiếu telemetry phần cứng theo request

Ollama API cung cấp token count và duration nhưng không cung cấp CPU, RAM hệ thống, VRAM đỉnh hoặc GPU utilization theo request. Vì thế các trường này phải là `UNAVAILABLE/NOT VERIFIED`; không được lấy VRAM tổng trong preflight hoặc một ước lượng cấu hình làm số đo runtime.

Muốn bổ sung cần một collector ngoài tiến trình: lấy mẫu `nvidia-smi` và `psutil` theo interval cố định, đồng bộ timestamp/run ID, ghi thiết bị và process ID, sau đó báo peak/mean cùng sampling interval. Đối với Docker cần ghi cả giới hạn container và số đo host để tránh nhầm tài nguyên được cấp với tài nguyên thực dùng.

### 11.6. Cohort đã có trong artifact nhưng cần trình bày vì overall mean che khuất lỗi

`scores.json` đã chứa các cohort `answerable`, `unanswerable`, `turn_type:new_question` và `turn_type:follow_up`. Đây không còn là thiếu dữ liệu mà là thiếu phần trình bày trong báo cáo cũ. Bảng dưới bổ sung các chênh lệch quan trọng:

| Cấu hình | ROUGE-1 câu mới | ROUGE-1 follow-up | Key fact câu mới | Key fact follow-up | Abstention unanswerable |
|---|---:|---:|---:|---:|---:|
| Base | 0,1627 | 0,1773 | 0,0253 | 0,0059 | 0,0000 |
| RAG | 0,4027 | 0,2798 | 0,2625 | 0,0875 | 0,1429* |
| QLoRA | 0,4537 | 0,4902 | 0,1158 | 0,1438 | 0,0000 |
| QLoRA + RAG | **0,5133** | 0,3409 | **0,4170** | **0,2095** | **0,4634** |

`*` RAG abstention trên cohort unanswerable có `n=21` do 20 mẫu không có giá trị áp dụng trong aggregate, dù cohort có 41 mẫu; không được diễn giải là 14,29% của toàn bộ 41 nếu chưa rà soát lý do loại mẫu.

Kết quả cho thấy retrieval cải thiện mạnh câu hỏi mới nhưng giảm rõ ở follow-up, phù hợp với rủi ro query rewriting/mất ngữ cảnh hội thoại. QLoRA giữ similarity tốt ở follow-up, còn QLoRA+RAG có key-fact coverage cao nhất ở cả hai nhóm nhưng vẫn giảm từ 0,4170 xuống 0,2095 khi chuyển sang follow-up. Vì vậy tối ưu conversation state và query rewrite là ưu tiên cụ thể hơn so với chỉ tăng top-k.

### 11.7. Ma trận hành động khắc phục

| Hạn chế | Hành động | Tiêu chí hoàn tất |
|---|---|---|
| Judge chưa đủ bốn cấu hình | Chạy cùng judge/rubric cho 4 run | Groundedness có denominator rõ; faithfulness N/A đúng chỗ |
| Thiếu pháp lý thủ công | Review phân tầng bởi ≥2 chuyên gia | Có severity, agreement và adjudication |
| Thiếu tail/load metrics | Benchmark warm-up + nhiều mức concurrency | Có p50/p95/p99, throughput, error rate |
| Case chạy bù chưa có provenance | Tạo run revision bất biến | Manifest, sidecar và predictions cùng ghi 638 success |
| Thiếu resource telemetry | Collector `nvidia-smi`/`psutil` có timestamp | Có interval, peak/mean và mapping theo run |
| Overall che khuất cohort | Xuất bảng cohort bắt buộc | Báo answerable/unanswerable/new/follow-up kèm n |

## 12. Nguồn artifact

- `outputs/evaluation/eval-base-v3`
- `outputs/evaluation/eval-rag-v3`
- `outputs/evaluation/eval-qlora-v3`
- `outputs/evaluation/eval-qlora-rag-v3`
- `outputs/qlora/preflight_rtx5060ti.json`
- `outputs/qlora/best_adapter`
- `outputs/evaluation/eval-rag-v3/judgments.jsonl`

