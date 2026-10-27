# Thay đổi hệ thống

## Tách image web CPU và QLoRA GPU - 2026-10-27

### Mục tiêu

Giảm dung lượng runtime Docker mặc định và tránh mang dependency CUDA,
training khi chỉ chạy Base/RAG qua Ollama.

### Thực hiện

- Tách target web CPU và target QLoRA GPU, config và profile Compose tương ứng.
- Sinh lock CPU bằng resolver và giữ volume model/cache hiện có.

### Kết quả

Đã hoàn tất. Image mặc định giảm từ 12,8 GB xuống 2,03 GB, không
chứa CUDA/PEFT/bitsandbytes; Base và RAG streaming đều trả `success` trên
container healthy. Image GPU 12,8 GB giữ riêng QLoRA và đã xác nhận RTX 4050,
CUDA 12.8, PEFT/bitsandbytes. Đã thu hồi 32,01 GB BuildKit cache, không xóa
image runtime hay volume model/cache. Toàn bộ 249 test, Ruff, compileall,
Compose default/GPU và `git diff --check` đều đạt; 22 test tùy chọn bị skip.

## Streaming phản hồi LLM trên web - 2026-10-27

### Mục tiêu

Hiển thị phản hồi dần theo quá trình sinh token thay vì chờ toàn bộ văn bản.

### Thực hiện

- Bổ sung luồng streaming từ provider qua API đến giao diện web.
- Giữ nguyên hợp đồng `/api/chat` cho evaluation và client hiện có.

### Kết quả

Đã triển khai streaming qua Ollama, OpenAI-compatible và Transformers cục bộ;
web hiển thị token ngay khi nhận. Đã kiểm chứng 249 test, Ruff, compileall,
`git diff --check`, build/recreate container và API `qwen-base` thật. Lần gọi đã warm
phát token đầu sau 0,300 giây, hoàn tất sau 0,486 giây với 4 sự kiện token;
22 test dependency tùy chọn bị skip. Chưa thao tác xác minh trên trình duyệt thật.

## Intent classifier cho routing - 2026-10-27

### Mục tiêu

Giảm lượt gọi Qwen chỉ để phân loại intent nhưng vẫn giữ khả năng xử lý
follow-up, mixed, ambiguous và rollback an toàn.

### Thực hiện

- Thêm backend `llm`, `fasttext`, `hybrid` và artifact FastText có metadata/hash.
- Thêm dữ liệu contract, lệnh train/evaluate, diagnostics và fallback về Qwen.

### Kết quả

Đã triển khai backend, CLI, artifact validation, Docker packaging và diagnostics;
backend mặc định vẫn là `llm`. Đã kiểm chứng model FastText thật và regression
offline; quality gate và API latency chưa được xác nhận vì chưa có dataset routing
độc lập đã gán nhãn.

## Đưa trực tiếp top 5 retrieval vào LLM - 2026-10-26

### Mục tiêu

Gỡ bước rerank khỏi luồng RAG online và đưa trực tiếp năm kết quả FAISS đứng đầu
vào prompt của LLM.

### Thực hiện

- Loại cấu hình và lời gọi reranker khỏi runtime RAG.
- Đồng bộ profile host/Docker, giao diện quan sát context và kiểm thử liên quan.

### Kết quả

Đã chuyển runtime sang FAISS top 5 trực tiếp và loại cấu hình/module reranker
online. Đã kiểm chứng 36 test routing, 9 test server, 1 test UI, toàn bộ 235 test,
schema hai profile, Ruff, compileall và `git diff --check`; 21 test dependency tùy
chọn bị skip. Chưa xác minh API/container hoặc chất lượng câu trả lời thực vì
Docker daemon không hoạt động và host thiếu FAISS/model runtime.

## Rút gọn evidence có cấu trúc vượt ngân sách - 2026-10-25

### Mục tiêu

Không loại toàn bộ bảng hoặc giá trị JSON chỉ vì vượt `max_chunk_tokens`; giữ
phần bằng chứng hợp lệ trong prompt mà không cắt hỏng cấu trúc.

### Thực hiện

- Rút gọn bảng Markdown/HTML theo hàng hoàn chỉnh và JSON theo field/phần tử.
- Không thay đổi scalar hoặc giá trị trong ô; giữ giới hạn từng chunk, tổng
  context và trace phần nội dung thực tế đã dùng.

### Kết quả

Đã kiểm chứng bằng 11 test evidence chuyên biệt, full suite 238 test, Ruff,
compileall và `git diff --check`; 21 test dependency tùy chọn bị skip. Chưa chạy
tokenizer Qwen thật hoặc API generation vì môi trường Python hiện thiếu
Transformers/FAISS.

## Tách ngân sách context cho routing - 2026-10-25

### Mục tiêu

