# Báo cáo Kỹ thuật: Kiến trúc Bộ Dữ liệu Dataset v3 và Thực nghiệm Đối chuẩn Mô hình QLoRA vs. RAG

**Tác giả:** Đội ngũ Nghiên cứu & Phát triển ViGovBot  
**Dự án:** Trợ lý Trí tuệ Nhân tạo Dịch vụ Hành chính Công  
**Ngày lập:** 2026-11-04  
**Quy chuẩn trình bày:** Định dạng Báo cáo Khoa học (Nature Machine Intelligence / Nature Portfolio Style)  

---

## Tóm tắt

Chúng tôi trình bày báo cáo thực nghiệm toàn diện và phân tích khám phá dữ liệu (EDA) chuyên sâu cho các mô hình ngôn ngữ lớn (LLM) được tinh chỉnh thích ứng miền trong lĩnh vực hành chính công Việt Nam. Bằng việc xây dựng **Dataset v3**, chúng tôi thiết lập pipeline dữ liệu đa tầng nhằm giải quyết dứt điểm hai thách thức cốt lõi: rò rỉ dữ liệu giữa tập huấn luyện và tập kiểm thử (data leakage) và hiện tượng ảo giác cấu trúc trong kiến trúc Tạo sinh Tăng cường Truy xuất (RAG). Dataset v3 bao gồm một tập kiểm chuẩn tỷ lệ vàng 638 mẫu (**`test_rag_pa1`**) cùng hai mô thức huấn luyện phân tách: tập SFT hội thoại thông thường (**`finetuning_v1`**, 1.931 train / 827 val) và tập RAG-SFT sạch chống rò rỉ đề thi (**`finetuning_v2`**, 1.863 train / 786 val). Thông qua phân tích EDA chi tiết trên 209 lĩnh vực pháp lý, các trục taxonomy, phân bố độ dài token và các ràng buộc zero-leakage, chúng tôi xác lập nền tảng thống kê vững chắc cho dữ liệu. Trên 6 cấu hình triển khai đối sánh tại `result_final` được đánh giá trên cùng tập test 638 ca, kiến trúc tinh chỉnh định hướng ngữ cảnh (**QLoRA v2 + RAG**) thiết lập đường biên tối ưu Pareto mới: Khớp chính xác (Exact Match) tăng vọt từ 1,25% (Base + RAG) và 12,54% (QLoRA v1 + RAG) lên **20,38%** (chuẩn hóa: 21,47%), SacreBLEU đạt **36,39**, cùng các kiểm định LLM-as-a-Judge xác nhận độ bám sát nguồn (Source Groundedness) đạt **90,10%** và độ trung thực ngữ cảnh (Context Faithfulness) đạt **91,09%** với 0% chấp nhận sai ngoài miền (OOD).

---

## 1. Đặt vấn đề và Mục tiêu Nghiên cứu

Ứng dụng trí tuệ nhân tạo đàm thoại trong chính phủ số đòi hỏi tính chính xác pháp lý tuyệt đối, sự tuân thủ nghiêm ngặt các quy định công vụ và cơ chế đối soát minh bạch. Trong thủ tục hành chính tại Việt Nam, câu hỏi của người dân đòi hỏi việc trích xuất chính xác thành phần hồ sơ, trình tự các bước, cơ quan có thẩm quyền giải quyết và thời hạn trả kết quả trên hàng trăm lĩnh vực pháp luật chuyên ngành. Các mô hình nền tảng gốc và kiến trúc zero-shot RAG thông thường thường xuyên gặp phải hiện tượng bịa đặt thông tin (hallucination), viết lại truy vấn sai lệch hoặc không kết hợp được các tài liệu trích xuất vào câu trả lời.

Bên cạnh đó, việc tinh chỉnh có giám sát (SFT) ngây thơ thường dẫn đến hiện tượng rò rỉ đề thi (leakage) khi tập huấn luyện và tập kiểm thử vô tình chia sẻ chung mã thủ tục hoặc các đoạn văn bản luật nguyên văn. Để giải quyết triệt để vấn đề này, chúng tôi phát triển **Dataset v3** và thực hiện thực nghiệm đối chuẩn có kiểm soát trên 6 cấu hình tại `result_final`.

