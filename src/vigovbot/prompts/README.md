# Module `vigovbot.prompts`

## Trách nhiệm

Module định nghĩa system prompt và xây dựng message gửi tới Ollama trong giới hạn
context của model. Nội dung truy hồi được coi là dữ liệu, không phải chỉ dẫn.

## Đầu vào và đầu ra

`build_messages(question, hits, tokenizer, num_ctx, num_predict,
max_chunk_tokens)` nhận câu hỏi, các hit truy hồi và tokenizer tương thích Qwen.
Hàm trả về ba giá trị:

- danh sách message theo định dạng chat;
- danh sách nguồn thực tế được đưa vào context, kèm `included_text`;
- số token prompt ước tính.

## Thuật toán ngân sách context

Ngân sách khả dụng bằng `num_ctx - num_predict - 256`. Mỗi chunk được cắt tối đa
theo `max_chunk_tokens`, sau đó tìm nhị phân phần nội dung dài nhất còn vừa ngân
sách. Khi hit tiếp theo không thể thêm, quá trình dừng và không vượt context.

## Ràng buộc

`num_ctx` phải lớn hơn `num_predict + 256`; `max_chunk_tokens` phải dương. Câu hỏi
quá dài để chứa trong ngân sách phát sinh lỗi thay vì âm thầm cắt câu hỏi.

[Kiến trúc hệ thống](../../../docs/architecture.md) · [Module RAG](../rag/README.md)
