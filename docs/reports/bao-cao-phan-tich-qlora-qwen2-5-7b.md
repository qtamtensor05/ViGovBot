# Báo Cáo Phân Tích Triển Khai QLoRA Cho Mô Hình Qwen2.5-7B-Instruct

*Ngày thực hiện báo cáo: 14/10/2026 (Asia/Saigon)*  
*Mã thực nghiệm: `qlora-full-20261014-153839-desktop-7pkpjrj-ea78be2d`*  
*Mục tiêu: Tinh chỉnh cục bộ mô hình nền Qwen2.5-7B-Instruct thích nghi với tác vụ hỏi đáp Thủ tục hành chính (TTHC) tiếng Việt qua kỹ thuật QLoRA (Quantized Low-Rank Adaptation) trên phần cứng đơn GPU RTX 5060 Ti.*

---

## 1. Tổng quan & Mục tiêu Triển khai

Dự án ViGovBot trước đây sử dụng mô hình gốc **Qwen2.5-7B-Instruct** kết hợp cơ chế RAG (Retrieval-Augmented Generation). Nhằm nâng cao khả năng bám sát ngữ cảnh pháp lý TTHC, hạn chế ảo giác, hiểu đúng mẫu câu hỏi hành chính và định dạng câu trả lời chuẩn xác mà không đòi hỏi chi phí phần cứng khổng lồ, kỹ thuật **QLoRA (Dettmers et al.)** đã được chọn để thực hiện tinh chỉnh có giám sát (Supervised Fine-Tuning - SFT).

### Điểm nổi bật về mặt kỹ thuật:
- **Lượng tử hóa 4-bit (NF4)** với cơ chế **Double Quantization** và **bfloat16 compute dtype**: Nén toàn bộ trọng số gốc 7B parameters từ ~15 GB VRAM xuống còn dưới ~5.5 GB VRAM, mở ra không gian cho gradient, optimizer states và context sequence length dài.
- **LoRA trên toàn bộ Linear Projection Modules (All Linear Layers)**: Không chỉ can thiệp vào tầng Attention (`q_proj`, `v_proj`), mô hình gắn adapter vào cả các tầng MLP Feed-Forward (`gate_proj`, `up_proj`, `down_proj`).
- **Tối ưu bộ nhớ với Paged AdamW 8-bit & Gradient Checkpointing**: Hạn chế tràn VRAM (OOM) khi xử lý chuỗi độ dài đến 2.048 tokens trên GPU tiêu dùng 16GB.

---

## 2. Cấu hình Tham số & Kiến trúc Triển khai

Toàn bộ thông số huấn luyện được trích xuất từ [config.yaml](../../outputs/qlora/qlora-full-20261014-153839-desktop-7pkpjrj-ea78be2d/config.yaml) và [parameter_report.json](../../outputs/qlora/qlora-full-20261014-153839-desktop-7pkpjrj-ea78be2d/parameter_report.json):

### 2.1. Cấu hình Mô hình Nền & Lượng tử hóa
- **Base Model**: `Qwen/Qwen2.5-7B-Instruct`
- **Max Sequence Length**: `2.048` tokens
- **Quantization Type**: `4-bit NormalFloat (NF4)`
- **Double Quantization**: `True` (nén thêm quantization constants, tiết kiệm ~0.37 bit/param)
- **Compute Dtype**: `bfloat16` (tận dụng phần cứng Tensor Cores của GPU NVIDIA thế hệ mới)

### 2.2. Cấu hình LoRA Adapter (PEFT)
- **Rank ($r$)**: `16`
- **Scaling Factor ($\alpha$)**: `32` (tỉ lệ scaling $\alpha/r = 2.0$)
- **LoRA Dropout**: `0.05`
- **Bias**: `none`
- **Target Modules**: Gồm toàn bộ 7 khối biến đổi tuyến tính trong 28 Decoder Layers của Qwen:
  - Attention projections: `q_proj`, `k_proj`, `v_proj`, `o_proj`
  - MLP projections: `gate_proj`, `up_proj`, `down_proj`