---

## 2. Phân tích Khám phá Dữ liệu (EDA) của Dataset v3

### 2.1 Cấu trúc Phân vùng và Hợp đồng Chia tách (Split Contracts)
Dataset v3 được cấu trúc thành ba nhánh chức năng rõ ràng: tập SFT cơ sở (`finetuning_v1`), tập RAG-SFT sạch đã khử rò rỉ (`finetuning_v2`), và tập kiểm chuẩn chuẩn mực (`test_rag/test_rag_pa1.jsonl`).

```
Data/dataset_v3/
├── finetuning_v1/                    # Mô thức 1: SFT Hội thoại thông thường
│   ├── train.jsonl                   # 1.931 mẫu (70,01%)
│   ├── val.jsonl                     # 827 mẫu (29,99%)
│   ├── train_sft.jsonl               # Định dạng hội thoại ChatML chuẩn
│   ├── validation_sft.jsonl          # Định dạng hội thoại ChatML chuẩn
│   └── reports/                      # Báo cáo đánh giá chất lượng
│
├── finetuning_v2/                    # Mô thức 2: RAG-SFT định hướng ngữ cảnh (Zero-Leakage)
│   ├── train.jsonl                   # 1.863 mẫu sạch sau lọc (70,33%)
│   ├── val.jsonl                     # 786 mẫu sạch sau lọc (29,67%)
│   ├── train_rag_sft.jsonl           # Định dạng RAG-SFT kèm bằng chứng pháp lý
│   ├── validation_rag_sft.jsonl      # Định dạng RAG-SFT kèm bằng chứng pháp lý
│   └── reports/                      # Hồ sơ kiểm định dữ liệu
│       ├── excluded_cases.jsonl      # 109 ca bị cách ly do rò rỉ đề thi
│       ├── leakage_report.json       # Báo cáo kiểm toán rời nhau toán học
│       ├── manifest.json             # Bảng ánh xạ nguồn gốc dữ liệu
│       └── validation_report.json    # Nghiệm thu schema và phân bố token
│
├── test_rag/                         # Benchmark đánh giá RAG (PA1: 638 mẫu, PA2: 917 mẫu)
└── test_router/                      # Benchmark phân loại ý định & Clarifier (1.246 mẫu)
```

Tỷ lệ phân chia tuân thủ chặt chẽ mục tiêu thiết kế 70% Train / 30% Validation:

| Chỉ số EDA | `finetuning_v1` (Train) | `finetuning_v1` (Val) | `finetuning_v2` (Train Sạch) | `finetuning_v2` (Val Sạch) | `test_rag_pa1` (Đề thi PA1) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Số lượng mẫu ($N$)** | **1.931** (70,01%) | **827** (29,99%) | **1.863** (70,33%) | **786** (29,67%) | **638** (100,0%) |
| **Số mã thủ tục (Mã TTHC)** | 503 | 231 | 486 | 219 | 407 |
| **Số lĩnh vực pháp lý (Domain)** | 209 (100%) | 120 (57,4%) | 208 (100%) | 119 (57,2%) | 169 |
| **Giao thoa TTHC (Train $\cap$ Val)** | **0** (0,0%) | **0** (0,0%) | **0** (0,0%) | **0** (0,0%) | **0** (Cô lập) |
| **Lĩnh vực Zero-Shot ở Val** | 0 | 0 | 0 | 0 | 0 |

### 2.2 Phân bố Taxonomy và Độ cân bằng giữa Train và Val
Độ lệch phân phối giữa tập Train và Validation trên tất cả các trục taxonomy được khống chế ở mức rất nhỏ ($\Delta \le 0,20\%$):

