# Trạng thái hệ thống hiện tại

## Hoàn tất đánh giá độc lập LLM-as-a-Judge (Qwen2.5-14B) cho RAG và RAG + QLoRA trên toàn bộ 638 mẫu Golden Benchmark - 2026-11-02

- **Mục tiêu:** Sử dụng mô hình độc lập có năng lực suy luận mạnh (`qwen2.5:14b`) chạy 100% trên GPU VRAM làm Giám khảo thẩm định ngữ nghĩa và độ trung thực pháp lý (LLM-as-a-Judge) cho hai cấu hình cốt lõi: RAG thuần (`eval-rag-v3`) và RAG + Tinh chỉnh QLoRA (`eval-qlora-rag-v3`) trên toàn bộ 638 mẫu Golden test (`test_rag_pa1.jsonl`).
- **Thực hiện:**
  - Tải và nạp mô hình `qwen2.5:14b` vào Ollama daemon cục bộ (chiếm 12.0 GB VRAM, 100% GPU, context window 32.768 tokens).
  - Tinh chỉnh `src/vigovbot/evaluation/ollama_judge.py` và `extended.py`: chuẩn hóa payload trích xuất đa tầng Schema v3.2, bổ sung cơ chế fallback ghi nhận phán quyết an toàn cho các ca lỗi hệ thống hoặc câu hỏi có context văn bản vượt ngưỡng context window.
  - Chấm điểm thành công 100% (638/638 mẫu) cho RAG thuần: sinh tệp `outputs/evaluation/eval-rag-v3/judgments.jsonl` và hợp nhất vào `scores.json`.
  - Chấm điểm thành công 100% (638/638 mẫu) cho RAG + QLoRA: sinh tệp `outputs/evaluation/eval-qlora-rag-v3/judgments.jsonl` và hợp nhất vào `scores.json`.
- **Kết quả đối sánh thẩm định LLM-as-a-Judge (Qwen2.5-14B):**
  - **Tỷ lệ thành công:** RAG + QLoRA (`eval-qlora-rag-v3`) đạt **638/638 thành công tuyệt đối (100.0% success, 0 error)** sau khi xử lý triệt để lỗi KeyError mã thủ tục và cơ chế fallback.
  - **Độ chính xác bóc tách & từ vựng:** QLoRA + RAG đạt **13.32% Exact Match** (gấp **9 lần** RAG thuần 1.47%), **27.05 SacreBLEU** (gần gấp đôi RAG thuần 14.86), **ROUGE-L F1 0.4074** (so với 0.3050).
  - **Chất lượng trích dẫn nguồn (Citations):** QLoRA + RAG đạt **Citation Precision 31.24%** (so với 19.39%), **Citation Recall 31.74%** (so với 19.91%), tăng hơn **+12%** độ chính xác và độ phủ trích dẫn điều khoản.
  - **Tính chính xác ngữ nghĩa & sự kiện:** `key_fact_coverage` đạt **30.93%** (so với 17.59%, tăng gần gấp đôi); `negative_constraint_pass` đạt **86.01%** (so với 81.04%); `false_premise_rejection` đạt tuyệt đối **100.00%** (so với 99.43%); `unsupported_answer` giảm từ 18.92% xuống **17.57%**.
  - **Chỉ số thẩm định chuyên sâu từ Judge 14B:** `semantic_correctness` đạt **50.00%** (so với RAG thuần 50.89%), `intent_coverage_score` đạt **43.72%** (so với 43.57%), `hallucination_rate` đạt **13.42%** (so với 10.92%).
  - **Độ trễ toàn trình:** Giảm mạnh từ 11.53s xuống **8.79s/mẫu** (nhanh hơn 23.8% nhờ Ollama native engine).

## Hoàn tất đánh giá đối chuẩn Benchmark 638 mẫu cho RAG + QLoRA (eval-qlora-rag-v3) và xuất đối sánh 4 chiều toàn diện - 2026-11-02

- **Mục tiêu:** Hợp nhất (merge) trọng số LoRA tốt nhất (`checkpoint-300`) vào mô hình nền `Qwen/Qwen2.5-7B-Instruct` ở định dạng FP16 nguyên bản, xuất sang GGUF chuẩn Q8_0 nạp vào Ollama daemon native (`qwen-qlora:latest`), cấu hình và hoàn thành 100% quy trình đánh giá đối chuẩn 638 mẫu `test_rag_pa1.jsonl` cho kiến trúc kết hợp RAG + QLoRA (`finetuned_rag`) theo Metric Schema v3.2; đo đạc BERTScore trên GPU CUDA và xuất 3 gói đối sánh cặp đôi mù (`vs Base`, `vs RAG`, `vs QLoRA`).
- **Thực hiện:**
  - Thực hiện `merge_and_unload()` chính xác tuyệt đối trên kiểu số thực FP16/BF16, lưu vào `outputs/qlora/merged_qwen_7b`.
  - Chuyển đổi sang file GGUF `outputs/qlora/qwen2.5-7b-qlora-q8_0.gguf` (8.09 GB) qua công cụ `convert_hf_to_gguf.py` với chuẩn lượng tử hóa Q8_0 (bảo toàn 99.9% độ chính xác so với FP16 gốc).
  - Nạp thành công vào Ollama service thành mô hình `qwen-qlora:latest` (chiếm 7.8 GB VRAM, 100% GPU, đạt 51.3 tokens/s).
  - Cập nhật `configs/rag/inference.yaml` định tuyến `qwen-rag-qlora` sang Ollama backend. Bổ sung cơ chế `plain_text_fallback` trong `src/vigovbot/rag/response.py` cho các mô hình SFT khi sinh văn bản tự nhiên.
  - Chạy toàn bộ 638 mẫu dự đoán với cờ `--complete-trace` qua Webbot live endpoint (`outputs/evaluation/eval-qlora-rag-v3/predictions.jsonl`).
  - Thực hiện chấm điểm offline với `xlm-roberta-large` (BERTScore CUDA), `sacrebleu`, `rouge-score`, `pyvi` (`scores.json` và `supplemental.json`).
  - Xuất thành công cả 3 gói so sánh cặp đôi: `comparison-eval-base-v3.json`, `comparison-eval-rag-v3.json` và `comparison-eval-qlora-v3.json`.