### 2.3. Thống kê Tham số Huấn luyện
- **Tổng tham số mô hình gốc (Base Model Parameters)**: `4.352.972.288`
- **Số tham số huấn luyện LoRA (Trainable Parameters)**: `40.370.176` (khoảng 40.37 triệu)
- **Số tham số bị đóng băng (Frozen Parameters)**: `4.352.972.288`
- **Tỉ lệ tham số huấn luyện (% Trainable)**: **`0,919%`**
- **Mức giảm thiểu tham số so với Full Fine-Tuning**: **`99,08%`**

### 2.4. Siêu tham số Huấn luyện (Hyperparameters)
- **Tối ưu hóa (Optimizer)**: `paged_adamw_8bit`
- **Tốc độ học (Learning Rate)**: $2 \times 10^{-4}$ (`0.0002`)
- **Bộ điều chỉnh tốc độ học (LR Scheduler)**: `cosine` với `warmup_ratio = 0.03` (làm nóng trong 56 steps đầu tiên)
- **Batch Size thực tế (Effective Batch Size)**:
  - `per_device_train_batch_size`: 1
  - `gradient_accumulation_steps`: 8
  - $\rightarrow$ **Effective Batch Size**: **8 mẫu/bước cập nhật gradient**
- **Weight Decay**: `0.01`
- **Max Gradient Norm (Clip)**: `1.0`
- **Gradient Checkpointing**: `True`
- **Kế hoạch dừng sớm (Early Stopping)**:
  - `Patience`: 2 lần đánh giá liên tiếp không cải thiện
  - `Threshold`: 0.001
  - `Metric`: `eval_loss` (thấp hơn là tốt hơn)
- **Tần suất đánh giá & lưu checkpoint**: Mỗi `100 steps` (tương đương 800 mẫu)

### 2.5. Môi trường Thực thi (Hardware & Environment)
- **GPU**: 1x NVIDIA GeForce RTX 5060 Ti (VRAM: 16 GB vật lý, ~15.9 GB khả dụng)
- **Hệ điều hành**: Windows 11 (64-bit)
- **Nền tảng phần mềm**: Python 3.11.9, PyTorch `2.9.1+cu130`, Transformers `4.57.3`, PEFT `0.18.0`, Bitsandbytes `0.49.0`, Accelerate `1.12.0`

### 2.6. Bộ Dữ liệu Huấn luyện SFT
Dữ liệu chuẩn bị tại `Data/tthc_test_case_v1/data/fintuning/`:
- **Train split**: 3.000 mẫu hội thoại (định dạng ChatML SFT, nhãn loss chỉ tính trên lượt trả lời của Assistant)
- **Validation split**: 1.000 mẫu độc lập
- **Test split**: 1.000 mẫu độc lập (dành cho kiểm thử sau huấn luyện)

---

## 3. Phân Tích Kết Quả Huấn Luyện (Training & Validation Dynamics)

Quá trình huấn luyện diễn ra tự động và kích hoạt cơ chế **Early Stopping** tại **Step 1.300 / 1.875** (đạt Epoch 3.47), kéo dài trong **3 giờ 41 phút 50 giây** (13.310 giây thời gian tính toán của Trainer; tổng wall-clock bao gồm export/plot là ~4 giờ 01 phút).

### 3.1. Bảng Diễn biến Loss qua các Mốc Đánh giá (Mỗi 100 steps)