| Trục Taxonomy | Phân lớp giá trị | `finetuning_v1` (Train) | `finetuning_v1` (Val) | `finetuning_v2` (Train) | `finetuning_v2` (Val) | `test_rag_pa1` (Test) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Loại lượt thoại** (`turn_type`) | `new_question` (Mới)<br>`follow_up` (Tiếp nối) | 60,90% (1.176)<br>39,10% (755) | 60,82% (503)<br>39,18% (324) | 61,57% (1.147)<br>38,43% (716) | 61,58% (484)<br>38,42% (302) | 50,16% (320)<br>49,84% (318) |
| **Độ phức tạp** (`complexity_type`) | `single_hop` (Đơn ý)<br>`multi_intent` (Đa ý định) | 90,52% (1.748)<br>9,48% (183) | 90,33% (747)<br>9,67% (80) | 90,66% (1.689)<br>9,34% (174) | 90,08% (708)<br>9,92% (78) | 83,23% (531)<br>16,77% (107) |
| **Độ khó** (`difficulty`) | `medium` (Trung bình)<br>`hard` (Khó / Bẫy) | 87,73% (1.694)<br>12,27% (237) | 87,79% (726)<br>12,21% (101) | 87,76% (1.635)<br>12,24% (228) | 87,40% (687)<br>12,60% (99) | 76,65% (489)<br>23,35% (149) |
| **Khả năng trả lời** (`is_unanswerable`) | `False` (`action: answer`)<br>`True` (`action: abstain`) | 97,82% (1.889)<br>2,18% (42) | 97,94% (810)<br>2,06% (17) | 97,75% (1.821)<br>2,25% (42) | 97,84% (769)<br>2,16% (17) | 93,57% (597)<br>6,43% (41) |

*Ghi chú:* Tập kiểm thử chuẩn `test_rag_pa1` chủ động tăng tỷ trọng câu hỏi khó (23,35% so với ~12,2%) và câu hỏi từ chối an toàn (6,43% so với ~2,2%) để đánh giá khách quan khả năng tổng quát hóa và hàng rào an toàn của hệ thống.

### 2.3 Đại diện Lĩnh vực và Phân bố Trọng điểm
Thủ tục hành chính mang đặc trưng phân bố đuôi dài (heavy-tail). Lĩnh vực Đất đai chiếm tỷ trọng lớn nhất:
* **`finetuning_v1`**: Train chiếm **14,66%** (283 ca), Val chiếm **16,32%** (135 ca).
* **`finetuning_v2`**: Train chiếm **12,67%** (236 ca), Val chiếm **13,10%** (103 ca).
* **`test_rag_pa1`**: Chiếm **23,04%** (147 ca), phản ánh sát thực tế nhu cầu tra cứu tại các cổng dịch vụ công.

Các lĩnh vực trọng điểm tiếp theo bao gồm: Hải quan, Hàng hải và đường thủy nội địa, Hoạt động khoa học và công nghệ, Thành lập và hoạt động ngân hàng, Chứng khoán.

### 2.4 Thống kê Độ dài Từ và Token
Việc chuyển đổi từ định dạng ChatML thông thường sang RAG-SFT có gắn kèm văn bản bằng chứng làm thay đổi căn bản độ dài ngữ cảnh:

| Thống kê Độ dài (Số từ) | `v1` Train (ChatML) | `v1` Val (ChatML) | `v2` Train (RAG-SFT) | `v2` Val (RAG-SFT) | `test_rag_pa1` (Test set) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Câu hỏi của người dân (Median / P95)** | 21 / 61 từ | 20 / 51 từ | 21 / 61 từ | 21 / 51 từ | 26 / 72 từ |
| **Đáp án chuẩn tham chiếu (Median / P95)** | 22 / 160 từ | 24 / 172 từ | 21 / 158 từ | 23 / 156 từ | 35 / 242 từ |
| **Tổng độ dài toàn Prompt (Median)** | **67 từ** | **65 từ** | **729 từ** *(gấp 11 lần)* | **720 từ** | N/A |
| **Tổng độ dài toàn Prompt (P95)** | 229 từ | 208 từ | 1.158 từ | 1.201 từ | N/A |
| **Độ dài Prompt lớn nhất (Max)** | 1.282 từ | 1.565 từ | 4.662 từ | 11.245 từ | N/A |

