# Continued-SFT theo hợp đồng QLoRA + RAG

## Mục tiêu

Pipeline này huấn luyện QLoRA với đúng dạng prompt evidence và target JSON của
runtime RAG. Pipeline chạy độc lập, không thay đổi artifact hoặc profile plain SFT.

## Tạo và kiểm tra dữ liệu

```powershell
vigov data filter-rag-leakage `
  --source-dir Data/dataset_v3/fintuning `
  --test Data/dataset_v3/test_rag/test_rag_pa1.jsonl `
  --test Data/dataset_v3/test_rag/test_rag_pa2.jsonl `
  --output-dir Data/dataset_v3/fintuning_clean

vigov data golden-to-rag-sft `
  --source-dir Data/dataset_v3/fintuning_clean `
  --output-dir Data/dataset_v3/finetuning_rag_clean

vigov data check `
  --config configs/training/experiments/golden_rag_sft.yaml `
  --output Data/dataset_v3/finetuning_rag_clean/validation_report.json
```

Filter dùng policy procedure/content-disjoint: loại case trùng mã thủ tục, context
ID/text, standalone query hoặc đáp án dài nguyên văn với PA1/PA2. Câu mẫu ngắn và
near-duplicate khác thủ tục chỉ được báo cáo, không tự loại. Nguồn và test không bị
ghi đè; danh sách bị loại nằm trong `fintuning_clean/excluded_cases.jsonl`.

Converter chỉ đọc `train` và `val` sạch, không đọc test. Input gồm system prompt, lịch
sử, câu hỏi và evidence JSON; target gồm `answer`, `action`, `evidence_status` và
`citations`. Nhãn chấm khác không được đưa vào input.

Muốn đo token bằng tokenizer chính thức, thêm `--with-tokenizer`. Dùng
`--local-files-only` để cấm tải mạng; lệnh báo lỗi nếu cache chưa có tokenizer.
Profile đặt `max_seq_length: 16384`. Mẫu vượt giới hạn bị từ chối, không cắt
evidence hoặc assistant target.

## Huấn luyện

```powershell
vigov train start `
  --config configs/training/environments/rtx5060ti_16gb_rag_sft.yaml `
  --run-id qlora-rag-sft-HOST-DATE `
  --dry-run
```

Sau dry-run phải chạy GPU smoke trước full run vì sequence 16k có thể vượt VRAM.
Không resume checkpoint khác config hoặc khác hash dataset.

## Chấm test độc lập

Sau khi train, merge adapter và công bố local model với tên
`qwen-qlora-rag-sft:latest`, rồi chạy endpoint riêng:

```powershell
vigov web --config configs/rag/evaluation-qlora-rag-sft.yaml --port 8002

vigov eva run `
  --dataset Data/dataset_v3 `
  --split test `
  --profile qlora_rag `
  --run-id qlora-rag-sft-test-DATE `
  --endpoint http://localhost:8002/api/chat `
  --config configs/rag/evaluation-qlora-rag-sft.yaml `
  --model-metadata outputs/qlora/<run-id>/model-metadata.json `
  --complete-trace
```

Profile chấm vẫn dùng kiến trúc canonical `finetuned_rag`; config riêng chỉ đổi
model phục vụ sang `qwen-qlora-rag-sft:latest`. Không dùng validation SFT thay test.