| Global Step | Epoch | Training Loss | Validation Loss | Learning Rate | Trạng thái Checkpoint |
|:---:|:---:|:---:|:---:|:---:|:---|
| **100** | 0.27 | 0.5736 | 0.4077 | $1.997 \times 10^{-4}$ | Checkpoint 100 |
| **200** | 0.53 | 0.6565 | 0.3622 | $1.970 \times 10^{-4}$ | Checkpoint 200 (Cải thiện) |
| **300** | 0.80 | 0.5782 | 0.3399 | $1.914 \times 10^{-4}$ | Checkpoint 300 (Cải thiện) |
| **400** | 1.07 | 0.4541 | 0.3197 | $1.830 \times 10^{-4}$ | Checkpoint 400 (Cải thiện) |
| **500** | 1.33 | 0.5405 | 0.2972 | $1.722 \times 10^{-4}$ | Checkpoint 500 (Cải thiện) |
| **600** | 1.60 | 0.4467 | 0.2902 | $1.593 \times 10^{-4}$ | Checkpoint 600 (Cải thiện) |
| **700** | 1.87 | 0.4601 | 0.2702 | $1.445 \times 10^{-4}$ | Checkpoint 700 (Cải thiện) |
| **800** | 2.13 | 0.2794 | 0.2732 | $1.285 \times 10^{-4}$ | Tăng nhẹ (+0.0030) |
| **900** | 2.40 | 0.3113 | 0.2597 | $1.116 \times 10^{-4}$ | Checkpoint 900 (Tiếp tục giảm) |
| **1000** | 2.67 | 0.3151 | 0.2517 | $9.430 \times 10^{-5}$ | Checkpoint 1000 (Cải thiện) |
| **1100** | **2.93** | **0.3379** | **0.2465** | **$7.722 \times 10^{-5}$** | ⭐ **Best Checkpoint (Val Loss tối ưu)** |
| **1200** | 3.20 | 0.1347 | 0.2585 | $6.082 \times 10^{-5}$ | Chững lại, tăng lên (+0.0120) |
| **1300** | 3.47 | 0.1604 | 0.2541 | $4.558 \times 10^{-5}$ | Không cải thiện $\rightarrow$ **Kích hoạt Early Stopping** |

---

### 3.2. Phân Tích Đường Cong Hội Tụ & Khả Năng Khái Quát Hóa (Generalization)

1. **Giai đoạn đầu (Step 0 – 400)**:
   - Training loss ban đầu giảm dốc đứng từ **`2.1170`** (step 10) xuống dưới **`0.58`** ở step 100.
   - Validation loss giảm mạnh từ **`0.4077`** xuống **`0.3197`**. Điều này chứng minh LoRA adapter nhanh chóng học được cấu trúc cú pháp của tập dữ liệu TTHC và phong cách phản hồi chuẩn.

2. **Giai đoạn ổn định (Step 400 – 1100)**:
   - Quá trình học ổn định dần theo hàm Cosine Decay.
   - Validation loss giảm liên tục và đạt điểm cực tiểu toàn cục: **`0.24649`** tại **Step 1.100 (Epoch 2.93)**.
   - Độ phức tạp ngữ nghĩa trên tập validation (Validation Perplexity): đạt **`1.2795`** (rất thấp, thể hiện khả năng dự đoán từ ngữ chính xác cao).

3. **Hiện tượng Overfitting nhẹ & Quyết định Dừng Sớm**:
   - Sau step 1.100, trong khi Training loss tiếp tục giảm sâu xuống **`0.1015`** ở step 1.210, thì Validation loss bắt đầu chững lại và tăng ngược lên **`0.2585`** (step 1200) và **`0.2541`** (step 1300).
   - Khoảng cách tổng quát hóa (Generalization Gap = $Val\_Loss - Train\_Loss$) tại thời điểm kết thúc là **`0.1450`**.
   - Cơ chế Early Stopping (`patience=2`) đã hoạt động chính xác theo thiết kế, ngắt huấn luyện kịp thời để tránh mô hình học vẹt (overfit) dữ liệu train.
   - Hệ thống đã tự động phục hồi và lưu lại đúng trọng số của **`checkpoint-1100`** thành `best_adapter`.

---

## 4. Hiệu Năng & Tài Nguyên Thực Thi

- **Bộ nhớ VRAM đỉnh (Peak GPU Memory)**:
  - **Allocated Memory**: **`12.86 GB`** (~80.3% dung lượng VRAM 16GB)
  - **Reserved Memory**: **`16.93 GB`** (tận dụng tối đa bộ nhớ đệm của GPU mà không gây ra lỗi Out-of-Memory)
- **Tốc độ xử lý (Throughput)**:
  - Tốc độ huấn luyện trung bình: **`1.127 samples/second`** (~0.141 steps/second).
  - Thời gian trung bình cho mỗi bước cập nhật optimizer: **`10.24 giây / step`** (tương đương ~1.28s cho mỗi batch size 1).
  - Tốc độ xử lý token: **~`218 tokens/giây`**.
  - Tổng số input tokens mô hình đã duyệt qua: **`2.838.247 tokens`**.