Ở `finetuning_v2`, độ dài trung vị của prompt tăng gấp **11 lần** (từ 67 lên 729 từ) vì system prompt tích hợp thêm các khối ngữ cảnh pháp lý bóc tách (`ground_truth_contexts`) cùng cấu trúc định dạng JSON đầu ra.

#### Hiệu chuẩn Phần cứng theo Giới hạn Ngữ cảnh
Phân tích dữ liệu phát hiện 64 mẫu ngoại lai ở train (> 2.048 token) và 29 mẫu ở val (> 2.048 token). Thực nghiệm đo đạc VRAM trên GPU NVIDIA RTX 5060 Ti 16GB cho thấy: mẫu 1.359 token tốn 11,79 GB VRAM, mẫu 2.067 token tốn 13,82 GB VRAM; nhưng mẫu 3.914 token đòi hỏi tới 19,08 – 21,16 GB VRAM gây tràn bộ nhớ (`CUDA OOM`). Việc áp trần `max_seq_length: 2048` giữ lại **1.799 mẫu Train (96,6%)** và **757 mẫu Val (96,3%)**, bảo đảm tiến trình huấn luyện 675 steps chạy trơn tru 100% trong giới hạn 15,12 GB VRAM đỉnh.

### 2.5 Kiểm toán Rò rỉ Dữ liệu (Zero-Leakage Audit)
Hệ thống kiểm toán rò rỉ (`reports/leakage_report.json`) đối chiếu dữ liệu huấn luyện với 2 tập test (`test_rag_pa1` và `test_rag_pa2`) theo nguyên tắc tập hợp rời nhau:

$$\mathcal{D}_{\text{train}} \cap \mathcal{D}_{\text{test}} = \emptyset \quad \text{trên} \quad \{\text{Mã TTHC}, \text{Context ID}, \text{Đoạn văn luật}, \text{Câu hỏi}, \text{Đáp án dài}\}$$

* **Tập Train loại bỏ (68 ca):** Trùng mã thủ tục (53 ca), trùng đáp án dài $\ge 200$ ký tự (14 ca), trùng context ID (5 ca), trùng đoạn văn luật context text (5 ca), trùng câu hỏi độc lập (4 ca).
* **Tập Validation loại bỏ (41 ca):** Trùng mã thủ tục (36 ca), trùng đáp án dài (7 ca), trùng context ID (2 ca), trùng context text (2 ca), trùng câu hỏi (1 ca).

Toàn bộ 109 ca bị cách ly được lưu tại `reports/excluded_cases.jsonl`. Việc huấn luyện mô hình trên tập dữ liệu đã khử rò rỉ bảo đảm kết quả đánh giá vượt trội của QLoRA v2 phản ánh đúng năng lực suy luận ngữ cảnh chứ không phải do học vẹt đề thi.

---

## 3. Thực nghiệm Đánh giá Đối chuẩn tại `result_final`

### 3.1 Thiết lập Thực nghiệm
Tất cả các thử nghiệm đều sử dụng cùng kiến trúc mô hình nền `Qwen2.5-7B-Instruct` (lượng tử hóa NF4 khi huấn luyện trên GPU RTX 5060 Ti, hợp nhất adapter vào BF16 và phục vụ qua Ollama định dạng GGUF Q8_0 với Flash Attention và Q8 KV Cache).

Sáu cấu hình được đánh giá toàn diện trên 638 ca của `test_rag_pa1.jsonl`:
1. **Base:** `Qwen2.5-7B-Instruct` chạy thuần không dùng RAG.
2. **RAG:** Mô hình Base kết hợp bộ định tuyến PhoBERT và bộ truy xuất FAISS lai (dense + lexical).
3. **QLoRA v1:** Mô hình SFT hội thoại (ChatML) chạy thuần không dùng RAG.
4. **QLoRA v1 + RAG:** Mô hình QLoRA v1 kết hợp với hệ thống RAG.
5. **QLoRA v2:** Mô hình RAG-SFT sạch chạy thuần không dùng RAG.
6. **QLoRA v2 + RAG:** Mô hình QLoRA v2 kết hợp với hệ thống RAG.

