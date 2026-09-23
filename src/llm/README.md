# LLM — gọi Qwen qua Ollama

[llm_client.py](llm_client.py) giao tiếp HTTP với dịch vụ Ollama.
Mô hình mặc định là `qwen2.5:7b`, giống notebook baseline. Module không tự truy hồi
tài liệu; nhận `messages` đã được [prompts](../prompts/README.md) xây dựng.

## Các hàm và quy trình

| Hàm | Công việc |
| --- | --- |
| `check_model(base_url, model)` | Gọi `/api/tags`, tìm model, trả thông tin gồm digest nếu có |
| `ollama_answer(messages, settings)` | Gọi `/api/chat` với `stream=False`, trả câu trả lời, JSON gốc và thời gian gọi |
| `unload_model(base_url, model)` | Gọi `/api/generate` với `keep_alive=0` để yêu cầu dỡ mô hình |

Trước inference, pipeline kiểm tra model và ghi digest vào manifest.
Mỗi câu hỏi được gửi với system/user messages, không giữ hội thoại giữa các câu.
Sau inference, pipeline yêu cầu dỡ Qwen để dành tài nguyên cho BERTScore.

## Cấu hình

Nhóm `llm` trong [rag_config.yaml](../../rag_config.yaml):

```yaml
llm:
  model: qwen2.5:7b
  ollama_url: http://localhost:11434
  temperature: 0.0
  num_ctx: 8192
  num_predict: 512
  seed: 42
  timeout: 300
  keep_alive: 10m
```

`temperature`, `num_ctx`, `num_predict`, `seed` được chuyển vào `options` của request;
`timeout` là thời gian chờ HTTP. Các khóa tokenizer do pipeline/prompts sử dụng,
không gửi tới Ollama.

## Chuẩn bị dịch vụ

Trên máy cá nhân, cài Ollama rồi chạy dịch vụ và tải mô hình:

```sh
ollama serve
ollama pull qwen2.5:7b
```

Nếu dịch vụ đã chạy, không cần mở thêm `ollama serve`. Trên Colab,
[utils/colab_runtime.py](../utils/README.md) chuẩn bị dịch vụ trước khi chạy pipeline.
Ollama quản lý việc dùng GPU/CPU; LLM client không ấn định lượng VRAM hay số lớp GPU.

## Lỗi và phạm vi

Lỗi HTTP, timeout, model không có hoặc câu trả lời rỗng được báo lên caller.
Không tự retry trong một request. [Evaluation runner](../evaluation/README.md)
ghi lỗi từng câu và thử lại câu chưa thành công khi chạy lại.
Hiện chưa có provider khác, streaming output hoặc kiểm chứng factuality sau sinh.

[Quay lại tổng quan](../README.md)
