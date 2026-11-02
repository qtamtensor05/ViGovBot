# Báo cáo kết quả fine-tuning QLoRA

> Artifact hiện hành `outputs/qlora/best_adapter` · rà soát ngày 02/11/2026

## Mục tiêu

Tổng hợp kết quả fine-tuning có thể kiểm chứng trực tiếp từ `outputs`: dữ liệu, cấu hình adapter, môi trường GPU, artifact xuất ra và đánh giá sau huấn luyện. Số liệu không còn log gốc không được phục dựng từ báo cáo cũ.

## Dữ liệu huấn luyện

| Split | Bản ghi | Cấu trúc hội thoại | SHA-256 |
|---|---:|---|---|
| Train | 1.931 | 1.176 hội thoại 2 message; 755 hội thoại 4 message | `7c2d3c7260c119d8da129b334fb6f352a64e24c99b00bf2752fd7629fda19083` |
| Validation | 827 | 503 hội thoại 2 message; 324 hội thoại 4 message | `526f58f13c056b0865c93686eda32d8fa85e7d4faf1523f5479ae8c257c07700` |

`dataset_report.json` ghi không có nhóm hội thoại trùng khớp hoàn toàn trong từng split. Kết luận overlap/near-duplicate phải đọc theo đúng trường và ngưỡng trong artifact.

## Cấu hình mô hình và adapter

| Hạng mục | Giá trị đã kiểm chứng |
|---|---|
| Mô hình nền | `Qwen/Qwen2.5-7B-Instruct` |
| PEFT | LoRA cho `CAUSAL_LM` |
| Lượng tử hóa | `4bit-nf4` |
| Rank / alpha / dropout | 16 / 32 / 0,05 |
| Target modules | `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj` |
| Adapter được chọn | `checkpoint-300` / `step-300` |
| Giải mã trong metadata | Greedy |
| Kích thước adapter | 161.533.192 byte, khoảng 154,05 MiB |

`training_args.bin` tồn tại, nhưng output không có `trainer_state.json`, log history, checkpoint trung gian hoặc biểu đồ loss. Do đó learning curve, train/validation loss, số epoch thực chạy, thời gian huấn luyện, early stopping, throughput và VRAM đỉnh đều là `NOT VERIFIED`. Những số này trong báo cáo cũ không được tiếp tục khẳng định nếu thiếu log nguồn.

## Cấu hình máy fine-tuning/preflight

| Thành phần | Giá trị |
|---|---|
| Hệ điều hành | Windows 10 build 19045 |
| Python | 3.11.9, 64-bit |
| GPU | NVIDIA GeForce RTX 5060 Ti |
| VRAM tổng / rảnh lúc preflight | 15,90 / 14,82 GiB |
| CUDA / compute capability | 13.0 / 12.0 |
| BF16 | Có hỗ trợ |
| PyTorch | 2.9.1+cu130 |
| Transformers / PEFT / TRL | 4.57.3 / 0.18.0 / 0.26.2 |
| Accelerate / bitsandbytes | 1.12.0 / 0.49.0 |

CPU và RAM là `NOT VERIFIED`. Khoảng VRAM ước lượng 12–21 GiB trong preflight là heuristic, không phải VRAM thực đo khi train.

## Kết quả artifact và đánh giá downstream

Fine-tuning đã tạo được adapter PEFT có cấu hình, tokenizer và metadata liên kết checkpoint 300. Đây là bằng chứng đóng gói adapter thành công, không tự chứng minh quá trình train hội tụ hoặc checkpoint 300 là tối ưu theo validation loss.

| Chỉ số trên tập test v3 (638 mẫu) | Base | QLoRA | Chênh lệch |
|---|---:|---:|---:|
| BERTScore F1 | 0,8479 | 0,9119 | +0,0640 |
| ROUGE-1 F1 | 0,1700 | 0,4719 | +0,3019 |
| ROUGE-L F1 | 0,1117 | 0,4482 | +0,3365 |
| chrF | 20,9224 | 45,3621 | +24,4397 |
| Key-fact coverage | 0,0153 | 0,1302 | +0,1149 |
| Completion token trung bình | 311,64 | 77,88 | -233,76 |
| Tổng độ trễ trung bình | 6.642,85 ms | 5.720,39 ms | -922,46 ms |

Adapter cải thiện mạnh độ gần đáp án tham chiếu và làm câu trả lời ngắn hơn. Tuy nhiên abstention correctness vẫn bằng 0 và không có groundedness, nên chưa đủ căn cứ tuyên bố mô hình đúng pháp lý hay thay thế được RAG. Khi kết hợp RAG, key-fact coverage tăng lên 0,3108 và abstention lên 0,4634 nhưng BERTScore giảm còn 0,8914; đây là trade-off, không phải thứ hạng “tốt nhất tổng thể”.

## Kết luận và việc còn thiếu

Fine-tuning đã tạo thành công adapter checkpoint 300 và cho cải thiện rõ trên nhiều metric generation so với Base. Kết luận về quá trình tối ưu vẫn bị giới hạn bởi thiếu log huấn luyện gốc. Hồ sơ đầy đủ cần bổ sung `trainer_state.json` hoặc log tương đương, đường loss train/validation, thời gian và VRAM thực đo, tiêu chí chọn best checkpoint, cùng checksum/revision chính xác của mô hình nền.

Nguồn: `outputs/qlora/dataset_report.json`, `preflight_rtx5060ti.json`, `best_adapter/adapter_config.json`, `model_metadata.json`, `adapter_model.safetensors`, và hai run `eval-base-v3`, `eval-qlora-v3`.

