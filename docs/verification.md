# Báo cáo kiểm chứng dự án ngày 27/09/2026

Đây là báo cáo tại một thời điểm, không phải trạng thái CI hiện thời hoặc chứng
nhận an toàn. Môi trường thực hiện: Windows x64, Python 3.14. Phạm vi kiểm chứng
gồm mã nguồn và khả năng chạy pipeline trong điều kiện kiểm thử.

## Phạm vi thay đổi

- Package `vigovbot`, CLI thống nhất, lớp tương thích `src.*` và script cũ.
- Cấu hình mẫu, dependency extras, lock theo nhóm, CI và tài liệu quản lý công việc.
- Hợp đồng pack/corpus độc lập, checksum nội dung và revision BGE-M3 bất biến.
- Tách `ask`/`prepare` khỏi yêu cầu bộ test; giữ luồng đánh giá/resume/report.
- Khóa ghi artifact/cache/prediction, manifest ghi cuối và kiểm tra cache hỏng.
- UTF-8 cho CLI Windows; giữ cảnh báo trích xuất PDF khi bổ sung cảnh báo chunking.
- Bộ cài Ollama dùng đường dẫn executable đã phân giải, file tạm riêng và
  kiểm tra tên model/URL; không dùng shell để nội suy tham số.
- Chuyển dữ liệu mẫu sang `examples/`, bảo toàn nội dung 9 file; 4 notebook
  được sinh từ generator, không chứa output và sinh lại cho cùng nội dung.
- LICENSE ghi rõ chưa cấp quyền sử dụng lại, theo lựa chọn của chủ dự án.

## Kết quả kiểm chứng

| Kiểm tra | Kết quả |
|---|---|
| Bộ test offline | 56/56 đạt trong môi trường hiện tại; chạy bằng lệnh mặc định, không cần `-X utf8` |
| Cài test lock vào venv tạm độc lập | Thành công; `pip check`, 56/56 test và demo offline đều đạt |
| `pip check` | Không phát hiện dependency không thỏa mãn |
| Ruff lint và format | Đạt |
| Ruff security (`--select S src/vigovbot`) | Đạt; hai vị trí subprocess có giải thích ngoại lệ S603 ngay trong mã |
| Wheel build/install ngoài checkout | Đạt; cấu hình mặc định đóng gói và help của cả bốn nhóm CLI hoạt động |
| Điểm chạy tương thích | `main.py`, `main.py rag` và import `src.*` được kiểm tra trong bộ test |
| Import runtime thật | SentenceTransformers, Torch, Transformers, FAISS và PyMuPDF4LLM nạp được |
| PDF thật dạng text | Tạo PDF trong thư mục tạm, chạy extraction/chunking thật: thành công, 1 chunk |
| Demo offline | Thành công: 2 chunk, truy hồi nguồn `1.000005` bằng vector tổng hợp |
| Notebook generator | 4 notebook sinh ổn định, code compile được, output rỗng |
| Dữ liệu mẫu sau di chuyển | Nội dung 9 file khớp bản Git, khác biệt LF/CRLF được chuẩn hóa khi so sánh |
| Liên kết tài liệu local | 30 file tài liệu được kiểm tra, không có liên kết nội bộ bị thiếu |

Các test bao phủ checksum sai, metadata/vector không khớp, revision khác nhau,
manifest thiếu, corpus ZIP/thư mục, ánh xạ FAISS–SQLite, cache hỏng, nguồn corpus
đổi dù giữ nguyên size/mtime, rollback ghi lỗi, khóa ghi, UTF-8, giải phóng tài
nguyên khi inference lỗi, prompt budget, không rò rỉ đáp án, resume và report.
Ingestion được kiểm tra chữ ký/kích thước PDF, OCR không đọc được, review routing,
metadata recovery, bảo toàn bảng/nội dung và giữ file cũ khi ghi JSON thất bại.

## Giới hạn kiểm chứng

- Chưa chạy suy luận Qwen/BGE-M3 thật hoặc benchmark đầy đủ trên corpus của dự án.
  Encoder/HTTP được mô phỏng trong test; không suy ra chất lượng câu trả lời từ số test đạt.
- Chưa chạy GPU/Colab, OCR Tesseract thật trên bản scan hoặc các job CI Linux/GitHub.
- Chưa thực hiện kiểm toán dependency theo cơ sở dữ liệu CVE hoặc kiểm thử xâm nhập.
  Ruff security là kiểm tra mã tĩnh, không thay thế các bước đó.
- Checksum không xác thực tác giả; FAISS phải đến từ nguồn tin cậy. File lock
  không thay thế khóa phân tán giữa nhiều máy/phiên Colab qua Google Drive.
- Ollama installer/model weights và driver nằm ngoài lock Python. Colab helper
  tải installer HTTPS từ nguồn chính thức; chưa khóa checksum phiên bản installer.
- Notebook baseline lịch sử trong `ipynb/base/` được giữ nguyên, không thuộc bốn
  notebook do generator mới quản lý.

## Quy trình tái kiểm chứng

Theo [environments.md](environments.md). Corpus cũ cần làm theo
[migration.md](migration.md). Kết quả thí nghiệm cũ được giữ nguyên; phiên bản
pipeline mới dùng thư mục output mới, không tự sửa hoặc xóa corpus trong `Data/`.
