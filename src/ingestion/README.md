# Ingestion

`parse.py` điều phối PDF → trích xuất → làm sạch → chunking → lưu JSON.
`recovery.py` đọc từng trang, thử Markdown, dùng text gốc khi chuyển đổi thất bại,
và OCR trang ảnh. Trang OCR thất bại được liệt kê, không âm thầm bỏ qua.

`unified.py` phục vụ nhánh RAG: mở luồng từ thư mục/ZIP chứa chỉ mục và metadata đã tạo.
Hai luồng dùng chung thư mục module nhưng không đọc lại PDF khi truy vấn RAG.

## Đầu vào và đầu ra

| Nhánh | Đầu vào | Đầu ra |
| --- | --- | --- |
| PDF (`parse.py`, `recovery.py`) | File/thư mục PDF | JSON chunks và báo cáo đọc từng trang |
| Unified (`unified.py`) | Thư mục hoặc ZIP có hai file unified | Luồng nhị phân và định danh nguồn cho vector store |

Từ thư mục gốc, cài môi trường PDF bằng `pip install -r requirements.txt`.
Trên Colab dùng [parse_metadata.ipynb](../../ipynb/parse_metadata.ipynb).
Xem [bản đồ src](../README.md) để đi tới các bước sau.

## Các bước xử lý

1. Kiểm tra file tồn tại, đuôi `.pdf`, dung lượng hợp lệ và chữ ký `%PDF-`.
2. Đọc từng trang: chuyển text thành Markdown; nếu chuyển đổi thất bại thì dùng text gốc.
3. Trang ảnh không có text được OCR. Trang không có text, ảnh, nét vẽ hay annotation
   được coi là trắng; ảnh scan trắng vẫn đi qua OCR và có thể cần kiểm tra.
4. Chuẩn hóa xuống dòng, loại ký tự lỗi, token backtick rỗng và dòng bảng rỗng.
5. Chuyển nội dung sang [chunking](../chunking/README.md), rồi ghi JSON UTF-8.

PDF có mật khẩu hoặc không đọc được vẫn báo lỗi. Nếu một số trang OCR thất bại,
nội dung còn lại được lưu với danh sách trang thiếu. Không coi đây là tài liệu đầy đủ.

## Cấu hình

File [config.yaml](config.yaml) được tham chiếu từ `modules.ingestion` trong
[config gốc](../../config.yaml). Input/output chung nằm ở config gốc.

| Khóa | Ý nghĩa |
|---|---|
| `max_pdf_size_mb` | Giới hạn PDF, lớn hơn 0 và tối đa 100 MB |
| `reports_dir`, `review_dir` | Tên thư mục con khác nhau bên trong output |
| `recover_metadata` | Cho phép lưu tài liệu thiếu định danh để đối chiếu |
| `ocr.enabled` | Bật OCR trang ảnh |
| `ocr.language` | Mặc định `vie+eng` |
| `ocr.dpi` | Độ phân giải OCR, 72–600 |
| `ocr.full` | OCR toàn trang |
| `ocr.tessdata` | Thư mục traineddata; đường dẫn tương đối tính từ config module |

`tessdata: null` để PyMuPDF tự tìm dữ liệu Tesseract. Cần cài `vie.traineddata`
và `eng.traineddata` để OCR tiếng Việt/Anh. Thiếu OCR vẫn lưu các trang đọc được.

## Chạy và kết quả

Từ thư mục dự án: `python main.py` dùng input/output trong YAML.
`python main.py --config config.yaml --overwrite` xử lý lại kết quả cũ.
`python main.py Data/pdf --output-dir outputs/test --no-overwrite` ghi đè lựa chọn YAML.

Mỗi PDF sinh danh sách chunks JSON và báo cáo riêng. `success` là xử lý hoàn tất;
`partial_success`/`needs_review` nằm trong thư mục review. File thành công được bỏ qua
trừ khi bật overwrite; file lỗi được thử lại. Ctrl+C giữ file đã hoàn tất và ghi
`interrupted` cho file đang chạy. Không có checkpoint giữa trang.

API: `parse_pdf_to_hybrid_data(path, config_path='config.yaml')` trả về đường dẫn
JSON và số chunks. `output_dir` truyền trực tiếp có ưu tiên hơn YAML.
Các biến cũ `OUTPUT_DIR`, `MAX_PDF_SIZE_MB`, `OCR_LANGUAGE` trong `.env` không còn được đọc.

### Cấu trúc output

```text
outputs/metadata/
├── 1.000005.json           # danh sách chunks
├── review/                # kết quả cần xác minh
└── reports/               # báo cáo từng file, không dùng để embedding
```

Tên thư mục con có thể đổi trong YAML. Chạy cả thư mục sẽ giữ cấu trúc thư mục
con của nguồn. Mỗi JSON được ghi vào file tạm UUID rồi thay thế file đích,
giúp tránh file kết quả dở dang.

| Trạng thái báo cáo | Ý nghĩa |
|---|---|
| `success` | Hoàn tất; có thể đã dùng OCR hoặc fallback bảng |
| `partial_success` | Còn trang chưa đọc được |
| `needs_review` | Thiếu định danh hoặc dùng mã từ tên file cần xác minh |
| `failed` | Xử lý thất bại |
| `interrupted` | Nhận lệnh ngắt khi xử lý |
| `processing` | Chưa ghi nhận hoàn tất, có thể do tiến trình bị kill |

Báo cáo chứa phương pháp đọc từng trang, trang thiếu, cảnh báo và đường dẫn output.
Ưu tiên trạng thái báo cáo mới khi có JSON cũ từ lần chạy trước. `success` không
bảo đảm OCR đúng tuyệt đối. File lỗi/cần kiểm tra được thử lại khi chạy tiếp;
JSON cũ không có báo cáo có thể bị bỏ qua, cần `--overwrite` để xử lý lại.

## Đọc unified cho RAG

[unified.py](unified.py) được [vector store](../vectordb/README.md) gọi, không phải CLI riêng.

- `zip_member(archive, basename)`: tìm đúng một file theo tên cuối đường dẫn,
  chấp nhận thư mục con trong ZIP; báo lỗi nếu thiếu hoặc có nhiều bản trùng tên.
- `corpus_stream(source, basename)`: context manager mở file nhị phân từ thư mục
  hoặc ZIP; không giải nén theo đường dẫn của thành viên ZIP.
- `corpus_identity(source)`: lấy đường dẫn, kích thước, thời gian sửa; ZIP có thêm
  tên thành viên, CRC và dung lượng giải nén để phân biệt cache.

Hai tên file được dùng là `tthc_unified.index` và `tthc_unified_metadata.json`.
Nguồn được chọn bằng `data.unified_source` trong [rag_config.yaml](../../rag_config.yaml).
Module chỉ mở dữ liệu; kiểm tra số chiều/số dòng và chuyển JSON sang SQLite thuộc vector store.
Các ZIP chứa chunks cho worker embedding được xử lý riêng ở [embeddings](../embeddings/README.md).

[Quay lại tổng quan](../README.md)
