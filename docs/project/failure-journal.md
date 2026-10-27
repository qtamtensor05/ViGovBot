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
