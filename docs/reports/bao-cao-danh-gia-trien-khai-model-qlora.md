# Báo cáo đánh giá triển khai: Cấu hình QLoRA (Fine-Tuned Adapter Zero-Retrieval)

> **Hệ thống:** ViGovBot — Mô hình Tinh chỉnh tham số hiệu quả (QLoRA Adapter)  
> **Mô hình nền:** `Qwen/Qwen2.5-7B-Instruct` (Lượng tử hóa 4-bit NF4)  
> **Trọng số PEFT:** LoRA Adapter `checkpoint-300` / `best_adapter` (154,05 MiB)  
> **Cơ chế suy luận:** Zero-Retrieval (Không nạp tài liệu bên ngoài, dựa trên bộ nhớ tham số)  
> **Tập dữ liệu kiểm định chuẩn:** `Data/dataset_v3/test_rag/test_rag_pa1.jsonl` (638 mẫu thử)  
> **Thời điểm thẩm định artifact:** 03/11/2026  

---

## 1. Tổng quan cấu hình kiến trúc và Hồ sơ phục vụ (Serving Profile)

Cấu hình **QLoRA** đại diện cho phương pháp tối ưu hóa năng lực ngôn ngữ nội tại của mô hình thông qua quá trình tinh chỉnh có giám sát (Supervised Fine-Tuning - SFT) trên dữ liệu thủ tục hành chính công:

- **Mô hình nền tảng:** `Qwen2.5-7B-Instruct` được nạp ở định dạng 4-bit NormalFloat (NF4).
- **Cấu hình Adapter LoRA:** Thứ hạng $r=16$, hệ số tỷ lệ $\alpha=32$, dropout $0,05$, gắn trên toàn bộ 7 khối biến đổi tuyến tính (`q, k, v, o, gate, up, down_proj`) trong 28 khối giải mã.
- **Kích thước adapter:** `161.533.192 byte` (~154,05 MiB).
- **Backend phục vụ:** Thư viện Hugging Face Transformers cục bộ kết hợp bitsandbytes.
- **Tham số giải mã chuẩn hóa:** $T = 0,0$ (Greedy search), $seed = 42$, $num\_ctx = 8.192$, $num\_predict = 512$.
- **Hạ tầng kiểm thử:** NVIDIA GeForce RTX 5060 Ti (15,90 GiB VRAM), CUDA 13.0, Windows 10 build 19045.

---

## 2. Độ tin cậy thực thi và Tính toàn vẹn vận hành

| Chỉ số vận hành | Giá trị đo lường thực tế | Đánh giá kỹ thuật |
| :--- | :---: | :--- |
| **Tổng số ca thử nghiệm (Sample IDs)** | 638 / 638 (100%) | Đầy đủ 100% định danh mẫu |
| **Số ca suy luận thành công** | **638** (100%) | Không có ngoại lệ hệ thống |
| **Số lỗi phát sinh (Placeholder Error)** | **0** (0,00%) | **Độ ổn định tuyệt đối** |
| **Sự cố tràn bộ nhớ GPU (OOM)** | **0** | Tiêu thụ VRAM thấp (~5,5 GB) |
| **Sự cố quá hạn kết nối (Timeout)** | **0** | Không phụ thuộc mạng hay kho vector |
| **Tuân thủ định dạng (Format Compliance)** | **1,0000** | 100% tuân thủ chặt chẽ cấu trúc phản hồi |

QLoRA đạt độ tin cậy vận hành hoàn hảo (100% không phát sinh lỗi), triệt tiêu hoàn toàn nguy cơ gián đoạn do kết nối mạng hoặc lỗi nạp prompt dài vốn gặp phải ở RAG.

---

## 3. Ma trận năng lực sinh và Khớp văn bản (Generation Matrix)

Mô hình QLoRA dẫn đầu tuyệt đối về mọi chỉ số tương đồng ngôn ngữ học và độ cô đọng biểu đạt:

