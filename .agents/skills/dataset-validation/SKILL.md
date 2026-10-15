---
name: dataset-validation
description: Validate ViGovBot JSON or JSONL datasets for schema, splits, duplicates, leakage, distributions and conversational edge cases. Use before training or evaluation.
---

# Dataset Validation

Kiểm tra dữ liệu trước training/evaluation.

## Hợp đồng

- Input: JSON/JSONL và mô tả split/schema; khóa identity nếu có.
- Output: Báo cáo schema, duplicate/near-duplicate, leakage, distribution, edge-case coverage và warning có mẫu.

## Quy trình

+1. Xác nhận schema single-turn/multi-turn và ID ổn định.\n2. Chạy `scripts/validate_dataset.py` cho kiểm tra deterministic.\n3. Kiểm tra duplicate trong split và leakage xuyên split; near-duplicate phải ghi threshold/method.\n4. Báo phân bố domain, difficulty, action/no-answer/typo/ambiguous/premise correction nếu field tồn tại.

## Ví dụ

Yêu cầu phù hợp: "validate this QA dataset." Thực hiện quy trình trên và báo rõ bằng chứng.

## Giới hạn và kiểm chứng

Không tự xóa hay sửa dataset. Không gọi similarity heuristic là duplicate chắc chắn. Kiểm chứng bằng scenario tương ứng trong
`docs/agent-skills/TEST_REPORT.md`; nếu có script, chạy cả fixture hợp lệ và input lỗi.
