# Lịch sử thay đổi hệ thống

## Tách image web CPU và QLoRA GPU - 2026-10-27

### Mục tiêu

Giảm dung lượng web thường ngày và chỉ mang CUDA khi chạy QLoRA cục bộ.

### Thực hiện

- Tách Docker target `web-ollama` dùng Torch CPU và `web-gpu` dùng CUDA.
- Tách config Base/RAG mặc định và service QLoRA thuộc profile `gpu`.
- Sinh lock CPU bằng resolver; giữ nguyên volume Ollama, Hugging Face và RAG.

### Kết quả

Image mặc định giảm 12,8 GB xuống 2,03 GB; Base/RAG streaming trả
`success`. Image GPU 12,8 GB xác nhận RTX 4050, CUDA 12.8, PEFT và
bitsandbytes. Đã thu hồi 32,01 GB BuildKit cache. 249 test, Ruff, compileall,
Compose default/GPU và `git diff --check` đạt; 22 test tùy chọn bị skip.

## Streaming phản hồi LLM trên web - 2026-10-27

### Mục tiêu

Giảm cảm giác chờ bằng cách hiển thị phản hồi ngay trong quá trình model sinh.

### Thực hiện

- Bổ sung callback token cho Ollama, OpenAI-compatible và Transformers cục bộ.
- Thêm `/api/chat/stream` dạng NDJSON và cập nhật từng thẻ model trên web.
- Giữ `/api/chat` và payload kết quả cuối cùng tương thích ngược.

### Kết quả

249 test, Ruff, compileall và `git diff --check` đạt; 22 test dependency tùy chọn
bị skip. Image web đã build, container healthy; API `qwen-base` thật phát 4 sự
kiện token, TTFT warm 0,300 giây và hoàn tất sau 0,486 giây. Chưa thao tác
xác minh trên trình duyệt thật.

## Intent classifier FastText/hybrid - 2026-10-27

### Mục tiêu

Giảm chi phí prompt routing bằng classifier CPU nhưng bảo toàn hợp đồng routing
nhiều lượt và khả năng rollback về Qwen.

### Thực hiện

- Thêm backend `llm|fasttext|hybrid`, confidence threshold, diagnostics và
  fallback an toàn khi artifact thiếu/sai hash hoặc cần rewrite/clarification.
- Thêm CLI train/evaluate, schema dataset chống group leakage, cấu hình FastText
  gọn có kiểm tra kích thước trên fixture, Docker builder stage và hướng dẫn.

### Kết quả

Docker build thành công; 62 test router/server/CLI, 5 test tài liệu/cấu hình,
Ruff, compileall và diff check đều đạt. Full suite chạy 269 test còn 7 lỗi nền
không thuộc thay đổi này và 7 skip. Chưa huấn luyện artifact thật trên dữ liệu
độc lập, chưa đạt quality gate và chưa đo API latency, nên giữ mặc định `llm`.

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


## 2026-10-27 — Follow-up truy xuất trực tiếp theo mã thủ tục

### Mục tiêu

Giảm thời gian truy xuất cho câu nối tiếp đã xác định thủ tục, giữ đúng nguồn.

### Thực hiện

Thêm lookup SQLite theo mã/phần, kiểm tra fingerprint corpus/chunk/lịch sử,
fallback trong đúng thủ tục khi thiếu phần hoặc vượt top_k. API/UI giữ ngữ cảnh
riêng theo model và xóa cùng hội thoại; trace phân biệt chiến lược truy xuất.

### Kết quả

Bộ Python mở rộng 128 test PASS; nhóm kiểm tra cuối bao gồm hai ca bảo vệ bổ sung.
Hai test JavaScript, Ruff, compileall và diff check PASS. Đo hai câu follow-up
trên corpus/model cục bộ: đúng mã và phần dữ liệu; retrieval warm giảm
1,182 → 0,067 s, cold tăng 1,170 → 1,456 s do nạp danh mục. Routing dao động,
chưa chứng minh giảm đều tổng latency. Chi tiết ở
`outputs/verification/follow-up/report.md`. Chưa restart web hoặc kiểm tra browser thật.


## 2026-10-27 — Hỏi lại thủ tục và section từ metadata

- **Mục tiêu:** Không tự trả lời một phần hoặc tự chọn thủ tục khi câu hỏi chưa rõ mục tiêu/đối tượng.
- **Thực hiện:** Thêm danh mục SQLite và bước hỏi lại trong RAG; ưu tiên mã/tên, hiển thị tối đa năm thủ tục và các section có thật. Giữ mục tiêu qua lựa chọn nhiều lượt, hỗ trợ context có chữ ký theo lịch sử/model và client cũ qua lịch sử; tích hợp API thường/streaming và reset UI. Giữ nguyên các chỉnh sửa follow-up đã có, không sửa corpus/model.
- **Kết quả:** 123 test Python routing/retrieval/API/prompt và 2 test JavaScript đạt; Ruff và compileall đạt. HTTP thường → streaming kiểm tra bằng model giả lập. SQLite thực tế có 6.192 thủ tục; mã tạm trú 1.004194 có sáu section. Chưa restart backend, chưa xác minh bằng model hoặc trình duyệt thật.


