# Xử lý dữ liệu

Pipeline hiện tại chuyển PDF thủ tục hành chính thành chunks JSON để dùng ở bước
embedding và truy xuất RAG. Pipeline này chưa tạo embedding hay lập vector index.

```text
PDF → ingestion (Markdown/text/OCR) → làm sạch → chunking → JSON + báo cáo
```

- [Ingestion](ingestion/README.md): kiểm tra PDF, đọc từng trang, OCR và lưu kết quả.
- [Chunking](chunking/README.md): nhận diện section, chia đoạn và gắn metadata.

## Cấu hình

```text
config.yaml                  # input/output, overwrite, Colab, đường dẫn config module
src/ingestion/config.yaml    # giới hạn PDF, OCR, review/reports
src/chunking/config.yaml     # kích thước chunk, overlap, từ khóa phân loại
```

[Config gốc](../config.yaml) được đọc và kiểm tra bởi `configuration.py`.
Đường dẫn tương đối trong config gốc được tính từ thư mục chứa file đó.
Tham số CLI/API truyền trực tiếp có ưu tiên hơn YAML. Cấu hình pipeline cũ trong
`.env` không còn được đọc. Chi tiết từng trường nằm trong README của module tương ứng.

## Chạy trên máy

Chạy các lệnh sau từ thư mục gốc dự án:

```powershell
python -m pip install -r requirements.txt
python main.py
```

Chạy một PDF hoặc một thư mục và ghi đè các kết quả đã có:

```powershell
python main.py Data\pdf\1.000005.pdf --overwrite
python main.py Data\pdf --output-dir outputs\metadata --overwrite
```

Chọn cấu hình riêng: `python main.py --config config.yaml`.
PDF được xử lý tuần tự trên CPU. OCR cần dữ liệu ngôn ngữ Tesseract;
xem hướng dẫn trong [ingestion](ingestion/README.md).

## Kết quả

Mỗi PDF có JSON chunks và báo cáo xử lý. Chỉ sử dụng kết quả có báo cáo `success`
để đưa vào index; các file trong `review/` cần được đối chiếu trước.
Ý nghĩa trạng thái và cách tiếp tục sau lỗi nằm trong [ingestion](ingestion/README.md#chạy-và-kết-quả).
Schema chunks và cách dùng `parent_section` nằm trong [chunking](chunking/README.md#schema-json).

## Google Colab

Mở [ipynb/main.ipynb](../ipynb/main.ipynb) bằng Colab. Notebook cài dependencies,
clone/cập nhật repository, nhận PDF qua upload hoặc Google Drive, chạy pipeline,
hiển thị kết quả mẫu và đóng gói JSON thành ZIP để tải về.

Thiết lập nguồn Drive và output ở nhóm `colab` trong config gốc. Notebook tải mã
từ GitHub nên bản sửa local cần được đồng bộ lên repository trước khi sử dụng.
Parse/chunk dùng CPU; GPU phục vụ các bước mô hình như embedding nếu được bổ sung.

## Kiểm thử

```powershell
python -m unittest discover -s tests -v
```

Bộ kiểm thử bao gồm cấu hình YAML, schema, làm sạch HTML, phân loại section,
bảng, giới hạn kích thước, phục hồi metadata và báo cáo trang OCR thất bại.
