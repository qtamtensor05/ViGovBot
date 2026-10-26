# Sự cố hệ thống và vận hành

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