- **Tính ổn định của Gradient**:
  - Gradient norm dao động ổn định trong khoảng `0.40` – `1.39`, không xảy ra hiện tượng bùng nổ gradient (gradient explosion) hay tiêu biến gradient (vanishing gradient).

---

## 5. Artifacts & Sản Phẩm Đạt Được

Thư mục lưu trữ: `outputs/qlora/qlora-full-20261014-153839-desktop-7pkpjrj-ea78be2d/`

1. **Bộ Trọng Số Tinh Chỉnh (Best Adapter)**:
   - Thư mục `best_adapter/` chứa `adapter_model.safetensors` (~161 MB), `adapter_config.json`, tokenizer và chat template Jinja.
   - Đã được đồng bộ hoàn toàn với checkpoint tốt nhất tại step 1.100.
2. **Các Checkpoints Trung Gian**:
   - Lưu 3 checkpoints gần nhất (`checkpoint-1100`, `checkpoint-1200`, `checkpoint-1300`) theo chính sách `save_total_limit: 3`.
3. **Biểu đồ Trực Quan Hóa Đã Xuất (`plots/`)**:
   - `training_loss.png`, `validation_loss.png`, `combined_loss.png`: Trực quan hóa diễn biến loss.
   - `learning_rate.png`: Đường cong điều chỉnh learning rate cosine.
   - `gradient_norm.png`: Biểu đồ kiểm soát gradient norm.
   - `parameter_proportions.png`: Tỉ lệ tham số huấn luyện 0.919% so với mô hình gốc.
   - `time_per_epoch.png`, `duration_breakdown.png`: Thống kê thời gian từng epoch.
4. **Nhật Ký Máy Đọc**:
   - `training_metrics.json`: Tổng hợp toàn bộ metric cuối cùng.
   - `training_log.csv`: Bảng số liệu chi tiết từng 10 steps.
   - `parameter_report.json`, `timing_report.json`, `environment.json`.

---

## 6. Kết Quả Đánh Giá Trên Tập Test Độc Lập (Test Set Benchmark)

*Cập nhật ngày 15/10/2026: Đã hoàn tất suy luận và chấm điểm toàn diện cho **1.000 ca kiểm thử** trên tập test chuẩn hóa `tthc_test_case_v1`.*  
*Artifact kết quả:*
- **Dự đoán**: [predictions_qwen_qlora_batch4.jsonl](../../outputs/tthc_test_case_v1/tthc_test_case_v1/predictions_qwen_qlora_batch4.jsonl) ([run report](../../outputs/tthc_test_case_v1/tthc_test_case_v1/predictions_qwen_qlora_batch4.jsonl.run.json))
- **Điểm số**: [scores_qwen_qlora_batch4.json](../../outputs/tthc_test_case_v1/scores_qwen_qlora_batch4.json)

### 6.1. Thiết Lập & Quy Trình Đánh Giá
- **Dữ liệu kiểm thử**: 1.000 ca thuộc `Data/tthc_test_case_v1/data/rag/test_queries.jsonl`, đối chiếu với nhãn chuẩn `Data/tthc_test_case_v1/data/test.jsonl`.
- **Cơ chế suy luận**: Mô hình chạy dạng **Zero-Retrieval** (không cấp tài liệu qua RAG, dựa thuần túy vào tri thức được học trong bộ trọng số LoRA sau SFT).
- **Batching & Concurrency**: Batch size = 4, concurrency = 1.
- **Tập con chấm tương đồng văn bản (Similarity evaluation)**: Áp dụng trên **810 ca có nội dung** (600 ca `answer`, 140 ca `partial`, 70 ca `correct_premise`). Các nhóm `abstain` (130 ca) và `clarify` (60 ca) được loại khỏi mẫu số tương đồng văn bản do không có câu trả lời tri thức tương ứng, đúng chuẩn quy ước đánh giá của benchmark.

---

### 6.2. Bảng So Sánh 3 Chiều: Qwen2.5-7B Base vs ViGovBot RAG vs QLoRA (Fine-Tuned)

Dưới đây là bảng đối sánh tổng hợp giữa **Mô hình gốc (Base)**, **Hệ thống RAG** và **Mô hình sau tinh chỉnh QLoRA**:

