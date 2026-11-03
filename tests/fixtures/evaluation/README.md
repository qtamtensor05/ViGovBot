# QLoRA + RAG regression cases

Manifest này liệt kê các `test_id` phải chấm lại sau khi sửa luồng RAG. Nguồn
phát hiện là `predictions.jsonl` của hai run canonical trong `result_final`; file
không sao chép toàn bộ dataset hay context truy xuất.

## Phạm vi

- Tổng case duy nhất: 107
- P0: 100
- P1: 7
- `selection_intent_loss`: 97
- `generation_truncated_at_length`: 3
- `answer_action_with_missing_evidence`: 13

Một case có thể thuộc nhiều loại lỗi nên tổng theo loại lớn hơn số case duy nhất.

## Tiêu chí chọn

- `selection_intent_loss`: lượt follow-up chọn thủ tục nhưng output trả metadata
  thay vì ý định gốc.
- `generation_truncated_at_length`: provider kết thúc bằng
  `finish_reason=length`.
- `answer_action_with_missing_evidence`: action là `answer` nhưng nội dung nói
  không có thông tin.

Không đưa toàn bộ output ngắn vào manifest vì câu trả lời ngắn có thể đúng với
câu hỏi phí, thời hạn hoặc cấp thực hiện.

## Cách sử dụng

Sau khi sửa RAG, chọn lại các `test_id` trong
`qlora_rag_regression_cases.jsonl`, chạy inference và kiểm tra toàn bộ
`rerun_assertions` của từng case. Kết quả mới phải được chấm riêng theo cohort;
không thay metric thiếu bằng 0.