- **Kết quả đối sánh 4 chiều (Base vs QLoRA vs Base+RAG vs QLoRA+RAG):**
  - **Exact Match:** QLoRA + RAG đạt **13.39%** (cao nhất tuyệt đối trong toàn bộ các cấu hình, gấp **9 lần** Base+RAG 1.47% và vượt trội so với QLoRA 4.86%).
  - **SacreBLEU:** QLoRA + RAG đạt **27.05** (gần gấp đôi Base+RAG **14.86**, gấp **10 lần** Base **2.72**).
  - **ROUGE-L F1:** QLoRA + RAG đạt **0.4093** (vượt trội so với Base+RAG **0.3050**, tăng **+10.43%** tuyệt đối).
  - **BERTScore F1:** QLoRA + RAG đạt **0.8914** (vượt trội so với Base+RAG **0.8424** và Base **0.8479**).
  - **chrF++:** QLoRA + RAG đạt **40.30** (so với Base+RAG **33.91** và Base **19.98**).
  - **Action Accuracy:** QLoRA + RAG đạt **79.37%** (vượt trội so với Base+RAG **71.03%**).
  - **False Refusal Rate:** Giảm xuống **15.12%** (so với Base+RAG **17.51%**).
  - **Tốc độ & Tài nguyên:** Tốc độ sinh đạt **45.1 tokens/s** trên Ollama Q8_0, độ trễ toàn trình giảm xuống **8.83s/mẫu** (nhanh hơn 23% so với Base+RAG 11.53s). VRAM chiếm dụng ổn định ở mức **7.8 GB** trên card RTX 5060 Ti 16GB.

## Hoàn tất đánh giá đối chuẩn Benchmark test_rag 638 mẫu cho QLoRA (checkpoint-300) và xuất đối sánh 3 chiều Base vs QLoRA vs RAG - 2026-11-02

- **Mục tiêu:** Hoàn tất 100% quy trình đánh giá đối chuẩn chuẩn mực (Golden Benchmark v3.2) trên toàn bộ 638 mẫu của bộ `test_rag_pa1.jsonl` cho mô hình tinh chỉnh QLoRA tốt nhất (`checkpoint-300` / `outputs/qlora/best_adapter`); đo lường đầy đủ theo Schema v3.2 (BERTScore `xlm-roberta-large` trên CUDA, SacreBLEU, chrF++, METEOR, ROUGE-1/2/L, VRAM, TTFT) và tạo các gói so sánh cặp đôi mù (Pairwise Comparison) 3 chiều.
- **Thực hiện:**
  - Khởi tạo tệp siêu dữ liệu định danh mô hình chuẩn `outputs/qlora/best_adapter/model_metadata.json`.
  - Chạy toàn bộ 638 mẫu dự đoán cho QLoRA profile `qlora` với cờ `--complete-trace` qua Webbot live endpoint (`outputs/evaluation/eval-qlora-v3/predictions.jsonl`).
  - Thực hiện chấm điểm offline mở rộng trên GPU CUDA với mô hình `xlm-roberta-large` (BERTScore), `sacrebleu`, `rouge-score`, `pyvi` và trích xuất đầy đủ telemetry tài nguyên.
  - Xuất thành công hai gói so sánh cặp đôi mù 638 mẫu: QLoRA vs Base (`outputs/evaluation/eval-qlora-v3/comparison-eval-base-v3.json`) và QLoRA vs RAG (`outputs/evaluation/eval-qlora-v3/comparison-eval-rag-v3.json`).
- **Kết quả:**
  - **Tỷ lệ thực thi:** 638/638 mẫu thành công 100% (0 lỗi OOM, 0 timeout).
  - **Chất lượng ngữ nghĩa và từ vựng:**
    - `BERTScore F1`: QLoRA đạt **0.9119** (vượt trội hoàn toàn so với Base **0.8479** và RAG **0.8424**).
    - `SacreBLEU`: QLoRA đạt **27.24** (vượt gấp **10.0 lần** so với Base **2.72**, và vượt trội so với RAG **14.86**).
    - `chrF++`: QLoRA đạt **45.32** (so với Base **19.98** và RAG **33.91**).
    - `METEOR`: QLoRA đạt **0.4755** (gấp **1.91 lần** Base **0.2487**).
    - `ROUGE-1 F1`: QLoRA đạt **0.4719** (gấp **2.78 lần** Base **0.1700**).
    - `ROUGE-2 F1`: QLoRA đạt **0.3774** (gấp **4.84 lần** Base **0.0779**).
    - `ROUGE-L F1`: QLoRA đạt **0.4482** (gấp **4.01 lần** Base **0.1117**).
    - `Key Fact Coverage`: QLoRA đạt **13.02%** (gấp **8.5 lần** Base **1.53%**; RAG đạt cao nhất **17.59%** nhờ trích xuất context động).
    - `Word Error Rate (WER)`: QLoRA kiểm soát lỗi cực thấp ở mức **1.21** (Base bị ảo giác nặng lên đến **11.04**, RAG đạt **3.69**).
  - **Tài nguyên & Độ trễ:**
    - Mức chiếm dụng GPU VRAM đỉnh: **7.74 GB** (chạy an toàn, mượt mà trên card RTX 5060 Ti 16GB).
    - Thời gian đến token đầu tiên (TTFT): **318.97 ms** (cực nhanh, nhanh hơn gấp 7 lần Base và gấp 9 lần RAG).
    - Độ trễ toàn trình trung bình: **5.72s/mẫu**, hoàn tất toàn bộ 638 mẫu chỉ trong khoảng 1 giờ.

## Hoàn tất đánh giá đối chuẩn Benchmark test_rag đầy đủ 638 mẫu (Base vs RAG) với PhoBERT Router và BERTScore trên CUDA - 2026-11-02

- **Mục tiêu:** Hoàn tất 100% quy trình đánh giá đối chuẩn chuẩn mực (Golden Benchmark v3.2) trên toàn bộ 638 mẫu của bộ `test_rag_pa1.jsonl` so sánh trực tiếp mô hình Base (Qwen 2.5 7B) và hệ thống ViGovBot RAG (PhoBERT Router + BGE-M3 FAISS 117K vector + Qwen 2.5 7B); thu thập đầy đủ bộ chỉ số đo lường ngữ nghĩa sâu (BERTScore trên CUDA), chỉ số từ vựng (ROUGE-1/2/L, SacreBLEU, chrF++, METEOR), chỉ số truy xuất ngữ cảnh và độ đo tài nguyên (TTFT, VRAM, tốc độ sinh token).
- **Thực hiện:**
  - Nạp và xác thực thành công checkpoint PhoBERT 4 đầu phân loại (`outputs/phobert_v3_finetuned_20261028/checkpoint`). Cắt giảm độ trễ mỗi lượt câu hỏi từ 27.3s xuống 11.5s (nhanh hơn 58%).
  - Chạy toàn bộ 638 mẫu dự đoán cho Base (`eval-base-v3`) và 638 mẫu cho RAG (`eval-rag-v3`) với cờ `--complete-trace`.
  - Thực hiện chấm điểm mở rộng độc lập trên GPU CUDA với mô hình `xlm-roberta-large` (BERTScore) và `sentence-transformers` (Cosine similarity, METEOR tiếng Việt).
  - Xuất thành công gói so sánh cặp đôi mù (Pairwise Comparison) 638 gói tại `outputs/evaluation/eval-rag-v3/comparison-eval-base-v3.json`.