| Nhóm Chỉ Số | Thước Đo Đánh Giá | Qwen2.5-7B Base | ViGovBot RAG | Qwen2.5-7B + QLoRA | Tương Quan So Với RAG | Tương Quan So Với Base |
|---|---|:---:|:---:|:---:|:---:|:---:|
| **Độ khớp chính xác** | **Exact Match (EM)** | 0% | 0% | **26,30%** (213 / 810) | $\mathbf{+26,30\%}$ | $\mathbf{+26,30\%}$ |
| **Tương đồng văn bản** | **Corpus BLEU-4** | 8,27 | 23,91 | **33,23** | $\mathbf{+9,32}$ | $\mathbf{+24,96}$ |
| | **Sentence BLEU (mean)** | 15,41 | 31,15 | **61,38** | $\mathbf{+30,23}$ | $\mathbf{+45,97}$ |
| | **ROUGE-1 F1** | 0,3329 | 0,5173 | **0,7577** | $\mathbf{+0,2404}$ | $\mathbf{+0,4248}$ |
| | **ROUGE-2 F1** | 0,2291 | 0,4237 | **0,6870** | $\mathbf{+0,2633}$ | $\mathbf{+0,4579}$ |
| | **ROUGE-L F1** | 0,3188 | 0,5069 | **0,7169** | $\mathbf{+0,2100}$ | $\mathbf{+0,3981}$ |
| | **chrF++** | 33,26 | 50,42 | **72,90** | $\mathbf{+22,48}$ | $\mathbf{+39,64}$ |
| | **TER (thấp hơn là tốt)** | 134,81 | 85,32 | **43,60** | $\mathbf{-41,72}$ | $\mathbf{-91,21}$ |
| **Ngữ nghĩa sâu** | **BERTScore Precision** | 0,8794 | 0,9114 | **0,9529** | $\mathbf{+0,0415}$ | $\mathbf{+0,0735}$ |
| | **BERTScore Recall** | 0,8851 | 0,8985 | **0,9503** | $\mathbf{+0,0518}$ | $\mathbf{+0,0652}$ |
| | **BERTScore F1** | 0,8816 | 0,9041 | **0,9514** | $\mathbf{+0,0473}$ | $\mathbf{+0,0698}$ |
| **Độ tin cậy vận hành** | **Tỷ lệ suy luận thành công** | **100%** (1.000/1.000) | 99,5% (995/1.000) | **100%** (1.000/1.000) | +0,5% (0 lỗi) | Bằng nhau |
| | **Số ca lỗi cấu trúc/JSON** | 0 | 5 | **0** | Triệt tiêu lỗi | Bằng nhau |
| **Thời gian & Tốc độ** | **Tổng thời gian chạy (Wall time)** | ~17,2 phút (c=4) | ~43,0 phút (c=4) | ~201,4 phút (batch=4, c=1) | Chạy tuần tự | Chạy tuần tự |
| | **Độ trễ trung bình / câu** | ~1,03 s | ~2,59 s | **12,08 s** (p50: 11,71 s) | Tải model qua PyTorch | |

---

### 6.3. Phân Tích Chi Tiết Kết Quả Đạt Được Của Mô Hình QLoRA

#### 1. Bước nhảy vọt về chất lượng văn phong và thuật ngữ hành chính
- **Corpus BLEU-4 đạt 33,23** (vượt RAG +9,32 điểm và Base +24,96 điểm). Đặc biệt, **Sentence BLEU trung bình đạt 61,38**, cao gần gấp đôi RAG (31,15) và gấp 4 lần Base (15,41).
- **ROUGE-L F1 đạt 0,7169** (so với 0,5069 của RAG và 0,3188 của Base).
- **BERTScore F1 đạt 0,9514**: Thể hiện sự tương thích ngữ nghĩa gần như tuyệt đối với câu trả lời mẫu của chuyên viên hành chính.
- **Tỉ lệ Exact Match đạt tới 26,30%**: 213/810 câu hỏi có câu trả lời sinh ra **khớp từng từ** với đáp án mẫu. Cả RAG và Base trước đây đều đạt 0% ở chỉ số này do mô hình gốc thường diễn giải dài dòng hoặc dùng từ đồng nghĩa khác biệt.

#### 2. Kết quả theo từng nhóm hành động (Per-Action Breakdown)

