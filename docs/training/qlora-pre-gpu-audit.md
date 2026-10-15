# Audit pre-GPU pipeline QLoRA Qwen2.5-7B

Ngày audit: 2026-10-14 (Asia/Saigon)  
Phạm vi: source, config, test và dataset hiện có trong repository.  
Ranh giới: không tải trọng số Qwen2.5-7B, không chạy CUDA/QLoRA thật.

## Kết luận

**READY có điều kiện cho GPU smoke testing, chưa READY cho full training.**

Implementation local không còn critical finding đã biết sau audit. Bước tiếp
theo bắt buộc là preflight và smoke 4 optimizer step trên Linux CUDA, sau đó
kiểm tra checkpoint/resume và artifact thật trước khi cho phép full run.

## Thành phần đã xác minh

### Chat template, multi-turn và loss masking

- Official tokenizer `Qwen/Qwen2.5-7B-Instruct` được nạp cache-only.
- Multi-turn 2/4/6 message giữ đúng thứ tự user/assistant.
- Header `<|im_start|>assistant` bị mask `-100`; nội dung assistant và
  `<|im_end|>` được supervise. User/system/template không sinh loss.
- Mẫu vượt `max_seq_length` bị từ chối toàn bộ; không cắt im lặng
  câu trả lời cuối.
- Collator pad input bằng pad/EOS, attention mask bằng 0 và label bằng `-100`.

### QLoRA và PEFT

- Config bắt buộc 4-bit NF4, double quantization, BF16 hoặc FP16 compute.
- Target modules Qwen được khóa đúng bộ:
  `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`.
- Optimizer bắt buộc `paged_adamw_8bit`; gradient checkpointing được
  truyền cả vào k-bit preparation và `TrainingArguments`.
- Runtime kiểm tra chỉ parameter có tên `lora_` được trainable.
- BF16 chỉ chọn khi GPU báo hỗ trợ; nếu không thì FP16. Không có
  fallback ngầm sang CPU hoặc full fine-tuning.

