# Prompts — xây dựng ngữ cảnh cho Qwen

[prompt_templates.py](prompt_templates.py) chứa `SYSTEM_PROMPT` và
`build_messages()`. Module nhận câu hỏi, danh sách đoạn đã truy hồi và tokenizer Qwen;
không truy vấn DB hay gọi LLM.

## Luồng xử lý

1. Tạo system message yêu cầu trả lời tiếng Việt, bám tài liệu và nói rõ khi thiếu thông tin.
2. Ghép câu hỏi với các đoạn tham khảo theo thứ tự truy hồi, kèm `chunk_id` và mã thủ tục.
3. Cắt mỗi đoạn theo `max_chunk_tokens`.
4. Đếm token bằng `apply_chat_template()` của tokenizer Qwen; rút bớt đoạn để vừa ngân sách tổng.
5. Trả `(messages, used, token_count)` cho [LLM client](../llm/README.md).

Ngân sách prompt: `num_ctx - num_predict - 256`. Phần 256 token dự phòng khác biệt
template; số token này là ước tính bằng tokenizer, không phải số token thực Ollama báo lại.
Nếu riêng câu hỏi và system prompt đã quá ngân sách, hàm báo lỗi.

## Cấu hình và dữ liệu ghi nhận

| Khóa trong [rag_config.yaml](../../rag_config.yaml) | Mặc định | Ý nghĩa |
| --- | --- | --- |
| `llm.tokenizer` | `Qwen/Qwen2.5-7B-Instruct` | Tokenizer tương ứng Qwen |
| `llm.tokenizer_revision` | `null` | Có thể cố định phiên bản |
| `llm.num_ctx` | 8192 | Ngữ cảnh Ollama |
| `llm.num_predict` | 512 | Token tối đa cho câu trả lời |
| `retrieval.max_chunk_tokens` | 1200 | Giới hạn mỗi đoạn tham khảo |

`used` chứa nguồn, điểm và `included_text` thực sự đưa vào prompt. Pipeline lưu nó
trong `context_used` của prediction để phân biệt đoạn tìm được với đoạn đã gửi cho mô hình.
Một số kết quả top-k có thể không còn chỗ trong prompt.

## Quy tắc hiện tại

Nội dung tài liệu được trình bày như dữ liệu tham khảo, không phải chỉ dẫn thực thi.
Không thêm `ground_truth` hoặc `rag_context` có sẵn của bộ test.
System prompt yêu cầu không bịa số liệu, không thêm lời chào/danh sách nguồn vì nguồn
được lưu riêng. Đây là hướng dẫn mô hình, chưa có bước kiểm chứng câu trả lời tự động.
Không có lịch sử hội thoại, nén ngữ cảnh bằng mô hình khác hay truy hồi section cha.

Prompt là một phần định danh lượt chạy do [bộ điều phối RAG](../rag/README.md)
ghi trong manifest. Thay đổi prompt khiến cấu hình không còn khớp lượt đánh giá trước.

[Kiến trúc tổng thể](../README.md)