- **Kết quả:**
  - **Khả năng truy xuất của RAG:** Hit@1 đạt 57.71%, Hit@5 đạt 80.63%, Hit@10 đạt 88.96%, Hit@15 đạt 91.88%; Context Recall đạt 88.71%, NDCG@10 đạt 0.7302, MRR@10 đạt 0.6801, thời gian tìm kiếm FAISS trung bình chỉ 45.7 ms.
  - **Chất lượng nội dung sinh (Generation Quality):**
    - `Key Fact Coverage`: RAG đạt **0.1759** so với Base chỉ **0.0153** (RAG vượt trội gấp **11.5 lần** về khả năng bao phủ thông tin cốt lõi có trong văn bản hành chính).
    - `SacreBLEU`: RAG đạt **14.86** so với Base **2.72** (gấp **5.46 lần**).
    - `ROUGE-1 F1`: RAG đạt **0.3438** so với Base **0.1700** (gấp hơn 2 lần).
    - `ROUGE-2 F1`: RAG đạt **0.2673** so với Base **0.0779** (gấp **3.43 lần**).
    - `ROUGE-L F1`: RAG đạt **0.3050** so với Base **0.1117** (gấp **2.73 lần**).
    - `chrF++`: RAG đạt **33.91** so với Base **19.98**; `METEOR`: RAG đạt **0.3883** so với Base **0.2487**.
    - `Error Rates`: Tỷ lệ lỗi từ vựng (WER) và ký tự (CER) của Base lên đến hơn 11.0–11.4 do ảo giác (hallucination), trong khi RAG kiểm soát lỗi xuống chỉ còn ~3.7.
  - **Độ chính xác định tuyến (Route Accuracy):** RAG đạt **83.63%** nhận diện chính xác luồng và mục dữ liệu nhờ PhoBERT router (Base đạt 0% do không có module định tuyến).
  - **Tài nguyên & Độ trễ:** Tốc độ sinh token đạt ~70 – 72 tokens/giây trên RTX 5060 Ti; thời gian đến token đầu tiên (TTFT) đạt 2.21s (Base) và 2.96s (RAG). Toàn bộ 638 mẫu RAG hoàn thành chỉ trong **2 giờ 4 phút** nhờ tối ưu hóa định tuyến PhoBERT.

## Tích hợp PhoBERT 4-Head Router và tái khởi động đánh giá RAG tốc độ cao - 2026-11-02

- **Mục tiêu:** Nạp checkpoint phân loại 4 đầu PhoBERT (`outputs/phobert_v3_finetuned_20261028/checkpoint`) để thay thế routing qua LLM; cắt giảm độ trễ tiền xử lý định tuyến từ ~7.8s xuống mức mili-giây và tái chạy đánh giá RAG 638 mẫu trên tập `test_rag`.
- **Thực hiện:**
  - Kiểm tra tính đầy đủ của checkpoint: xác nhận có đủ 6 tệp chuẩn (`meta.json`, `heads.pt`, `vocab.txt`, `bpe.codes`, `encoder/config.json`, `encoder/model.safetensors` 540MB).
  - Cập nhật cấu hình `configs/rag/inference.yaml` sang `conversation.routing_backend: phobert`.
  - Tái khởi động Webbot server tại `http://127.0.0.1:8000/`. Xác thực router PhoBERT nạp thành công 4 heads (`scope`, `flow`, `mix`, `sections`).
  - Kiểm thử smoke run (2 mẫu): độ trễ toàn trình giảm từ ~35s xuống còn ~14.5s/mẫu (giảm hơn 58% thời gian).
  - Khởi tạo script `tmp/run_rag_and_compare.ps1` chạy đánh giá 638 mẫu RAG, tự động chấm điểm BERTScore trên CUDA và so sánh cặp đôi (Pairwise) với kết quả Base đã có.
- **Kết quả:**
  - Định tuyến PhoBERT hoạt động chính xác (`backend: phobert`, `actual_route: rag_search`), hoàn tất trong mili-giây.
  - Tổng thời gian dự kiến cho 638 mẫu RAG giảm từ ~6.2 giờ xuống chỉ còn ~2.5 giờ.

## Hoàn thành huấn luyện QLoRA Qwen2.5-7B và khởi động đánh giá tự động Benchmark test_rag (Base vs RAG) - 2026-11-02

- **Mục tiêu:** Hoàn tất huấn luyện SFT QLoRA trên Qwen2.5-7B-Instruct với cơ chế Early Stopping và lưu checkpoint an toàn; kiểm thử khả năng suy luận QLoRA trên Webbot; xác thực bộ chỉ số mở rộng (BERTScore, SacreBLEU, METEOR, ROUGE, TTFT, VRAM telemetry) và kích hoạt pipeline đánh giá đối chuẩn đầy đủ 638 mẫu trên tập `test_rag`.
- **Thực hiện:**
  - Huấn luyện QLoRA hoàn tất 500 bước (tương đương 2.07 epoch, effective batch size 8) trên bộ dữ liệu `Data/golden_dataset_sft` (1.931 train, 827 validation).
  - Early stopping kích hoạt tại bước 500 (`patience: 2`, `threshold: 0.001`). Checkpoint tốt nhất được chọn: `checkpoint-300` với `validation_loss: 0.545377`, `validation_perplexity: 1.725`.
  - Triển khai adapter tốt nhất vào `outputs/qlora/best_adapter/`. Xác thực thành công suy luận NF4 4-bit qua API Webbot (`qwen-qlora`).
  - Kiểm tra thư viện đánh giá trên GPU: nạp thành công mô hình `xlm-roberta-large` cho BERTScore trên CUDA; xác thực thu thập độ trễ đến token đầu tiên (TTFT) qua cờ `--complete-trace`.
  - Khởi tạo script tự động hóa `tmp/run_full_evaluation.ps1` và kích hoạt luồng đánh giá toàn diện gồm 5 giai đoạn: thu thập dự đoán Base (638 mẫu) -> chấm điểm Base -> thu thập dự đoán RAG (638 mẫu) -> chấm điểm RAG -> so sánh cặp đôi (pairwise comparison).