NF4 cho training model 4-bit, compute dtype và nested quantization phù hợp
với tài liệu Transformers/bitsandbytes. PEFT cho phép target module bằng
danh sách tên suffix. Tham chiếu:
[Transformers bitsandbytes](https://huggingface.co/docs/transformers/main/quantization/bitsandbytes),
[PEFT LoRA](https://huggingface.co/docs/peft/main/package_reference/lora).

### Early stopping, best checkpoint và resume

- `eval_steps == save_steps` và eval/save strategy phải khớp.
- `load_best_model_at_end=True`; sau `Trainer.train()`, pipeline yêu cầu có
  `best_model_checkpoint`/`best_metric`, đánh giá lại model đã restore rồi
  mới lưu `best_adapter`.
- Resume tiếp tục trong run directory cũ, không tạo run rỗng mới.
- Validator checkpoint yêu cầu adapter weights, `trainer_state.json`,
  `optimizer.pt`, `scheduler.pt`, `rng_state*.pth`, global step hợp lệ và
  callback state; từ chối marker checkpoint incomplete.
- Config snapshot và dataset SHA-256 phải khớp run gốc.
- `restore_callback_states_from_checkpoint=True`, `ignore_data_skip=False`,
  `save_only_model=False` được đặt tường minh.

Trainer chính thức restore model/optimizer/scheduler/RNG khi resume; callback
state chỉ restore khi bật option tương ứng. Tham chiếu:
[Trainer recipes](https://huggingface.co/docs/transformers/trainer_recipes),
[Trainer API](https://huggingface.co/docs/transformers/main/main_classes/trainer).

### Dataset và evaluation isolation

- Validator thật đọc 3.000 train, 1.000 validation, 1.000 test; ID duy nhất
  toàn split, role/order/content hợp lệ.
- Không có exact conversation hoặc exact question overlap giữa split.
  Answer/procedure/near-question overlap được report, không tự xóa.
- Training chỉ đọc train/validation. Test không tham gia early stopping,
  tuning hay checkpoint selection.
- Generation evaluation dùng `messages[:-1]`; reference assistant cuối không
  được đưa vào prompt. Teacher-forced loss dùng đầy đủ conversation.

### Metrics, accounting và plots

- Token loss/perplexity được aggregate theo số target token, không theo
  trung bình example. Perplexity là `exp(token_cross_entropy)`.
- EM raw, normalized EM, bag-of-token precision/recall/F1 và ROUGE-1/2/L
  là macro mean. BLEU và chrF là corpus score SacreBLEU.
- Train/validation generalization gap được tính bằng hai lần evaluation
  token-loss trên cùng best-restored model.
- Parameter report tách base count, PEFT total, LoRA trainable, frozen,
  percentage và adapter size. Quantized footprint dùng `get_memory_footprint()`
  khi runtime cung cấp; FP16/BF16 baseline được ghi rõ là estimate.
- Peak allocated/reserved VRAM dùng CUDA counters sau reset. GPU utilization
  không có sampler thì để unavailable.
- Wall time và time/optimizer-step là measured; GPU kernel time không bị bịa.
- Plot chỉ đọc observation có thật theo `step`, không interpolate; loss
  plot đánh dấu best checkpoint và early-stop step từ metrics artifact.

### Portability và chatbot

- Windows local chỉ cần CPU dependencies; GPU flow tách sang Linux CUDA.
- Path dữ liệu/output tương đối với project root và override được
  bằng CLI/environment.
- PyTorch CUDA wheel phải cài từ index phù hợp driver; tài liệu PyTorch
  liệt kê wheel 2.9.1 cho CUDA 12.6/12.8/13.0:
  [PyTorch previous versions](https://pytorch.org/get-started/previous-versions/).
- bitsandbytes 0.49.0 yêu cầu Python >=3.10, PyTorch >=2.3; CUDA/NVIDIA
  compatibility vẫn phải xác nhận trên host thật:
  [bitsandbytes 0.49 installation](https://huggingface.co/docs/bitsandbytes/v0.49.0/installation).
- Chatbot giữ API contract, nạp cùng base model với hoặc không có PEFT
  adapter, kiểm base model name trong adapter config và mặc định chỉ cache
  một bản 7B. Adapter PEFT lưu riêng khỏi base weights:
  [PEFT checkpoint format](https://huggingface.co/docs/peft/main/developer_guides/checkpoint).

## Issues phát hiện và fix đã áp dụng

1. **Critical:** assistant header bị supervise. Đã chuyển boundary sang sau
   generation prompt; EOS assistant vẫn được supervise.
2. **Critical:** truncation có thể giữ target cũ nhưng cắt target cuối. Đã
   từ chối mọi conversation vượt max length.
3. **Critical:** resume tạo run directory mới và chỉ kiểm adapter/trainer
   state. Đã resume run cũ và xác minh optimizer/scheduler/RNG/callback,
   global step, config và dataset hash.
4. **High:** callback early stopping không được restore tường minh. Đã bật
   `restore_callback_states_from_checkpoint` và thêm test state transition.
5. **High:** loss evaluation trung bình theo example. Đã chuyển sang weighted
   average theo assistant target token.
6. **High:** BLEU/chrF report là mean của sentence scores. Đã dùng corpus
   BLEU/chrF; giữ per-example score cho manual inspection.
7. **High:** final training loss và validation loss không cùng định nghĩa.
   Đã evaluate cả hai split bằng best-restored model.
8. **Medium:** base parameter count có thể đếm qua wrapper PEFT. Đã đếm
   trước khi wrap và kiểm danh sách trainable names.
9. **Medium:** adapter inference không kiểm base model compatibility. Đã
   validate `base_model_name_or_path` trước khi load PEFT.
10. **Test outdated:** `test_multiturn` mong `response_format="json"`, trong khi
    structured runtime cố ý dùng JSON schema và các test khác đã khóa
    contract này. Đã sửa assertion test; provider vẫn hỗ trợ caller JSON
    mode cũ nên backward compatibility được giữ.

## Kết quả test thực tế

- `python -m unittest discover -s tests -p 'test_*.py' -q`:
  **136 passed, 1 skipped, 0 failed**.
- Nhóm audit QLoRA/multi-turn: **27 passed, 1 skipped**.
- `ruff check training tests src`: **passed**.
- `compileall training src tests`: **passed**.
- `git diff --check`: **passed**; chỉ có cảnh báo line-ending Windows.
- Dataset validation + official tokenizer cache-only: **passed 5.000/5.000**.
- Preflight local: CUDA unavailable, bitsandbytes/PEFT/TRL/Accelerate chưa cài;
  đúng với môi trường local, không phải GPU verification.

Test skipped là dataset QA-v4 tùy chọn không có tại path fixture; không
thuộc pipeline QLoRA SFT hiện tại.

## Hạng mục chỉ có thể verify trên GPU

- PyTorch CUDA wheel, driver, bitsandbytes kernels và `paged_adamw_8bit` thực tế.
- NF4 load của Qwen2.5-7B, module target tồn tại và chỉ LoRA trainable.
- BF16/FP16 forward-backward, gradient checkpointing, OOM margin và throughput.
- Trainer checkpoint thật có optimizer/scheduler/RNG/callback files; resume từ
  checkpoint tăng global step liên tục và không reset patience/LR.
- Best checkpoint được restore byte-for-byte và `best_adapter` load được.
- Baseline và PEFT generation trên cùng held-out examples; VRAM peak, timing,
  TensorBoard, plots và report từ log thật.

## Rủi ro còn lại

- Version pin có thể cài được nhưng kernel compatibility phụ thuộc
  GPU/driver/CUDA host; preflight hiện chỉ report, không thể thay smoke thật.
- Near-duplicate detector dùng top-10 candidate heuristic; exact overlap là đầy
  đủ nhưng near-overlap không phải exhaustive O(N²).
- Rule-based procedure/legal/authority checks không chứng minh factual grounding;
  unsupported claim/refusal vẫn unavailable nếu thiếu label/evidence.
- `save_total_limit=3` giữ best checkpoint theo Trainer contract, nhưng cần
  quan sát artifact thật trên phiên bản pin.
- KeyboardInterrupt chỉ lưu state/report tại checkpoint gần nhất; không hứa
  khôi phục gradient dang dở giữa optimizer step.

## Các bước GPU tiếp theo

1. Trên Linux NVIDIA, tạo Python 3.10-3.12 venv. Cài PyTorch 2.9.1 từ
   index CUDA phù hợp driver, sau đó cài requirements GPU:

   ```bash
   python -m venv .venv-qlora
   source .venv-qlora/bin/activate
   python -m pip install --upgrade pip
   # Chọn đúng cu126/cu128/cu130 theo driver, ví dụ:
   python -m pip install torch==2.9.1 --index-url https://download.pytorch.org/whl/cu128
   python -m pip install -r requirements/qlora-gpu.txt
   python -m pip check
   ```

2. Chuyển ba JSONL ngoài Git, xác minh SHA-256 và validator:

   ```bash
   sha256sum Data/tthc_test_case_v1/data/*_sft.jsonl
   python -m training.validate_data --config configs/training/environments/gpu.yaml --with-tokenizer
   ```

3. Chạy preflight; xem gợi ý nhưng không tự áp dụng:

   ```bash
   python -m training.preflight --config configs/training/environments/gpu.yaml
   ```

4. Chạy smoke 4 step vào run ID ghi rõ `smoke`; lần này mới tải/nạp
   model weights sau khi người dùng duyệt:

   ```bash
   python -m training.train --config configs/training/experiments/smoke.yaml --approve --run-id smoke-HOST-DATE
   ```

5. Xác nhận `environment.json`, `training_log.csv`, best checkpoint, optimizer,
   scheduler, RNG, callback state, adapter, CUDA peak và plots. Sau đó resume
   chính checkpoint smoke và xác nhận global step/LR/patience liên tục:

   ```bash
   python -m training.train --config configs/training/experiments/smoke.yaml --approve \
     --resume outputs/qlora/smoke-HOST-DATE/checkpoints/checkpoint-2
   ```

6. Chỉ khi smoke + resume đạt mới chạy full training bằng run ID mới.
   Evaluation test chỉ chạy sau khi checkpoint selection kết thúc:

   ```bash
   python -m training.train --config configs/training/environments/gpu.yaml --approve --run-id experiment-001
   python -m training.evaluate --run_dir outputs/qlora/experiment-001 --split validation
   python -m training.evaluate --run_dir outputs/qlora/experiment-001 --split test
   python -m training.plot --run_dir outputs/qlora/experiment-001
   python -m training.report --run_dir outputs/qlora/experiment-001
   ```

