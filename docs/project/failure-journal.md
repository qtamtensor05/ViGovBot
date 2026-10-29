# Sự cố hệ thống và vận hành

## Rebuild image CUDA khi chỉ thay đổi source bind mount - 2026-10-27

### Mục tiêu

Tránh build lại dependency nặng và phát sinh cache khi chỉ sửa source/config.

### Thực hiện

- Xác định `src` và `configs` đã bind mount, nên chỉ cần restart web.
- Tách image CPU mặc định khỏi image QLoRA GPU và dọn BuildKit cache dư.

### Kết quả

Thay đổi source/config hằng ngày dùng `docker compose restart web`; image GPU
chỉ build theo profile khi cần. Đã thu hồi 32,01 GB cache mà không xóa volume.

## FastText không có wheel Python 3.12 trong image slim - 2026-10-27

### Mục tiêu

Đóng gói intent classifier CPU mà không đưa toolchain biên dịch vào image runtime.

### Thực hiện

Build đầu tiên thất bại vì `fasttext==0.9.3` cần C++17 nhưng image
`python:3.12-slim` không có compiler. Chuyển bước tạo wheel sang Docker builder
stage có `g++`, sau đó chỉ sao chép wheel vào stage runtime.

### Kết quả

Đã xác định nguyên nhân; kết quả build lại được ghi trong mốc triển khai tương ứng.

## QLoRA/RAG trả lỗi khi output phụ không hợp lệ - 2026-10-23

### Mục tiêu

Không để lỗi decomposition hoặc citation làm hỏng toàn bộ request hợp lệ.

### Thực hiện

- Fallback về truy vấn gốc khi decomposition không phải JSON hợp lệ.
- Chỉ loại citation sai sau retry nếu nội dung câu trả lời còn hợp lệ.
- Giới hạn schema cho lượt repair cuối khi output bị cắt.

### Kết quả

Các request tiếp tục chạy với diagnostics rõ ràng; lỗi phụ không còn tự động biến
thành HTTP 502 cho toàn bộ câu trả lời.

## Semantic retrieval làm mất mã thủ tục chính xác - 2026-10-23

### Mục tiêu

Không để tìm kiếm ngữ nghĩa loại tài liệu có mã thủ tục được nêu rõ.

### Thực hiện

- Thêm exact lookup theo `source_code` và expression index trong cache SQLite.
- Ưu tiên section theo ý định trước khi cắt top-k.

### Kết quả

Mã `1.116222` trả đúng tài liệu và số quyết định; mã không tồn tại không rơi sang
mã gần giống.

## Reranker loại metadata đúng - 2026-10-24

### Mục tiêu

Giữ chunk trả lời trực tiếp sau bước rerank.

### Thực hiện

- Bổ sung intent `metadata_identity`.
- Chuẩn hóa Unicode và xếp section ưu tiên trước điểm cross-encoder.

### Kết quả

MiniLM vẫn xếp hạng trong từng nhóm; API trả đúng metadata và giữ luồng Top-20
đến Top-3.

## Môi trường host thiếu dependency RAG/evaluation - còn hiệu lực

### Mục tiêu

Không nhầm lỗi môi trường host với lỗi hệ thống.

### Thực hiện

- Chạy test phụ thuộc FAISS/model trong container hoặc môi trường đã cài extras.
- Ghi `SKIPPED` hoặc `NOT VERIFIED` khi dependency không có; không tự cài hoặc
  tải model ngoài phạm vi.

### Kết quả

Python host tối thiểu không được dùng làm bằng chứng runtime RAG; Docker là môi
trường kiểm chứng hiện có cho FAISS, CUDA và model.


## 2026-10-29 — Nhầm không cần menu với không tìm được thủ tục