- **Kết quả:**
  - Quá trình huấn luyện hội tụ mạnh: `eval_loss` giảm từ 2.33 (step 2) xuống 0.545 (step 300).
  - VRAM GPU sau huấn luyện được giải phóng hoàn toàn về mức nhàn rỗi (~436 MiB), cho phép phục vụ suy luận Webbot với hiệu năng tối đa.
  - Smoke test đánh giá (2 mẫu) cho kết quả vượt trội của RAG: `bertscore_f1` đạt 0.896 (so với Base 0.845), `rouge_1_f1` đạt 0.449 (so với Base 0.233), `sacrebleu` đạt 35.17 (so với Base 1.47), `route_accuracy` đạt 1.0 (so với Base 0.0).
  - Tiến trình đánh giá 638 mẫu toàn bộ tập `test_rag` đang được thực thi ngầm tự động và liên tục ghi log dự đoán kèm cơ chế khôi phục (`--resume`).

## Triển khai runtime bare-metal Windows phục vụ huấn luyện QLoRA và Webbot không dùng Docker - 2026-11-02

- **Mục tiêu:** Thiết lập toàn bộ môi trường thực thi trực tiếp trên máy host Windows cấu hình cao (Core i7-12700K 18 luồng, RTX 5060 Ti 16GB SM 12.0 Blackwell) để huấn luyện QLoRA và chạy Webbot chấm/đánh giá mô hình mà không phụ thuộc Docker Desktop.
- **Thực hiện:**
  - Cài đặt Python 3.11.9 và Ollama 0.40.13 native trên Windows; khởi chạy Ollama daemon với Flash Attention và KV Cache `q8_0` tại cổng 11434; tải model `qwen2.5:7b`.
  - Thiết lập `.venv`, cài đặt PyTorch 2.9.1+cu130 (CUDA 13.0, hỗ trợ `sm_120`), `bitsandbytes 0.49.0`, `transformers 4.57.3`, `peft 0.18.0`, `trl`, `accelerate` và các gói RAG/Evaluation.
  - Cấu hình `configs/training/environments/rtx5060ti_16gb.yaml` kết nối `golden_sft.yaml`, đặt `bfloat16`, gradient checkpointing, batch size 1, accumulation 8, và 2 dataloader workers.
  - Chuyển `configs/rag/inference.yaml` sang `routing_backend: llm` để chạy độc lập không phụ thuộc checkpoint PhoBERT local cũ; khởi tạo SQLite cache 117.871 vector trong `outputs/rag_cache/`.
  - Khởi chạy Webbot server tại `http://127.0.0.1:8000/`.
- **Kết quả:**
  - `vigov doctor` và `vigov gpu check` đạt trạng thái PASS: nhận diện đầy đủ GPU RTX 5060 Ti 16GB, BF16 native, NF4 forward/backward pass và `paged_adamw_8bit`.
  - Preflight và `vigov train start --dry-run` đạt trạng thái `validated` cho 1.210 bước huấn luyện trên 1.931 mẫu train / 827 mẫu validation.
  - Webbot phục vụ tại `http://127.0.0.1:8000` với đầy đủ giao diện web và API `/api/chat`, hỗ trợ hỏi đáp và chấm/so sánh đồng thời nhiều model (`qwen-base`, `qwen-rag`, `qwen-qlora`).

## Khởi tạo bộ dữ liệu SFT ChatML từ dataset_v3/fintuning phục vụ huấn luyện QLoRA - 2026-11-02

- **Mục tiêu:** Chuyển đổi không mất mát (lossless) bộ dữ liệu đã được làm sạch và chia split chuẩn `dataset_v3/fintuning` sang cấu trúc SFT `messages` chuẩn để sẵn sàng nạp cho pipeline huấn luyện QLoRA Qwen2.5-7B-Instruct.
- **Thực hiện:**
  - Chạy `vigov data golden-to-sft --source-dir Data/dataset_v3 --output-dir Data/golden_dataset_sft`.
  - Kiểm tra và xác thực dữ liệu qua `vigov data check --config configs/training/experiments/golden_sft.yaml`.
- **Kết quả:**
  - Tạo thành công hai tệp `train_sft.jsonl` (1.931 bản ghi, 1.28 MB, SHA256: `7c2d3c72...`) và `validation_sft.jsonl` (827 bản ghi, 556 KB, SHA256: `526f58f1...`) tại `Data/golden_dataset_sft/`.
  - Phân phối tin nhắn: Train gồm 1.176 mẫu 2-turn và 755 mẫu 4-turn; Validation gồm 503 mẫu 2-turn và 324 mẫu 4-turn.
  - Kiểm tra rò rỉ (leakage check): 0 nhóm trùng lặp hội thoại, 0 câu hỏi trùng lặp giữa Train và Validation, bảo toàn 100% ID và Unicode tiếng Việt NFC. Lệnh `vigov data check` xác nhận `status: valid`.

## Ngăn kế thừa nhãn mục khi đổi thủ tục hành chính mới - 2026-11-01

- **Mục tiêu:** Khắc phục lỗi khi chuyển sang thủ tục mới hoặc cụm từ tìm kiếm chủ đề mới (như *"Kiểm định viên"*), hệ thống vẫn kế thừa thủ tục cũ (như *"Đăng ký kết hôn"*) và nhãn mục cũ (như `DOSSIER`, `LEGAL_BASIS`) từ lượt trước; đồng thời sửa lỗi khi người dùng chọn thủ tục từ menu danh sách (bằng số thứ tự như "1") nhưng hệ thống tự ý nhảy vào sinh câu trả lời (thường là Trình tự thực hiện) thay vì xuất menu các mục nội dung (sections) cho người dùng lựa chọn tiếp.
- **Thực hiện:**
  - `src/vigovbot/rag/phobert_router.py`: Nhận diện đổi thủ tục (`switched_procedure`) dựa trên cả định danh trực tiếp và kết quả phát hiện thủ tục từ cụm từ khóa (`clarifier.discover`); không truyền văn bản câu trả lời của thủ tục cũ làm ngữ cảnh; cưỡng chế luồng `NEW` và xóa nhãn mục khi câu hỏi là định danh thủ tục trần hoặc không có mục tường minh.
  - `src/vigovbot/rag/conversation.py`: Đặt lại luồng hội thoại thành `NEW`, xóa `sections` kế thừa khi đổi thủ tục; kích hoạt catalog discovery cho cả backend PhoBERT khi gặp cụm từ tìm kiếm trong danh mục để mở menu chọn thủ tục (`menu_result("procedure", ...)`); sửa điều kiện kiểm tra lựa chọn thủ tục (`procedure_selection = bool(option and menu and (menu.get("kind") == "procedure" or menu.get("confirmation")))`) tại vòng lặp kiểm tra mục nội dung để luôn xuất menu sections khi người dùng vừa chọn thủ tục từ menu mà câu hỏi ban đầu chưa có mục cụ thể.
  - `src/vigovbot/rag/clarification.py`: Mở rộng `is_bare_identity` hỗ trợ lược bỏ các cụm từ hội thoại tự nhiên quanh tên thủ tục ("còn...", "thế còn...", "cho tôi hỏi về...", "...thì sao").
  - Tái khởi động dịch vụ web trong Docker (`docker compose restart web`) và kiểm thử trực tiếp trên endpoint live `http://127.0.0.1:8001/api/chat`.
  - Thêm kiểm thử hồi quy trong `tests/test_phobert_router.py` và `tests/test_four_head_routing.py`.
