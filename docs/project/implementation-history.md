# Lịch sử thay đổi hệ thống

## Đưa trực tiếp top 5 retrieval vào LLM - 2026-10-26

### Mục tiêu

Loại chi phí và tác động xếp hạng của reranker khỏi luồng RAG online để thử
nghiệm trực tiếp năm kết quả FAISS đầu tiên trong prompt LLM.

### Thực hiện

- Đổi hai profile host/Docker sang `retrieval.top_k: 5` và bỏ cấu hình reranker.
- Bỏ module reranker online; pipeline truy hồi trực tiếp top 5 cho cả truy vấn
  đơn và hợp nhất sub-query.
- Đồng bộ trace cấu hình, panel nguồn, hướng dẫn vận hành và kiểm thử regression.
- Giữ công cụ rerank artifact ngoại tuyến trong evaluation, không tham gia luồng
  trả lời chatbot.

### Kết quả

36 test routing, 9 test server, 1 test UI, toàn bộ 235 test, schema hai profile,
Ruff, compileall và `git diff --check` đạt; 21 test dependency tùy chọn bị skip.
Chưa xác minh API/container hoặc chất lượng câu trả lời thực vì Docker daemon
không hoạt động và host thiếu FAISS/model runtime.

## Rút gọn evidence có cấu trúc vượt ngân sách - 2026-10-25

### Mục tiêu

Tránh `abstain` giả khi các hit đầu là bảng hoặc JSON có bằng chứng nhưng vượt
`max_chunk_tokens`.

### Thực hiện

- Chiếu bảng Markdown/HTML theo hàng hoàn chỉnh và JSON theo field/phần tử.
- Giữ nguyên scalar và giá trị ô; chỉ dùng projection có dữ liệu và còn vừa cả
  giới hạn chunk lẫn tổng prompt.
- Cập nhật test hồi quy và hợp đồng module prompt.

### Kết quả

11 test evidence chuyên biệt, full suite 238 test, Ruff, compileall và
`git diff --check` đạt; 21 test dependency tùy chọn bị skip. Chưa xác minh bằng
tokenizer Qwen thật hoặc API generation do thiếu Transformers/FAISS.

## Tách ngân sách context cho routing - 2026-10-25

### Mục tiêu

Giảm context và giới hạn đầu ra của routing mà không thu hẹp ngân sách sinh câu
trả lời.

### Thực hiện

- Thêm `routing_num_ctx=4096` và `routing_num_predict=128` vào schema và hai
  profile RAG.
- Áp dụng ngân sách riêng cho request, kiểm tra prompt và routing retry.
- Giữ `num_ctx=8192` và `num_predict=512` cho generation.

### Kết quả

36 test routing, full suite 234 test và Ruff đạt. Chưa đo latency A/B vì không có
Ollama hoặc Docker runtime hoạt động.

## Chuẩn hóa cấu trúc repository và CLI - 2026-10-15 đến 2026-10-18

### Mục tiêu

Loại bỏ package song song và thống nhất đường dẫn sử dụng công khai.

### Thực hiện

- Chuyển source về `src/vigovbot/`.
- Hợp nhất training tại `src/vigovbot/training/` và evaluation tại
  `src/vigovbot/evaluation/`.
- Thống nhất CLI `vigov`, cấu hình theo miền và tài liệu theo nhóm trong `docs/`.

### Kết quả

Cấu trúc canonical, package discovery, CLI và kiểm tra tài liệu đã hoạt động trên
checkout sạch; wrapper và cây package cũ không còn là điểm triển khai chính.

## QLoRA local-first và tích hợp Web - 2026-10-14 đến 2026-10-16

### Mục tiêu

Huấn luyện, đánh giá và chạy QLoRA trên GPU mà không thay thế Base/RAG.

### Thực hiện

- Hoàn thiện masking assistant-only, resume gate, profile GPU và cấu hình adapter.
- Tích hợp lựa chọn `base`, `rag`, `qlora` vào Web với lịch sử tách biệt.
- Dùng checkpoint validation tốt nhất `checkpoint-1100` cho adapter hiện tại.

### Kết quả

QLoRA chạy cục bộ trên RTX 4050 với Transformers 4.57.3; Base/RAG vẫn được giữ
và QLoRA-only không được xem là nguồn căn cứ cho thủ tục chưa có trong SFT.

## Docker runtime và cache bền vững - 2026-10-16 đến 2026-10-25

### Mục tiêu

Vận hành Web/Ollama trên Docker GPU mà không tải lại dependency và model sau mỗi
chỉnh sửa source.

### Thực hiện

- Tách lớp dependency CUDA khỏi source thay đổi thường xuyên.
- Dùng volume cho Hugging Face, Ollama và RAG; bind mount source/config cần thiết.
- Bổ sung healthcheck, preflight và lệnh `vigov doctor`.

### Kết quả

Stack Docker CUDA đã healthy; Qwen2.5:7B và RAG cache được tái sử dụng;
`/api/chat` và CLI trả kết quả có nguồn từ corpus. Thay đổi source/config thông
thường chỉ cần khởi động lại Web.

## Evaluation v2 và Golden datasets - 2026-10-17 đến 2026-10-24

### Mục tiêu

Tách inference khỏi scoring và giữ provenance cho mọi kết quả đánh giá.

### Thực hiện

- Tách prediction, offline scoring, judge và export thành các bước có thể resume.
- Bổ sung fingerprint, schema kết quả, trace retrieval/generation và trạng thái
  metric chưa có.
- Chuyển Golden sang SFT train/validation, giữ Unicode, ID và chống leakage.

### Kết quả

Evaluation v2 hỗ trợ resume từ prediction cache và không giả lập metric thiếu;
Golden SFT có 2.200 mẫu train, 550 mẫu validation, không trùng ID/conversation.

## Cứng hóa RAG và retrieval - 2026-10-23 đến 2026-10-25

### Mục tiêu

Trả đúng thủ tục, đúng loại thông tin và giữ câu trả lời có căn cứ.

### Thực hiện

- Thêm exact lookup theo mã và tên thủ tục.
- Ưu tiên section theo ý định, rerank Top-20 xuống Top-3 bằng MiniLM.
- Thêm format policy theo loại câu hỏi và fallback an toàn cho output phụ lỗi.

### Kết quả

Truy vấn mã `1.116222` trả đúng số quyết định; bộ 18 câu theo tên thủ tục đạt
top-1 và top-3 đúng 18/18; API container đã xác nhận luồng retrieval-rerank.

## Chuẩn hóa hồ sơ vận hành - 2026-10-25

### Mục tiêu

Chỉ lưu thay đổi quan trọng liên quan hệ thống hoặc vận hành.

### Thực hiện

- Đổi quy định kích hoạt skill nhật ký.
- Hợp nhất yêu cầu, lịch sử, trạng thái và sự cố cũ theo mốc hệ thống.
- Loại nội dung báo cáo, dọn dẹp, kiểm tra và chỉnh sửa nhỏ.

### Kết quả

Hồ sơ dùng thống nhất ba phần `Mục tiêu - Thực hiện - Kết quả` và không còn cập
nhật theo mọi task nhiều bước.
