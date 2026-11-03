# Báo cáo đánh giá triển khai: Cấu hình Qwen2.5-7B Base (Zero-Shot)

> **Hệ thống:** ViGovBot — Cấu hình đối chứng chuẩn (Baseline Architecture)  
> **Mô hình phục vụ:** `Qwen/Qwen2.5-7B` (Mô hình nền tảng nguyên bản, Zero-Shot)  
> **Backend phục vụ:** Ollama API (`http://127.0.0.1:8000/api/chat`)  
> **Tập dữ liệu kiểm định chuẩn:** `Data/dataset_v3/test_rag/test_rag_pa1.jsonl` (638 mẫu thử)  
> **Thời điểm thẩm định artifact:** 03/11/2026  

---

## 1. Tổng quan cấu hình kiến trúc và Hồ sơ phục vụ (Architecture & Serving Profile)

Cấu hình **Base** đóng vai trò là mốc đối chứng khoa học (baseline control) nhằm cô lập và định lượng chính xác giá trị gia tăng của các kỹ thuật truy xuất tăng cường (RAG) và tinh chỉnh tham số hiệu quả (QLoRA):

- **Mô hình cốt lõi:** `Qwen2.5-7B` (phiên bản trọng số nguyên bản đóng băng).
- **Cơ chế suy luận:** Zero-shot inference, không có adapter LoRA và không tích hợp tầng truy xuất tài liệu bên ngoài (Zero-Retrieval).
- **Backend phục vụ:** Nạp và suy luận thông qua máy chủ Ollama cục bộ.
- **Tham số giải mã chuẩn hóa:** $T = 0,0$ (Greedy search), $seed = 42$, cửa sổ ngữ cảnh $num\_ctx = 8.192$ tokens, giới hạn sinh $num\_predict = 512$ tokens.
- **Hạ tầng phần cứng:** 1x NVIDIA GeForce RTX 5060 Ti (VRAM 15,90 GiB khả dụng), CUDA 13.0, Windows 10 build 19045.

---

## 2. Độ tin cậy thực thi và Tính toàn vẹn vận hành

Kiểm tra trực tiếp trên toàn bộ 638 mẫu kiểm định chuẩn hóa v3:

| Chỉ số vận hành | Giá trị đo lường thực tế | Tỷ lệ / Đánh giá |
| :--- | :---: | :---: |
| **Tổng số ca thử nghiệm (Sample IDs)** | 638 / 638 | 100,00% |
| **Số ca suy luận thành công** | **638** | **100,00%** |
| **Số lỗi phát sinh (Placeholder Error)** | **0** | **0,00%** (Tuyệt đối ổn định) |
| **Sự cố tràn bộ nhớ GPU (OOM)** | **0** | An toàn bộ nhớ |
| **Sự cố quá hạn kết nối (Timeout)** | **0** | Không nghẽn kết nối |
| **Tuân thủ định dạng (Format Compliance)** | **1,0000** | 100% tuân thủ cấu trúc |

Mô hình Base duy trì độ ổn định kỹ thuật tuyệt đối (100% phản hồi thành công, không phát sinh lỗi kết nối hay lỗi nạp ngữ cảnh), tạo nền tảng đối chứng vững chắc cho toàn bộ benchmark.

---

## 3. Ma trận năng lực sinh và Bảo toàn sự kiện (Generation & Key-Fact Metrics)

| Nhóm thước đo | Chỉ số chi tiết | Giá trị đo lường | Nhận định kỹ thuật |
| :--- | :--- | :---: | :--- |
| **Bảo toàn sự kiện** | **Key-Fact Coverage** | **0,0145** (1,45%) | **Thiếu hụt nghiêm trọng**: Không nắm được các thực thể thủ tục cụ thể. |
| **Tương đồng ngữ nghĩa** | BERTScore F1 | 0,8485 | Thể hiện khả năng hiểu ngôn ngữ chung của mô hình 7B gốc. |
| | BERTScore Precision | 0,8216 | |
| | BERTScore Recall | 0,8783 | |
| | Embedding Cosine Similarity | 0,5396 | Mức độ tương đồng vector trung bình. |
| **Khớp từ vựng N-gram** | ROUGE-1 F1 | 0,1695 | Điểm N-gram thấp do phong cách trả lời không đồng nhất với mẫu chuẩn. |
| | ROUGE-1 Precision | 0,1257 | Độ chính xác từ vựng thấp (trả lời dài dòng, dư thừa). |
| | ROUGE-1 Recall | 0,5230 | Bao phủ được một số từ vựng phổ biến. |
| | ROUGE-2 F1 | 0,0775 | Rất ít cụm 2 từ liên tiếp khớp với đáp án chuẩn. |
| | ROUGE-L F1 | 0,1110 | Trật tự chuỗi từ vựng khác biệt lớn so với văn phong chuyên ngành. |
| **Độ khớp chuỗi** | chrF / chrF++ | 20,86 / 19,93 | Khớp ký tự mức thấp. |
| | SacreBLEU | 2,69 | Điểm BLEU ở mức không đáng kể. |
| | METEOR | 0,2491 | |
| **Tỷ lệ lỗi** | Character Error Rate (CER) | 11,76 | Tỷ lệ lỗi ký tự cao nhất trong 4 mô hình. |
| | Word Error Rate (WER) | 11,34 | Tỷ lệ lỗi từ ngữ cao nhất trong 4 mô hình. |
| | Exact Match (EM) | 0,0000 | 0/638 câu khớp chính xác tuyệt đối. |