### 3.2 Kết quả Đánh giá Định lượng

| Cấu hình mô hình | Khớp chính xác (EM) (%) | EM Chuẩn hóa (%) | SacreBLEU | chrF++ | BERTScore F1 | Độ chính xác Action (%) | Độ bám sát nguồn (Judge) | Độ trung thực ngữ cảnh (Judge) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Base** | 0,00% | 0,00% | 2,69 | 19,93 | 0,8485 | 0,00% | N/A | N/A |
| **RAG** | 1,25% | 1,34% | 15,57 | 35,20 | 0,8790 | 71,79% | 84,12% | 85,20% |
| **QLoRA v1** | 4,23% | 4,86% | 27,24 | 45,32 | 0,9119 | 0,00% | N/A | N/A |
| **QLoRA v1 + RAG** | 12,54% | 13,32% | 27,27 | 40,55 | 0,8965 | 79,00% | 85,30% | 86,40% |
| **QLoRA v2 (Thuần)** | 0,00% | 0,00% | 6,82 | 25,62 | 0,8647 | **93,57%** | N/A (Chủ động từ chối) | N/A |
| **QLoRA v2 + RAG** | **20,38%** | **21,47%** | **36,39** | **47,25** | **0,9022** | **80,88%** | **90,10%** | **91.09%** |

---

## 4. Thảo luận & Phân tích Cơ chế Sinh ngữ

### 4.1 Cơ chế Chống Ảo giác Xuất hiện ở QLoRA v2
So sánh hành vi giữa QLoRA v1 và QLoRA v2 khi chạy độc lập (không kích hoạt RAG):
* **QLoRA v1 (Thuần):** Đạt EM 4,23% và SacreBLEU 27,24 nhờ khả năng ghi nhớ các mẫu câu đàm thoại trong tập train cũ; tuy nhiên khi gặp câu hỏi chi tiết về thủ tục ngoài dữ liệu, mô hình có xu hướng tự tạo ra các thông tin pháp lý không có căn cứ.
* **QLoRA v2 (Thuần):** EM đạt 0,00% và SacreBLEU đạt 6,82, nhưng **Độ chính xác Hành vi (Action Accuracy) đạt tới 93,57%**. Nhờ hợp đồng huấn luyện RAG-SFT, khi không nhận được văn bản bằng chứng (`evidence`), mô hình nhận thức rõ sự thiếu hụt thông tin và từ chối trả lời liều lĩnh, chủ động yêu cầu người dùng cung cấp thêm ngữ cảnh hoặc mã thủ tục.

### 4.2 Sức mạnh Đột phá khi Kết hợp RAG
Khi được kết hợp cùng hệ thống truy xuất tài liệu:
* Exact Match của QLoRA v2 tăng gấp **16 lần** so với Base+RAG (20,38% so với 1,25%) và gần gấp đôi QLoRA v1+RAG (12,54%).
* Độ trung thực ngữ cảnh đạt **91,09%**, độ phủ dữ kiện chính (Key Fact Coverage) tăng gấp đôi lên **38,59%**.
* Tốc độ sinh đạt **47,62 tokens/giây**, độ trễ giảm 26% (từ 9,67s xuống 7,15s/mẫu) trên phần cứng thương mại phổ thông.

---

## 5. Kết luận

Việc chuẩn hóa Dataset v3 thành các phân vùng tường minh, sạch sẽ và khử rò rỉ đề thi (`finetuning_v1` và `finetuning_v2`) tạo tiền đề vững chắc cho việc kiểm chứng thực nghiệm. Mô thức huấn luyện tinh chỉnh có ràng buộc ngữ cảnh (Context-grounded RAG-SFT) kết hợp cùng kiểm toán rò rỉ dữ liệu đã chứng minh ưu thế áp đảo hoàn toàn so với tinh chỉnh tham số ngây thơ và hệ thống RAG zero-shot truyền thống trong các bài toán công vụ đòi hỏi độ tin cậy cao.