Giảm chi phí context và giới hạn đầu ra của lần gọi routing mà không thay đổi
ngân sách sinh câu trả lời.

### Thực hiện

- Thêm `llm.routing_num_ctx` và `llm.routing_num_predict`.
- Dùng ngân sách riêng cho payload và kiểm tra context của routing.
- Kiểm chứng cấu hình, hành vi routing và regression.

### Kết quả

Đã triển khai và kiểm chứng bằng 36 test routing, full suite 234 test và Ruff.
Chưa đo latency thực tế vì máy hiện không có Ollama hoặc Docker runtime hoạt động.

## Chuẩn hóa hồ sơ vận hành - 2026-10-25

### Mục tiêu

Giữ tài liệu triển khai ngắn gọn và chỉ cập nhật khi chỉnh sửa quan trọng ảnh
hưởng hệ thống hoặc vận hành.

### Thực hiện

- Đổi điều kiện kích hoạt `vigovbot-task-journal`.
- Chuẩn hóa hồ sơ theo `Mục tiêu - Thực hiện - Kết quả`.
- Hợp nhất lịch sử cũ, loại yêu cầu báo cáo, dọn dẹp và chỉnh sửa nhỏ.

### Kết quả

Hoàn tất ngày 2026-10-25.


## 2026-10-27 — Truy xuất follow-up theo mã thủ tục

### Mục tiêu

Bỏ embedding khi follow-up có thủ tục và phần dữ liệu xác định.

### Thực hiện

Triển khai truy xuất SQLite, ngữ cảnh riêng theo model/hội thoại và fallback có giới hạn nguồn.

### Kết quả

Hoàn tất mã nguồn, kiểm tra hồi quy và phép đo cục bộ; chưa restart web đang chạy. Chi tiết tại `outputs/verification/follow-up/report.md`.


## 2026-10-27 — Hỏi lại theo metadata thủ tục

- **Mục tiêu:** Xác định đúng thủ tục và nội dung cần tra cứu trước khi trả lời.
- **Thực hiện:** Tích hợp danh sách thủ tục/section từ SQLite, lựa chọn nhiều lượt và context riêng theo model vào RAG/API/web.
- **Kết quả:** Hoàn tất mã nguồn; 123 test Python và 2 test JavaScript đạt, có HTTP thường → streaming giả lập và kiểm tra SQLite thực tế. Chưa restart backend hoặc xác minh model/trình duyệt thật.


## 2026-10-27 — Giữ thủ tục khi chọn dòng nội dung và hỏi nối tiếp

- **Mục tiêu:** Sửa lỗi sao chép “4. Cách thức nộp, thời hạn và phí” làm mất thủ tục đã xác định, và giữ mã cho câu hỏi hồ sơ tiếp theo.
- **Thực hiện:** Đối chiếu số kèm nhãn với danh sách hiện tại; xác nhận mã từ context truy hồi trước khi giải quyết câu nối tiếp; phục hồi danh sách qua lỗi không tìm thấy do parser cũ.
- **Kết quả:** 103 test Python liên quan và 2 test JavaScript đạt. Backend đã restart; Qwen thật qua API thường/streaming giữ mã 1.000894 khi chọn dòng phí rồi hỏi hồ sơ, lượt hồ sơ dùng procedure_direct/required_documents.


## 2026-10-27 — Chọn nguyên dòng thủ tục có mã và cấp thực hiện

- **Mục tiêu:** Không lặp danh sách thủ tục khi người dùng sao chép nguyên lựa chọn, gồm mã và cấp thực hiện.
- **Thực hiện:** Dùng chung nhãn hiển thị/đối chiếu lựa chọn; phân biệt metadata mô tả lựa chọn với mục tiêu hỏi, giữ mục tiêu đã có.
- **Kết quả:** 105 test Python liên quan và 2 test JavaScript đạt. Backend đã restart; API thật xác nhận dòng 5 chọn mã 1.000180 và dòng 1 chọn mã 2.000037, chuyển sang section_required, không gọi lại router.


## 2026-10-27 — Phân biệt hỏi danh sách thủ tục với chọn tên chính xác

- **Mục tiêu:** Câu “Các thủ tục cấp lại chứng chỉ kiểm định viên” phải đưa các biến thể để chọn thay vì tự chốt mã 2.000066.
- **Thực hiện:** Phát hiện yêu cầu danh sách/số nhiều, mở rộng tên khớp sang biến thể dài hơn trong catalog trước bước chọn section; giữ ưu tiên mã cụ thể và mục tiêu đã rõ.
- **Kết quả:** 106 test Python liên quan và 2 test JavaScript đạt. Backend đã restart; API thật trả procedure_required với năm ứng viên và more=true; chọn mục 2 chuyển section_required cho mã 1.000187.
