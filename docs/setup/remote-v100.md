# Triển khai container Tesla V100 32 GB

Profile train Golden SFT: `configs/training/environments/v100_32gb_golden_sft.yaml`.
V100 dùng FP16 cho compute NF4; profile throughput dùng train batch 2, eval batch 4,
gradient accumulation 4 (effective batch vẫn 8), 4 worker pinned/persistent và tắt
gradient checkpointing. Smoke dùng cùng profile để chặn OOM trước full training.
Smoke có profile riêng `configs/training/experiments/smoke_v100_32gb_golden_sft.yaml`.

Sau khi đồng bộ repository và hai thư mục `Data/golden_dataset*` vào
`/workspace/ViGovBot`, chuẩn bị và kiểm tra môi trường:

```bash
bash scripts/remote/setup_v100.sh /workspace/ViGovBot
bash scripts/remote/verify_v100.sh /workspace/ViGovBot
```

Hai script không chạy training/evaluation và không tải model weights. Model/tokenizer
chỉ tải khi người dùng chủ động chạy smoke hoặc training.

Lệnh do người dùng chủ động chạy sau khi xem preflight:

```bash
export PATH="/workspace/ViGovBot/.venv-v100/bin:$PATH"
hash -r
python -m vigovbot.training.train --config configs/training/experiments/smoke_v100_32gb_golden_sft.yaml --approve --run-id smoke-v100-DATE
python -m vigovbot.training.train --config configs/training/environments/v100_32gb_golden_sft.yaml --approve --run-id qlora-v100-DATE
```

Đánh giá tự động đầy đủ dùng `vigov eva complete-v2` theo
[hướng dẫn evaluation mở rộng](../guides/evaluation-extended.md). RAG cần thêm
`Data/vector/unified` (khoảng 6,8 GB ở máy nguồn), Ollama và web service; Base hoặc
QLoRA evaluation không cần vector index. Không chép `.env`, checkpoint hoặc cache
từ máy nguồn vào container. Giữ `outputs/` trên storage bền vững và tải artifact
về trước khi hủy container.