## 2026-10-27 — Sửa mất thủ tục khi chọn dòng và hỏi nối tiếp

- **Mục tiêu:** Giữ thủ tục đã xác định khi người dùng sao chép “4. Cách thức nộp, thời hạn và phí”, rồi hỏi “Hồ sơ, giấy tờ của thủ tục”.
- **Thực hiện:** Parser đối chiếu số kèm nhãn (kể cả dấu chấm escape Markdown), không nhầm mã thủ tục với số mục; phục hồi danh sách qua tối đa ba lượt lỗi không tìm thấy của parser cũ và không vượt qua câu đổi chủ đề. Pipeline xác minh fingerprint câu trả lời, corpus và chunk trước khi dùng lại mã cho câu hỏi phần nội dung, kể cả router chọn new_question. Giữ các ràng buộc context và phân loại ngoài phạm vi.
- **Kết quả:** 103 test Python liên quan, 2 test JavaScript, Ruff và compileall đạt. Restart web và /api/health trả ok. Qwen thật qua /api/chat → /api/chat/stream: danh sách kết hôn 1.000894 (1,37 giây), chọn dòng phí trả answer với cùng mã (15,77 giây), hỏi hồ sơ trả answer/required_documents bằng procedure_direct cùng mã (29,93 giây). Đây là kiểm chứng liên tục ngữ cảnh/truy hồi, không phải đánh giá đầy đủ tính đúng của nội dung pháp lý; chưa thao tác trình duyệt thật.


## 2026-10-27 — Sửa chọn nguyên dòng thủ tục có metadata

- **Mục tiêu:** Chọn được nguyên dòng thủ tục gồm tên, mã và cấp thực hiện thay vì lặp danh sách.
- **Thực hiện:** Dùng chung nhãn corpus cho render và parser; nhận tên, tên kèm mã, nguyên dòng có metadata với số thứ tự thường/escape Markdown. Kiểm tra số, mã, nhãn khớp; metadata mô tả không bị biến thành mục tiêu hỏi, giữ mục tiêu đã có.
- **Kết quả:** 105 test Python liên quan, 2 test JavaScript, Ruff/compileall đạt. Backend đã restart và health ok. API thật với câu “Thủ tục cấp lại chứng chỉ kiểm địng viên” trả đúng năm ứng viên; sao chép mục 5 chọn 1.000180 (0,56 giây), mục 1 chọn 2.000037 (0,41 giây), đều chuyển section_required với 0 lần gọi router. Chưa thao tác trình duyệt thật.


## 2026-10-27 — Hỏi danh sách không tự chọn tên khớp chính xác

- **Mục tiêu:** Nhận biết “Các thủ tục cấp lại chứng chỉ kiểm định viên” là yêu cầu chọn trong nhóm thủ tục, không tự chốt mã 2.000066.
- **Thực hiện:** Nhận diện yêu cầu danh sách/số nhiều; mở rộng tên khớp sang các biến thể dài hơn có cùng cụm tên trong catalog. Ưu tiên mã cụ thể khi được nêu, giữ tên đơn/ý hỏi rõ; không biến từ “tất cả các thủ tục” thành mục tiêu tổng quan sau khi chọn.
- **Kết quả:** 106 test Python liên quan và 2 test JavaScript đạt; Ruff/compileall đạt. Backend đã restart, health ok. API thật trả procedure_required với năm mã 2.000066, 1.000187, 1.000180, 1.000183, 2.000037 và more=true (3,23 giây); sao chép mục 2 chuyển section_required đúng mã 1.000187 (0,51 giây). Chưa thao tác trình duyệt thật.


## 2026-10-27 — Streaming early exit cho LLM router

- **Mục tiêu:** Trả sớm nhánh ngoài phạm vi/làm rõ trên API streaming.
- **Thực hiện:** Đọc prefix scope/relation qua nhiều chunk, dừng sinh router khi nhãn kết thúc được xác định; đóng HTTP stream hoặc dừng/join worker Transformers. Giữ đối chiếu metadata trước câu làm rõ, dùng câu hỏi mặc định khi bỏ phần clarification của JSON. Gửi token kết quả trước model_result; API thường vẫn chờ JSON đầy đủ.
- **Kết quả:** 90 test routing/provider/server/clarification/documentation đạt; Ruff và compileall đạt. Test provider giả lập xác nhận không đọc phần đuôi JSON và đóng kết nối. Chưa kiểm chứng model thật hoặc hủy sinh trên GPU; Docker daemon chưa chạy.