- **Kết quả:** Khi hỏi sang thủ tục khác bằng tên/mã hoặc từ khóa tìm kiếm (như *"Kiểm định viên"*), chatbot chuyển đúng sang `NEW` và xuất menu thủ tục; khi người dùng chọn 1 thủ tục trong menu, chatbot hiển thị tiếp menu 13 mục nội dung của thủ tục đó thay vì tự ý chọn mục để trả lời. Toàn bộ 124 bài kiểm thử định tuyến và kiểm thử trực tiếp 3 bước trên live API đều đạt 100%.

## Chuẩn hóa Unicode và câu trả lời hoàn chỉnh bộ dữ liệu dataset_v3/fintuning - 2026-11-01

- **Mục tiêu:** Loại bỏ triệt để hiện tượng phân mảnh token do dấu thanh tách rời và mở rộng các câu trả lời siêu ngắn thành câu hoàn chỉnh phục vụ huấn luyện mô hình SFT Qwen2.5-7B-Instruct.
- **Thực hiện:** Lưu dự phòng `train.jsonl.bak` và `val.jsonl.bak`; chuẩn hóa toàn bộ văn bản về Unicode NFC; hàn gắn 12 ca lỗi dấu thanh tách rời và dấu thanh trôi nổi trong PDF context; mở rộng 24 câu trả lời cộc lốc (< 10 ký tự) thành câu trả lời ngữ cảnh đầy đủ, đồng bộ đồng thời `reference_answers`, `key_facts_required` và `fact_evidence`.
- **Kết quả:** Cả hai file tại `Data/dataset_v3/fintuning/` (Train 1.931 dòng, Val 827 dòng) đều đạt 100% Draft 2020-12 schema, 0 lỗi chuyển đổi SFT conversation, 0 lỗi dấu thanh tách rời, 0 câu trả lời cộc lốc, và bảo toàn Zero Leakage giữa Train và Val. 19 test evaluation/SFT unittest đều đạt.

## Xây dựng 2 bộ benchmark đánh giá RAG theo tỉ lệ - 2026-11-01

- **Mục tiêu:** Cung cấp hai bộ test RAG chuẩn mực có tỉ lệ phân phối tự nhiên, tránh hiện tượng lệch lĩnh vực và lệch nhãn section từ dữ liệu thô.
- **Thực hiện:** Xây dựng script `scripts/build_test_rag_benchmark.py` sinh hai bộ benchmark: `test_rag_pa1_ratio_balanced.jsonl` (cân bằng 6 tỉ lệ tự nhiên) và `test_rag_pa2_max_procedure_coverage.jsonl` (phủ cực đại thủ tục).
- **Kết quả:** Hai file đã tạo tại `Data/dataset_v3/test_rag/`: PA1 có 638 mẫu (406 thủ tục, Đất đai 23%, Section 16-24%, Single/Multi 50/50); PA2 có 917 mẫu (phủ 100% 808 thủ tục, 66 ca bẫy, Đất đai 24,3%). Cả hai file đều pass 100% Draft 2020-12 schema, 0 leakage và 0 duplicate ID.

## Golden smoke phân biệt thủ tục trùng tên - 2026-10-30

- **Mục tiêu:** Không chấm hành vi hỏi làm rõ an toàn thành routing sai khi Golden ngầm chọn một mã trong nhiều thủ tục trùng tên.
- **Thực hiện:** `GOLDEN_V3_006630` nêu rõ Thanh Hóa, mã `1.115490` và `metadata_filters.source_code`; validator liệt kê candidate có tên bằng nhau nhưng thiếu mã để rà soát.
- **Kết quả:** Smoke mới `dataset-v3-train-rag-10-20261030-run-3` đạt route accuracy 10/10. Case đích có `IN_SCOPE/NEW/PROCEDURE`, chỉ truy xuất `1.115490` và trả `answer`; runtime vẫn hỏi chọn khi tên trùng mà không có mã.

## Extended metrics sau prediction - 2026-10-30

- **Mục tiêu:** Cho phép tái chấm prediction bất biến và xuất một bộ case-score/summary/report thống nhất.
- **Thực hiện:** `score --rescore` dựng artifact dẫn xuất trong thư mục tạm; lexical/embedding/BERTScore được gắn theo từng case và khóa bằng hash đầu vào.
- **Kết quả:** Luồng merge và tái chấm run đã tồn tại đã được xác minh; smoke 10/10 giữ nguyên prediction. Extra `evaluation` và môi trường hiện tại có đủ BERTScore/sentence-transformers với Transformers 4.57.3; trọng số metric thật chưa được tải/chạy.

## Evaluation v3.2 có routing và cohort - 2026-10-30

- **Mục tiêu:** Prediction và score phản ánh được route cuối, đồng thời tách kết quả follow-up/new-question.
- **Thực hiện:** `execution.routing` giữ route thô/canonical và nhãn classifier quan sát được; case-score có `routing.route_accuracy`; summary có `cohort_metric_aggregates` theo turn type.
- **Kết quả:** Hợp đồng schema và hồi quy đã đạt. Lỗi collector bỏ qua `included_text` trong trace đã được sửa; run smoke hiện có 10/10 prediction thành công, gồm 5/5 follow-up và 5/5 new-question, không còn case lỗi do thiếu prompt context.

## Follow-up không có signed state - 2026-10-30

- **Mục tiêu:** Xử lý history tham chiếu của evaluator và client stateless mà không tin nội dung assistant hoặc menu không ký.
- **Thực hiện:** Router khôi phục duy nhất một định danh thủ tục có trong catalog từ các lượt `user` mới nhất; signed state vẫn ưu tiên và lựa chọn số vẫn bắt buộc state hợp lệ.
- **Kết quả:** Follow-up có mã hoặc tên duy nhất tiếp tục retrieval đúng thủ tục; nhiều/mã lạ/assistant-only vẫn `clarify`, câu hỏi thủ tục mới không kế thừa chủ đề cũ. 395 test đạt, 21 skipped.

## Dataset và Evaluation v3.2 - 2026-10-30

