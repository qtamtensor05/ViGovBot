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

Toàn bộ thông số huấn luyện được trích xuất từ [config.yaml](file:///c:/Users/quangTam/Documents/ViGovBot/outputs/qlora/qlora-full-20261014-153839-desktop-7pkpjrj-ea78be2d/config.yaml) và [parameter_report.json](file:///c:/Users/quangTam/Documents/ViGovBot/outputs/qlora/qlora-full-20261014-153839-desktop-7pkpjrj-ea78be2d/parameter_report.json):

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

## 6. Lưu Ý Về Kết Quả Đánh Giá Tập Test & Các Bước Tiếp Theo

> [!IMPORTANT]
> **Tình trạng kết quả kiểm thử trên tập Test (`test_sft.jsonl` / `test_queries.jsonl`)**:
> - **Hiện tại**: Chưa chạy bước Generation Evaluation trên tập 1.000 câu hỏi test độc lập. Điều này là có chủ đích theo thiết kế pipeline nhằm tách biệt giai đoạn Huấn luyện (Training/Fitting) với giai đoạn Đánh giá Độc lập (Inference Benchmarking).
> - **Sẽ bổ sung**: Kết quả kiểm thử sẽ được đo đạc và cập nhật bổ sung theo quy trình chuẩn của `qa_v4` để đảm bảo tính công bằng và có thể so sánh chéo trực tiếp (paired comparison).

### Kế hoạch triển khai tiếp theo:
1. **Chạy suy luận đánh giá trên 1.000 ca test độc lập (`Data/tthc_test_case_v1/data/rag/test_queries.jsonl`)**:
   - Sử dụng lệnh benchmark adapter tích hợp:
     ```powershell
     python -m vigovbot.qa_v4 run --config configs/rag-fast-local.yaml --adapter outputs/qlora/qlora-full-20261014-153839-desktop-7pkpjrj-ea78be2d/best_adapter --concurrency 2 --out outputs/qlora/predictions_test.jsonl
     ```
2. **Chấm điểm toàn diện các chỉ số**:
   - Đo lường: `BLEU`, `ROUGE-1/2/L`, `BERTScore` ($F_1$), và `Action Accuracy` (độ chính xác chọn hành động: answer / partial / abstain / correct_premise / clarify).
3. **Báo cáo so sánh 3 chiều (Three-Way Comparison)**:
   - Lập bảng so sánh trực diện: **Qwen2.5-7B Base** vs **Qwen2.5-7B + RAG** vs **Qwen2.5-7B + QLoRA (Fine-tuned)**.