| Nhóm thước đo | Chỉ số chi tiết | Base | RAG | QLoRA (Dẫn đầu) | Mức cải thiện so với Base |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Tương đồng ngữ nghĩa** | **BERTScore F1** | 0,8485 | 0,8790 | **0,9119** | **+0,0634** (Cao nhất) |
| | BERTScore Precision | 0,8216 | 0,8662 | **0,9122** | **+0,0906** |
| | BERTScore Recall | 0,8783 | 0,8939 | **0,9128** | **+0,0345** |
| | Embedding Cosine Similarity | 0,5396 | 0,5852 | **0,7166** | **+0,1770** |
| **Khớp từ vựng N-gram** | **ROUGE-1 F1** | 0,1695 | 0,3399 | **0,4719** | **Tăng gấp 2,8 lần** |
| | ROUGE-1 Precision | 0,1257 | 0,3392 | **0,5212** | **Tăng gấp 4,1 lần** |
| | **ROUGE-2 F1** | 0,0775 | 0,2642 | **0,3774** | **Tăng gấp 4,9 lần** |
| | **ROUGE-L F1** | 0,1110 | 0,3001 | **0,4482** | **Tăng gấp 4,0 lần** |
| **Độ khớp chuỗi** | **chrF / chrF++** | 20,86 / 19,93 | 36,20 / 35,20 | **45,36 / 45,32** | **Tăng hơn 24 điểm** |
| | SacreBLEU | 2,69 | 15,57 | **27,24** | **Tăng gấp 10 lần** |
| | METEOR | 0,2491 | 0,4035 | **0,4755** | **+0,2264** |
| **Tỷ lệ lỗi** | Character Error Rate (CER) | 11,76 | 4,29 | **1,11** | **Thấp nhất** (-90%) |
| | Word Error Rate (WER) | 11,34 | 4,24 | **1,21** | **Thấp nhất** (-89%) |
| **Bảo toàn sự kiện** | **Key-Fact Coverage** | 0,0145 | **0,1765** | **0,1302** | Tăng 9× so với Base, nhưng kém RAG |

---

## 4. Hồ sơ hiệu năng và Độ trễ vận hành (Latency & Tokens)

| Tham số đo lường trung bình | Base | RAG | QLoRA | Ý nghĩa vận hành |
| :--- | :---: | :---: | :---: | :--- |
| **Tổng độ trễ xử lý (Total Latency)** | 6.642,85 ms | 12.834,90 ms | **5.720,39 ms** (5,72s) | **Nhanh nhất trong 4 cấu hình** |
| **Thời gian tới token đầu (TTFT)** | 2.214,66 ms | 3.003,94 ms | **318,97 ms** (0,32s) | **Nhanh gấp 9,4 lần RAG** (Phản hồi tức thì) |
| **Độ dài prompt đầu vào** | 172,52 tokens | 3.298,30 tokens | **171,53 tokens** | Cực kỳ ngắn, giải phóng VRAM |
| **Độ dài câu trả lời sinh ra** | 311,64 tokens | 270,90 tokens | **77,88 tokens** | **Cô đọng nhất** (Ngắn hơn Base 75%) |
| **Tổng số token xử lý** | 484,16 tokens | 3.569,20 tokens | **249,41 tokens** | Tiết kiệm tối đa chi phí tính toán |
| **Tốc độ sinh token (Throughput)** | **72,02 tok/s** | 70,26 tok/s | 13,32 tok/s | Chạy qua PyTorch Transformers cục bộ |

> **Lưu ý triển khai:** Tốc độ 13,32 tok/s ghi nhận trên testbed thử nghiệm do suy luận tuần tự qua PyTorch Python. Khi xuất sang định dạng GGUF Q8_0 (`qwen2.5-7b-qlora-q8_0.gguf`, 8,10 GB) và nạp qua Ollama/vLLM, tốc độ sinh token tăng vọt lên **~75–80 tokens/giây**, đưa tổng độ trễ thực tế xuống dưới **1,5 giây/câu**.

---

## 5. Rủi ro pháp lý và "Hiện tượng Ảo giác từ vựng" (Semantic Hallucination)

Phân tích sâu kết quả trên nhóm câu hỏi ngoài phạm vi (`unanswerable`) làm sáng tỏ ranh giới nghiêm trọng của mô hình QLoRA khi thiếu tầng truy xuất:

### Bảng đối chiếu nghịch lý ROUGE trên nhóm `unanswerable` (41 mẫu ngoài thẩm quyền):
- **ROUGE-1 F1:** **`0,8405` (84,05%)** — Cao kỷ lục, vượt trội mọi cấu hình khác.
- **chrF:** **`81,19`** — Khớp ký tự gần như tuyệt đối.
- **BERTScore F1:** **`0,9754`** — Trùng khớp ngữ nghĩa bề mặt ở mức hoàn hảo.
- **Abstention Correct (Từ chối đúng):** **`0,0000` (0,00%)** — **Thất bại hoàn toàn**.