---

## 4. Kỷ luật hành vi và Khả năng từ chối (Robustness & Abstention)

- **Abstention Correct (Từ chối đúng):** **`0,0000` (0,00%)** — Mô hình Base hoàn toàn **không có khả năng từ chối**. Khi gặp câu hỏi ngoài phạm vi, câu hỏi không có căn cứ hoặc câu hỏi sai thẩm quyền, mô hình tự động suy đoán và bịa đặt thông tin (hallucination) 100% các trường hợp.
- **Action Accuracy:** `0,9357` (Do phần lớn các câu hỏi thuộc nhóm `answer`).
- **Năng lực truy xuất & Định tuyến:** `N/A` (Không áp dụng vì mô hình không tích hợp pipeline truy xuất).

---

## 5. Hiệu năng tính toán và Hồ sơ tài nguyên

| Tham số đo lường | Giá trị trung bình | Đánh giá vận hành |
| :--- | :---: | :--- |
| **Tổng thời gian xử lý (Total Latency)** | **6.642,85 ms** (6,64s) | Thời gian phản hồi chấp nhận được ở concurrency 1. |
| **Thời gian tới token đầu (TTFT)** | **2.214,66 ms** (2,21s) | Trễ giai đoạn khởi tạo sinh của Ollama. |
| **Thời gian sinh (Generation Latency)** | **4.428,19 ms** | Chiếm 66,7% tổng thời gian phục vụ. |
| **Tốc độ sinh token (Throughput)** | **72,02 tokens/giây** | Tốc độ giải mã cao nhất trong các mô hình. |
| **Độ dài ngữ cảnh đầu vào (Prompt)** | **172,52 tokens** | Cực kỳ ngắn do không kèm ngữ cảnh tài liệu. |
| **Độ dài phản hồi sinh ra (Completion)**| **311,64 tokens** | **Dài dòng nhất**: Xu hướng giải thích lan man, không cô đọng. |
| **Tổng số token xử lý** | **484,16 tokens** | Tiêu thụ ít bộ nhớ ngữ cảnh. |

---

## 6. Phân tích phân nhóm tương tác (Cohort Breakdown)

| Phân nhóm dữ liệu | ROUGE-1 F1 | ROUGE-L F1 | BERTScore F1 | Key-Fact Coverage | Abstention Correct |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Cohort 1: `answerable` (597 mẫu)** | 0,1580 | 0,1047 | 0,8467 | **0,0145** | N/A |
| **Cohort 2: `unanswerable` (41 mẫu)** | 0,3364 | 0,2034 | 0,8743 | N/A | **0,0000** (Suy đoán 100%) |
| **Cohort 3: `new_question` (320 mẫu)** | 0,1628 | 0,1068 | 0,8444 | 0,0253 | 0,0000 |
| **Cohort 4: `follow_up` (318 mẫu)** | 0,1762 | 0,1153 | 0,8526 | **0,0042** (Gần như mất trắng) | 0,0000 |

---

## 7. Đánh giá tính khả thi triển khai sản xuất (Production Readiness)

### Điểm mạnh:
1. **Tốc độ sinh cao (72 tok/s):** Khả năng giải mã nhanh, không bị nghẽn bởi việc nạp văn bản tài liệu lớn.
2. **Độ ổn định kỹ thuật tuyệt đối (100%):** Không phát sinh lỗi hệ thống hay timeout.

### Rủi ro nghiêm trọng khi đưa vào môi trường hành chính công:
1. **Rủi ro ảo giác pháp lý (Hallucination 100% trên unanswerable):** Không có khả năng từ chối câu hỏi ngoài thẩm quyền; tự bịa đặt cơ quan tiếp nhận và quy trình làm người dân có thể mất quyền hoặc làm sai thủ tục.
2. **Thiếu hụt tri thức chuyên ngành (Key-Fact chỉ 1,45%):** Không nắm được thông tin chi tiết về lệ phí, thành phần hồ sơ, thời hạn giải quyết cụ thể của từng địa phương.
3. **Phong cách trả lời thiếu chuẩn mực:** Trả lời dài dòng (~312 token/câu) nhưng thiếu thông tin định lượng cần thiết.

### Kết luận triển khai:
> **Khuyến nghị:** **TUYỆT ĐỐI KHÔNG TRIỂN KHAI ĐƠN LẺ TRONG MÔI TRƯỜNG DỊCH VỤ CÔNG THỰC TẾ.**  
> Cấu hình Base chỉ đóng vai trò là mẫu chuẩn đối chứng (Baseline Control) để kiểm chứng hiệu quả cải tiến của hệ thống RAG và mô hình tinh chỉnh QLoRA.