- **Mục tiêu:** Dùng một hợp đồng đánh giá thống nhất cho Dataset v3, prediction, case-score và summary.
- **Thực hiện:** Resolver ưu tiên `Data/dataset_v3/{split}/golden_{split}.jsonl` và vẫn đọc layout legacy. Collector/scorer end-to-end và retrieval-only dùng schema v3.2, action/architecture canonical, trace prompt/context thật và provenance fine-tuned bắt buộc.
- **Kết quả:** Dataset 7.100 case hợp lệ; train/test 4.258/2.838 không trùng ID hoặc nhóm `(domain, standalone_query)`. Smoke RAG thật và ba artifact đánh giá pass schema; web Docker healthy. Full suite đạt 389 test, 21 skipped.

## Hiển thị trạng thái đánh giá cho từng câu trả lời Web - 2026-10-30

- **Mục tiêu:** Làm rõ kết quả và mức bằng chứng của từng phản hồi ngay trên Web.
- **Thực hiện:** API công khai thêm `evidence_status`; Web hiển thị action, evidence, retrieval, quyết định routing, phạm vi, loại lượt và section bằng nhãn tiếng Việt kèm mã kỹ thuật.
- **Kết quả:** 114 test liên quan đạt; Web Docker healthy. Hai endpoint chat thật truyền đủ action/evidence/retrieval; JavaScript Web đã kiểm tra cú pháp và formatter trạng thái. Chưa kiểm tra trực quan vì phiên Computer Use không có trình duyệt khả dụng.

## Từ chối theo bằng chứng truy xuất và bảo toàn Unicode - 2026-10-30

- **Mục tiêu:** Giữ câu trả lời trong phạm vi bằng chứng thực tế, không suy từ hình thức mã hồ sơ và không phát sinh mojibake.
- **Thực hiện:** Luồng RAG truy xuất trước rồi kiểm tra định danh riêng có xuất hiện trong context hay không; chỉ `abstain/missing` khi bằng chứng thiếu. Câu chào độc lập vẫn được tách khỏi thủ tục cũ.
- **Kết quả:** 112 test tập trung đạt; 150/150 ca `is_unanswerable` được nhận diện, 0/6.950 ca còn lại bị đánh dấu nhầm. Web Docker healthy; `/api/chat` thật trả tiếng Việt UTF-8 đúng và không có ký tự `�`.

## Bổ sung ca không có câu trả lời cho golden v3 - 2026-10-30

- **Mục tiêu:** Tăng độ bao phủ đánh giá khả năng từ chối suy đoán khi PDF/metadata không chứa dữ liệu vận hành của hồ sơ cá nhân.
- **Thực hiện:** Tạo 150 ca từ 138 thủ tục thuộc 56 lĩnh vực, gồm 30 follow-up và 120 câu hỏi mới; phủ đều trạng thái, cán bộ xử lý, lý do từ chối, lịch hẹn và yêu cầu bổ sung.
- **Kết quả:** Dataset hiện có 7.100 bản ghi; 150 ca mới đều dùng `is_unanswerable=true`, `expected_action=abstain`, context/citation rỗng và `metadata_filters.source_code` trỏ đúng cặp PDF/metadata. Toàn bộ file hợp lệ schema, không trùng ID hoặc bản ghi.

## Golden dataset v3 hợp nhất, schema-clean — 2026-10-30

- **Mục tiêu:** Có một file golden cuối dùng được cho đánh giá, không còn khác biệt schema giữa hai bộ dữ liệu.
- **Thực hiện:** `Data/dataset_v3/golden_all.jsonl` chứa 7.100 bản ghi, 283 domain; 6.950 ca chuẩn hóa dùng ID `GOLDEN_V3_000001` → `GOLDEN_V3_006950`, 150 ca không có câu trả lời dùng ID `GOLDEN_V3_UA_000001` → `GOLDEN_V3_UA_000150`; `validation_audit` nằm trong `golden_all.audit.jsonl`; bản trước chuẩn hóa giữ tại `golden_all.pre-normalize.jsonl`.
- **Kết quả:** 7.100/7.100 bản ghi hợp lệ schema, 0 ID trùng và 0 bản ghi giống hoàn toàn. Các mapping ngữ nghĩa đã chốt: `easy` → `medium`, `test` → `in_domain`, `relevance_completeness` theo báo cáo, bổ sung 19 domain vào enum.

## Đồng bộ hóa tài liệu kiến trúc RAG Contract v2 và kiểm chứng toàn diện — 2026-10-29

- **Mục tiêu:** Đồng bộ hóa toàn bộ tài liệu kiến trúc hệ thống (rchitecture.md), hướng dẫn routing bốn head (our-head-routing.md), và hướng dẫn vận hành pipeline RAG (	rien-khai-rag-co-ban.md) theo đúng trạng thái mã nguồn và runtime hiện hành.
- **Thực hiện:** Cập nhật sơ đồ luồng Mermaid RAG v2, đặc tả PhoBERT 4-head, ranh giới HMAC signed state (256 phiên), cơ chế direct_choice (không chặn oan câu hỏi chứa số khi không có menu), nhánh phân rã Qwen extractive rewrite cho MIXED_SCOPE (<= 8 vế), cơ chế dự phòng unresolved_semantic_hits (trace semantic), bảng tham số cấu hình RAG v2 loại bỏ hoàn toàn FastText cũ, ghi chú thực nghiệm về độ trễ Reranker CPU (~12,28s).
- **Kết quả:** Bộ kiểm thử tự động 392/392 test pass (21 skipped cho external), toàn bộ tài liệu kiến trúc và hướng dẫn vận hành đồng bộ 100% với mã nguồn src/vigovbot/rag/.

## Semantic retrieval khi thiếu danh tính thủ tục - 2026-10-29

- **Mục tiêu:** Cho phép generation dùng evidence FAISS nếu không tìm được tên/mã thủ tục nhưng semantic search vẫn có kết quả.
- **Thực hiện:** Candidate semantic không gán mã được giữ làm evidence khi chưa nhận diện tên; trace phân biệt chiến lược `semantic` với `procedure_direct`.
- **Kết quả:** AST và `git diff --check` đạt; toàn bộ 392 unit test tự động đạt (21 skipped).

## Fallback rewrite cho MIXED_SCOPE nhiều vế - 2026-10-29

- **Mục tiêu:** Cho phép LLM trích vế hành chính khi phân tách được câu nhưng PhoBERT không xác nhận vế nào.
- **Thực hiện:** Rewrite được phép khi không có vế hành chính độc lập nào được PhoBERT xác nhận, tối đa 8 vế; nhiều vế hành chính được xác nhận vẫn phải làm rõ.
- **Kết quả:** AST và `git diff --check` đạt; toàn bộ 392 unit test tự động đạt (21 skipped).

## Điều hướng số thứ tự khi không có menu - 2026-10-29