| Nhóm hành động | Số lượng ca test | Sentence BLEU | ROUGE-L F1 | BERTScore F1 | Exact Match |
|---|:---:|:---:|:---:|:---:|:---:|
| **answer** (Câu hỏi trực tiếp) | 600 | 57,87 | 0,6934 | 0,9484 | 22,50% (135/600) |
| **partial** (Hỏi 1 phần có đáp án) | 140 | 65,00 | 0,7299 | 0,9490 | 32,86% (46/140) |
| **correct_premise** (Sửa tiền đề sai) | 70 | **84,17** | **0,8924** | **0,9819** | **45,71%** (32/70) |
| **abstain** (Từ chối tra cứu) | 130 | — | — | — | 100% trả lời an toàn |
| **clarify** (Hỏi lại làm rõ) | 60 | — | — | — | 100% hỏi làm rõ đúng thủ tục |

* **Đột phá ở nhóm `correct_premise`**:
  - Sentence BLEU đạt tới **84,17**, ROUGE-L F1 đạt **0,8924**, BERTScore F1 đạt **0,9819**, và Exact Match đạt **45,71%**.
  - Mô hình QLoRA đã học được phản xạ: chỉ ra ngay tiền đề sai của người hỏi và cung cấp cơ quan/thông tin đính chính chuẩn mực (ví dụ: *"Không đúng với tài liệu nguồn. Cơ quan thực hiện là..."*). Đây từng là điểm yếu lớn nhất của RAG và Base (thường bị cuốn theo giả định sai của người hỏi).
* **Nhóm `clarify` và `abstain`**:
  - Với câu hỏi cân nhắc 2 thủ tục, mô hình tự động nhận diện và hỏi lại: *"Bạn muốn hỏi thủ tục nào trong hai thủ tục vừa nêu? Vui lòng xác định tên thủ tục để tôi trả lời đúng."*
  - Với câu hỏi trạng thái hồ sơ cá nhân ngoài phạm vi, mô hình từ chối lịch sự và hướng dẫn tra cứu cổng Dịch vụ công thay vì bịa đặt trạng thái hồ sơ như Base.

---

### 6.4. Đánh Giá Khách Quan: Ưu Điểm & Giới Hạn Của Mô Hình QLoRA

#### Ưu điểm:
1. **Khắc phục triệt để phong cách trả lời**: Không còn tình trạng trả lời lan man, dư thừa thông tin hoặc văn phong dịch thuật thiếu chuẩn xác của mô hình nền 7B gốc.
2. **Khả năng ghi nhớ tri thức TTHC cốt lõi**: Dù không có RAG hỗ trợ khi suy luận, adapter LoRA vẫn lưu giữ chính xác các thực thể thẩm quyền, cơ quan thực hiện và thành phần hồ sơ của các thủ tục phổ biến.
3. **Độ ổn định định dạng tuyệt đối**: 1.000/1.000 ca đều sinh văn bản hoàn chỉnh, không gặp lỗi cắt cụt token hay vỡ cú pháp.

#### Giới hạn & Điểm cần lưu ý:
1. **Thời gian suy luận cục bộ**: Quá trình chạy 1.000 câu trên GPU RTX 5060 Ti qua PyTorch HuggingFace mất ~3,3 giờ (12.082 giây, trung bình ~12 giây/câu) do chạy tuần tự chưa tối ưu vLLM/Ollama adapter serving.
2. **Tri thức đóng băng tại thời điểm SFT**: QLoRA giải quyết rất tốt phong cách và mẫu thủ tục đã học, nhưng nếu văn bản pháp luật thay đổi hoặc có thủ tục hoàn toàn mới chưa từng xuất hiện trong tập train, mô hình vẫn cần cơ chế **RAG (Retrieval)** để đọc văn bản cập nhật theo thời gian thực.
3. **Mô hình kết hợp tối ưu (Hybrid Recommendation)**:
   - Hướng đi tối ưu nhất cho ViGovBot là **ghép nối adapter QLoRA này vào chính pipeline RAG**: Dùng RAG để truy hồi tài liệu pháp lý mới nhất, và dùng QLoRA Adapter làm generator để tổng hợp câu trả lời chuẩn xác, ngắn gọn và không ảo giác.


