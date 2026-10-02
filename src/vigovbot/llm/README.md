# Module `vigovbot.llm`

## Trách nhiệm

Module là adapter HTTP đồng bộ cho Ollama. Nó kiểm tra model, gửi yêu cầu chat và
giải phóng model khỏi bộ nhớ; không chứa logic retrieval hoặc prompt.

## Giao diện và dữ liệu

| Hàm | Đầu vào | Đầu ra |
|---|---|---|
| `check_model()` | Base URL và tên model | Metadata model từ `/api/tags` |
| `ollama_answer()` | Message và inference settings | Câu trả lời, payload nguyên bản, thời gian sinh |
| `unload_model()` | Base URL và tên model | Không có; gửi `keep_alive: 0` |

`ollama_answer()` chuyển `temperature`, `num_ctx`, `num_predict`, `seed`,
`keep_alive` và timeout từ cấu hình RAG sang API `/api/chat` với `stream: false`.

## Ràng buộc và lỗi

HTTP status lỗi được chuyển thành exception qua `raise_for_status()`. Model chưa
được cài, phản hồi có trường `error` hoặc nội dung trả lời rỗng đều bị từ chối.
Module không tự cài hoặc tự khởi động Ollama.

[Kiến trúc hệ thống](../../../docs/architecture.md) · [Module RAG](../rag/README.md)