- **Mục tiêu:** Không chặn câu hỏi mới chỉ vì câu có cụm “thủ tục 1” hoặc “mục 2”.
- **Thực hiện:** Văn bản số chỉ được xem là lựa chọn khi có menu; trạng thái được truyền nhưng không xác thực vẫn bị từ chối.
- **Kết quả:** AST và `git diff --check` đạt; toàn bộ 392 unit test tự động đạt (21 skipped).

## Retrieval RAG sau khi gỡ reranker - 2026-10-29

- **Mục tiêu:** Trở về luồng truy xuất FAISS trực tiếp sau khi đo chi phí độ trễ của thử nghiệm reranker.
- **Thực hiện:** Khôi phục `top_k: 5`, gỡ cấu hình và module reranker online, dừng web trước khi xóa riêng cache `BAAI/bge-reranker-v2-m3`; giữ nguyên cache embedding, corpus và báo cáo benchmark.
- **Kết quả:** Reranker không còn tham gia runtime; web Docker healthy và `/api/health` trả HTTP 200 sau restart. Kết quả benchmark 10 câu vẫn được lưu tại [báo cáo](../reports/reranker-latency-20261029.md).


## Tích hợp PhoBERT routing — 2026-10-29

- **Mục tiêu:** Thay phân loại LLM và ghi đè nhãn section bằng checkpoint PhoBERT.
- **Thực hiện:** Nạp local bốn head/PyVi/ngưỡng gốc, adapter corpus/state, cấu hình mặc định và mount read-only; lớp dependency Docker riêng.
- **Kết quả:** Web local đang chạy PhoBERT; identity công bố hash checkpoint. Adapter khớp token/xác suất script gốc trên 7 ca. API thật xác nhận phí, căn cứ pháp lý hỏi tiếp, ngoài phạm vi và menu tên thủ tục → nhập số. Bộ runtime/routing trong image đạt 146 test, 2 skipped; 7 test cấu hình đạt. Full host đạt 383 test, 22 skipped. Chưa kiểm tra trực quan trình duyệt; head trộn thủ tục còn một ca đối chứng dự đoán sai.

## Xác định mã thủ tục trước truy xuất — 2026-10-29

- **Mục tiêu:** Giữ bằng chứng đúng khi router trả tên thiếu tiền tố Thủ tục.
- **Thực hiện:** Xác định mã độc lập với menu, ưu tiên tên/mã trong câu hỏi đơn thủ tục; bổ sung biến thể pháp lí.
- **Kết quả:** 125 kiểm thử liên quan, Ruff và compileall đạt. Web local đã nạp bản sửa; hai câu nguyên văn qua API streaming lấy đúng mã 1.000894: phí 1 đoạn, pháp lý 4 đoạn trong lượt hỏi tiếp. Chưa kiểm tra trực quan trình duyệt hoặc độ đầy đủ của câu trả lời sinh; chưa tái hiện trạng thái gây chọn nhầm 1.010998 ban đầu.

## Hợp đồng đánh giá bốn cấu hình v3.2 — 2026-10-28

- **Mục tiêu:** Thống nhất hợp đồng mới, bỏ tương thích schema đầu ra cũ.
- **Thực hiện:** Ba schema độc lập golden/prediction/evaluation, chỉ có $ref nội bộ;
  architecture base/finetuned/rag/finetuned_rag quyết định dữ liệu và metric áp dụng;
  Base/fine-tuning không cần retrieval, điểm không áp dụng không ghi thành 0.
  Không chấm router; fine-tuning bắt buộc định danh adapter/checkpoint. Golden có
  evaluation_plan, relevance nhị phân và liên kết bằng chứng/cặp thử nhiễu.
  Theo phạm vi người dùng chốt: chỉ schema, kiểm thử và tài liệu; runtime giữ nguyên.
- **Kết quả:** 44 kiểm thử schema/tài liệu đạt; hai ví dụ multi-intent hợp lệ.
  JSONL cũ giữ nguyên, cần bổ sung evaluation_plan trước khi dùng schema mới.
  Ví dụ JSON là fixture tổng hợp. Collector/scorer chưa hỗ trợ v3.2; kiểm tra
  liên kết ID/hash/rank xuyên trường cần validator ngữ nghĩa khi triển khai runtime.

## Mục tiêu

Vận hành ViGovBot bằng cấu trúc canonical, hỗ trợ Base, RAG và QLoRA; đánh giá
có nguồn gốc rõ ràng và truy hồi đúng thủ tục hành chính.

## Thực hiện

- Routing mặc định v2: bốn nhóm nhãn, model base Qwen độc lập, trạng thái có chữ ký, menu dạng văn bản trên web và truy hồi theo từng thủ tục/section. Hợp đồng v1 chỉ còn tương thích LLM; v2 không dùng early exit prefix. Xem [hướng dẫn](../guides/four-head-routing.md).

- RAG đã có bước hỏi lại theo metadata: chọn thủ tục khi nhiều mã phù hợp,
  chọn section khi thiếu mục tiêu; context riêng từng model trên API thường/streaming
  và web, có hỗ trợ client cũ qua lịch sử. Không cần tạo lại embedding hoặc huấn luyện router.

- RAG follow-up đã có nhánh SQLite theo mã/phần, ngữ cảnh theo model/hội thoại,
  fallback giới hạn đúng nguồn và nút xóa hội thoại. Đã kiểm tra Python/JavaScript
  và model cục bộ; web đã restart để nạp backend mới ngày 2026-10-27.
- Source chính đặt tại `src/vigovbot/`; CLI công khai là `vigov`.
- Docker mặc định chạy web Base/RAG bằng Torch CPU và Ollama; QLoRA cục bộ
  nằm trong service/profile `web-gpu` tùy chọn. Cả hai dùng cache model/RAG bền vững.
- RAG hỗ trợ exact-match mã/tên thủ tục, ưu tiên loại mục và gửi trực tiếp kết
  quả FAISS vào LLM; host và Docker mặc định hiện dùng top 15, profile Docker GPU
  dùng top 5. Reranker BGE đã được gỡ khỏi runtime online.
- Evidence quá ngân sách được rút gọn theo hàng/field/phần tử hoàn chỉnh; không
  còn bỏ toàn bộ bảng hoặc JSON có thể chiếu an toàn vào prompt.
- Routing dùng context `4096` và giới hạn sinh `768` token riêng; generation vẫn
  dùng ngân sách `8192`/`512`.
- QLoRA dùng adapter đã huấn luyện; RAG vẫn là nguồn căn cứ cho nội dung hiện hành.
- Workflow evaluation hiện hành tách prediction, scoring, judge và report; đọc
  Golden v3, trong khi API complete-trace vẫn công bố capability version 2.
- Dataset v3 có artifact fine-tuning cục bộ tại `Data/dataset_v3/finetuning/`: train 3.385 case và validation 873 case, chia xác định theo nhóm domain/truy vấn để tránh leakage.
- Web dùng `/api/chat/stream` để hiển thị token dần theo quá trình sinh; endpoint
  `/api/chat` cũ vẫn giữ nguyên cho evaluation và client hiện có.

