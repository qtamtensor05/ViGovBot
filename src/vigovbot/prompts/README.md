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

Ngân sách khả dụng bằng `num_ctx - num_predict - 256`, gồm system prompt,
lịch sử, JSON nguồn, metadata, câu hỏi và lời nhắc cuối. `evidence.py` đóng gói
metadata động, bỏ giá trị rỗng nhưng giữ `false`/`0`, không gộp cấp document/chunk.
`retrieval.max_metadata_tokens` (mặc định 256 mỗi nguồn) giữ nguyên từng trường
còn vừa ngân sách; ID/phạm vi/phiên bản được ưu tiên bằng heuristic và không
bị cắt thành giá trị khác. Trường bị bỏ được báo bằng `metadata_omitted`.

Văn bản thường có thể lấy prefix theo ranh giới dòng/từ và đánh dấu
`content_truncated`. Bảng Markdown/HTML vượt `max_chunk_tokens` hoặc tổng budget
được rút gọn theo hàng hoàn chỉnh; header được giữ cùng hàng dữ liệu, không cắt
hay sửa giá trị trong ô. JSON object/list được thu nhỏ theo trường hoặc phần tử
hoàn chỉnh rồi serialize lại, không cắt hoặc thay đổi scalar. Nội dung
rút gọn luôn có `content_truncated=true`. Nếu không tạo được projection có cấu
trúc và có dữ liệu, khối mới bị bỏ để thử nguồn sau. `omitted_sources` trong
prompt báo số nguồn chưa đưa vào.

Nguồn được serialize thành JSON, escape ký tự góc để tránh chèn delimiter/chat
token trực tiếp. Đây là bảo vệ cấu trúc, không bảo đảm model miễn nhiễm injection.
Nguồn không có ID không được tự cấp ID tài liệu hay dùng làm citation có ID.
Trace `included_text`/`included_metadata` là dữ liệu thật đã đóng gói; panel Web
hiện vẫn hiển thị toàn văn kết quả rerank, có thể dài hơn phần model nhận.

## Ràng buộc

`num_ctx` phải lớn hơn `num_predict + 256`; `max_chunk_tokens` phải dương. Câu hỏi
quá dài để chứa trong ngân sách phát sinh lỗi thay vì âm thầm cắt câu hỏi.
Core prompt dùng quy tắc bằng chứng tổng quát; router, thông báo nghiệp vụ và
format hồ sơ/trình tự/phí vẫn thuộc ứng dụng ViGovBot. Formatter nhận structured
content; ingestion/encoder hiện yêu cầu `text_content` là chuỗi được chuẩn hóa.

[Kiến trúc hệ thống](../../../docs/architecture/architecture.md) · [Module RAG](../rag/README.md)