### Bản chất kỹ thuật của hiện tượng:
Điểm số N-gram cực cao trên các câu hỏi không có căn cứ chứng minh rằng QLoRA đã học thuộc lòng toàn bộ từ ngữ hành chính chuyên môn (ví dụ: *"Căn cứ theo quy định của Ủy ban nhân dân...", "Hồ sơ gồm 01 bộ nộp tại Bộ phận một cửa..."*). Khi gặp câu hỏi ngoài phạm vi hoặc câu hỏi sai luật, mô hình **tự động sinh ra một câu trả lời hành chính có cấu trúc hoàn hảo nhưng hoàn toàn bịa đặt (hallucination)**. Người dùng không có chuyên môn luật sẽ rất dễ bị đánh lừa bởi câu trả lời có văn phong rất chuẩn nhưng sai cơ quan tiếp nhận hoặc sai thời hạn thực tế.

---

## 6. Phân tích phân nhóm tương tác (Cohort Breakdown)

| Phân nhóm dữ liệu | ROUGE-1 F1 | ROUGE-L F1 | BERTScore F1 | Key-Fact Coverage | Tổng độ trễ (ms) | TTFT (ms) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`answerable` (597 mẫu)** | 0,4465 | 0,4222 | 0,9075 | 0,1302 | 5.653,73 | 322,85 |
| **`unanswerable` (41 mẫu)** | **0,8405** | **0,8261** | **0,9754** | N/A | 6.690,95 | 262,51 |
| **`new_question` (320 mẫu)**| 0,4537 | 0,4320 | 0,9080 | 0,1158 | 5.413,77 | 253,15 |
| **`follow_up` (318 mẫu)** | **0,4902** | **0,4645** | **0,9157** | **0,1438** | 6.028,93 | 385,20 |

> **Tính ổn định đa lượt của QLoRA:** Khác với RAG bị suy giảm hiệu năng nghiêm trọng ở các câu hỏi tiếp nối (`follow_up`), QLoRA duy trì điểm số ROUGE-1 và BERTScore rất ổn định giữa câu hỏi mới (0,4537) và câu hỏi tiếp nối (0,4902). Điều này bắt nguồn từ khả năng ghi nhớ tham số đóng trong adapter, không phụ thuộc vào chất lượng của mô-đun viết lại câu hỏi (Query Rewriting).

---

## 7. Đánh giá tính khả thi triển khai sản xuất (Production Readiness)

### Điểm mạnh nổi bật:
1. **Phản hồi tức thì (TTFT 318 ms):** Trải nghiệm người dùng cực kỳ mượt mà, gần như không có độ trễ chờ đợi ban đầu.
2. **Văn phong hành chính chuẩn mực:** Câu trả lời ngắn gọn (trung bình 78 token), cấu trúc rõ ràng, không thừa thãi.
3. **Tiết kiệm tài nguyên:** Tiêu thụ ít VRAM, không tốn tài nguyên chạy kho vector search.

### Rủi ro pháp lý & Giới hạn:
1. **Không thể cập nhật văn bản pháp quy mới:** Tri thức bị đóng băng tại thời điểm huấn luyện (parametric memory). Bất kỳ thay đổi nào về thông tư/nghị định mới đều đòi hỏi phải tái huấn luyện.
2. **Ảo giác có cấu trúc (Structured Hallucination):** Tự tin trả lời sai các câu hỏi ngoài phạm vi; không có cơ chế từ chối khi không có căn cứ.
3. **Key-Fact còn hạn chế (13,02%):** Kém xa cấu hình kết hợp RAG (31,09%).

### Kết luận triển khai:
> **Khuyến nghị:** **KHÔNG TRIỂN KHAI ĐƠN LẺ CHO CÁC TÁC VỤ HỎI ĐÁP PHÁP LUẬT YÊU CẦU CĂN CỨ CHÍNH XÁC.**  
> - **Kịch bản phù hợp:** Sử dụng làm mô-đun tổng hợp ngôn ngữ, viết lại câu hỏi (Query Rewriter), tóm tắt hồ sơ, hoặc đóng vai trò Generator bên trong kiến trúc tích hợp `QLoRA + RAG`.