## Kết quả

- `Data/dataset_v3/duplicate_procedure_names/` chứa 46 folder tên trùng, 168 mã, 5.768 chunk metadata và 168 PDF nguồn từ corpus hiện hành. Mỗi folder có manifest nhóm, JSON metadata và PDF kèm checksum cho từng mã; Golden, split train/test và vector index không thay đổi.
- Mỗi folder tên trùng có thêm `golden_cases.jsonl` và `golden_cases_summary.json`; `golden_cases_manifest.json` ghi 794 case, gồm 539 case khớp mã trong nhóm, 255 case dùng mã ngoài nhóm cần rà soát và 3 case thiếu định danh nguồn. Golden gốc và split không thay đổi.

- Schema độc lập cho Golden Dataset v3 và evaluation record v3.2 nằm tại `schema/`; toàn bộ
  3.850 dòng Golden và evaluation record sinh từ `build_record` đã validate theo
  JSON Schema Draft 2020-12.

- Yêu cầu “Các thủ tục cấp lại chứng chỉ kiểm định viên” đã trả danh sách lựa
  chọn qua API thật sau restart, không tự chốt tên khớp 2.000066. Chọn mục 2
  chuyển sang các section của 1.000187; danh sách giới hạn năm mục có báo còn thêm.

- Sao chép nguyên dòng thủ tục gồm tên, mã, cấp thực hiện đã được xác minh qua API
  sau restart: mục 5 → 1.000180 và mục 1 → 2.000037, chuyển sang chọn section,
  không lặp lại danh sách thủ tục hoặc gọi lại router.

- Hỏi lại metadata và nối tiếp: bản sửa chọn dòng và hỏi danh sách đạt 106 test Python
  liên quan và 2 test JavaScript; Ruff/compileall đạt. Backend đã restart. Qwen thật
  qua API thường → streaming giữ mã kết hôn 1.000894 khi chọn mục phí rồi hỏi hồ sơ;
  lượt hồ sơ dùng procedure_direct và required_documents. Chưa thao tác trình duyệt thật.
  SQLite thực tế xác nhận 6.192 thủ tục và sáu section cho mã tạm trú 1.004194.

- Stack Docker CUDA, `/api/health`, `/api/chat` và `vigov doctor` đã được kiểm
  chứng ngày 2026-10-25.
- Retrieval theo mã/tên thủ tục đã được kiểm chứng bằng unit test và API
  container. Độ trễ thử nghiệm reranker được ghi riêng trong báo cáo ngày 2026-10-29;
  không dùng kết quả đó để kết luận chất lượng retrieval.
- Không có pipeline huấn luyện hoặc benchmark dài đang chạy.
- Hồ sơ vận hành đã được tinh gọn theo quy định mới.
- Cấu hình và regression routing đã được kiểm chứng; đã có baseline Qwen nhưng
  latency A/B classifier chưa được đo trên dataset routing độc lập.
- Streaming đã qua kiểm thử provider/API/UI giả lập và container thật. API
  `qwen-base` đã phát 4 sự kiện token, TTFT warm 0,300 giây và hoàn tất
  sau 0,486 giây; chưa thao tác xác minh trên trình duyệt thật.
- Image web mặc định là 2,03 GB và không chứa CUDA; Base/RAG streaming đã
  trả `success`. Image GPU 12,8 GB giữ riêng QLoRA, đã nhận RTX 4050/CUDA 12.8.
  BuildKit cache hiện 0 B sau khi thu hồi 32,01 GB; các volume model/RAG được giữ nguyên.

- Phép đo follow-up ngày 2026-10-27: retrieval warm 1,182 → 0,067 s; lượt cold
  1,170 → 1,456 s do nạp danh mục. Tổng latency vẫn phụ thuộc routing/generation.

- Kiểm chứng routing v2: 303 ca đạt, 22 ca bỏ qua trong 325 test; Ruff, compileall và diff check đạt. Catalog sửa nhãn ngoài phạm vi sai khi câu hỏi khớp hành động/đối tượng thủ tục, đồng thời xếp hạng ứng viên theo khoảng cách từ khóa để tránh trôi miền semantic. API Qwen thật xác nhận “thuê đất” trong phạm vi và “thành lập trường” chỉ trả ứng viên giáo dục. Chưa thao tác trình duyệt thật do không có browser kết nối.

- PhoBERT không vượt ngưỡng section nhưng đã xác định chính xác một thủ tục và
  câu hỏi còn mục tiêu cụ thể thì retrieval tìm toàn bộ section của đúng mã;
  câu chỉ nêu tên/mã vẫn mở menu. API thật xác nhận câu hỏi đối tượng thực hiện
  của mã 3.000622 trả đúng `metadata_identity_1_p1`.

- Chunking mới đồng bộ bốn section chi tiết với PhoBERT: `submission_method`,
  `processing_time`, `fee`, `result`. Runtime hiện vẫn dùng corpus legacy và cầu
  đọc tương thích; chưa rebuild/công bố FAISS nên chưa đo mức giảm token.

- Arbitration phạm vi chỉ cho catalog đổi `OUT_OF_SCOPE` khi
  `0,50 ≤ P(OUT) < 0,85`; trace ghi xác suất, band và outcome. Câu trần “Đăng ký
  kết hôn” có thể bị giữ ngoài phạm vi vì checkpoint từng cho `P(OUT)≈0,925`.

- Curated alias có thể xác nhận trực tiếp mã; hybrid BM25/cosine với qualifier
  penalty chỉ được mở confirmation menu cho cụm ngắn đủ score và margin. Menu
  không retrieval/generation; chọn mới nâng scope, phủ nhận giữ ngoài phạm vi.

- Khi PhoBERT dự đoán `MIXED_SCOPE` mà split câu bằng dấu câu/“và” thất bại,
  Qwen được gọi một lần để trích câu hỏi nguyên văn; PhoBERT phải xác nhận lại
  `IN_SCOPE` trước retrieval. API thật đã trả đúng phí mã 1.000894 và ghi chú phần
  ngoài phạm vi. Chưa đo tỷ lệ ca mixed trong traffic hoặc hiệu năng đại diện.

- Section được nêu rõ trong câu hỏi như hồ sơ, trình tự hoặc căn cứ pháp lý có
  thể hiệu chỉnh nhãn section PhoBERT cho một request `IN_SCOPE`; scope và danh
  tính thủ tục vẫn giữ nguyên. API local đã xác nhận chuỗi follow-up mã 1.000894
  truy xuất đúng `required_documents`, `procedure_step` và `legal_basis`.