- **Mục tiêu:** Tránh mất bằng chứng khi đã nhận diện được thủ tục.
- **Thực hiện:** Tách xác định mã khỏi inspect: None có thể nghĩa là đã biết một thủ tục và mục cần hỏi. Thêm hồi quy tên router thiếu tiền tố và kiểm tra giữ đúng mã/section trên API thật.
- **Kết quả:** Hai câu kết hôn trước sửa báo no_context dù truy xuất trực tiếp đúng; sau sửa trả 1 đoạn phí và 4 đoạn pháp lý cho 1.000894. Trạng thái hội thoại gây trả 1.010998 chưa tái hiện; không quy lỗi đó cho nguyên nhân này khi chưa có trace.

## 2026-10-29 — PhoBERT không cung cấp liên kết section–thủ tục

- **Mục tiêu:** Không ghép nhầm mục nội dung khi một câu chứa nhiều thủ tục.
- **Thực hiện:** Giữ head section toàn câu đúng hợp đồng checkpoint; không suy diễn union nhãn cho từng thủ tục. Khi mix được dự đoán hoặc không xác định được liên kết, yêu cầu hỏi riêng/chọn thủ tục. `Kết quả thực hiện` tìm trên toàn bộ section của đúng mã vì corpus không có taxonomy riêng.
- **Kết quả:** Tích hợp đúng checkpoint và fail closed khi thiếu model. Ca “Hồ sơ hộ chiếu và lệ phí đăng ký kết hôn” cho thấy head mix có thể dự đoán sai; đây là giới hạn model cần đánh giá/cải thiện bằng dữ liệu, không che bằng từ khóa hay fallback Qwen.

## 2026-10-29 — Section rỗng bị hiểu thành phải mở menu

- **Mục tiêu:** Không nhầm dự đoán đa nhãn dưới ngưỡng với câu hỏi chưa có mục tiêu.
- **Thực hiện:** Phân biệt danh tính thủ tục trần với câu hỏi cụ thể; trường hợp cụ thể tìm toàn bộ section của đúng mã, không tự gán nhãn bằng từ khóa.
- **Kết quả:** Câu hỏi đối tượng thực hiện của 3.000622 trước sửa dừng ở `section_required`; sau sửa đi `rag_search` và trả đúng chunk golden `metadata_identity_1_p1`.

## 2026-10-29 — Taxonomy router chi tiết hơn taxonomy corpus

- **Mục tiêu:** Không để nhiều nhãn PhoBERT cùng lọc vào `submission_deadline_fee` hoặc `RESULT` phải tìm toàn thủ tục.
- **Thực hiện:** Đưa taxonomy chi tiết vào chunking và routing; bảng thiếu cột chuẩn không bị tách đoán. Giữ fallback đọc artifact cũ đến khi corpus được rebuild.
- **Kết quả:** Mẫu 3.000622 chứng minh bốn section mới giữ nội dung nguồn. Lợi ích giảm token/hallucination chưa được xác nhận vì index vận hành vẫn là revision legacy.

## 2026-10-29 — Catalog override bỏ qua confidence phạm vi

- **Mục tiêu:** Tránh đổi mọi `OUT_OF_SCOPE` có catalog match thành trong phạm vi.
- **Thực hiện:** Arbitration theo xác suất; `P(OUT)≥0,85` giữ nguyên, chỉ band `[0,50; 0,85)` được override và luôn ghi trace.
- **Kết quả:** Loại bỏ override boolean. Chính sách có thể làm câu tên thủ tục trần bị từ chối nếu checkpoint quá tự tin sai; cần benchmark calibration thay vì che regression.

## 2026-10-29 — Hybrid raw score tự gán sai thủ tục hẹp

- **Mục tiêu:** Không tự gán thủ tục chỉ vì Top 1 hybrid vượt ngưỡng chưa calibration.
- **Thực hiện:** Candidate có qualifier thiếu bị phạt; hybrid chỉ mở menu khi đủ score và margin, không retrieval. Curated alias duy nhất mới được xác nhận trực tiếp.
- **Kết quả:** Trước phòng thủ, “đổi bằng lái xe máy” xếp 3.000351 người nước ngoài hạng 1 với 0,824278 còn mã tổng quát 1.115978 hạng 6. Sau bổ sung alias, API chọn đúng 1.115978; không tuyên bố các ngưỡng đã calibration.
