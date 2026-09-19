# ViGovBot

ViGovBot là dự án nghiên cứu kết hợp QLoRA (Quantized Low-Rank Adaptation) và RAG (Retrieval-Augmented Generation) trên mô hình ngôn ngữ lớn nhằm xây dựng chatbot tiếng Việt hỗ trợ dịch vụ hành chính công. Dự án hướng tới sử dụng QLoRA để tinh chỉnh mô hình với chi phí tài nguyên thấp, đồng thời áp dụng RAG để truy xuất thông tin từ tài liệu hành chính và bổ sung ngữ cảnh cho quá trình sinh câu trả lời. Chatbot được định hướng hỗ trợ người dân tra cứu thủ tục, thành phần hồ sơ, điều kiện thực hiện và quy trình giải quyết, với câu trả lời dễ hiểu và có dẫn nguồn. Nghiên cứu tập trung đánh giá độ chính xác, mức độ bám sát tài liệu, khả năng hạn chế thông tin sai lệch và hiệu quả sử dụng tài nguyên của phương pháp kết hợp trong bối cảnh tiếng Việt.

## Pipeline xử lý dữ liệu

Pipeline hiện tại chuyển tài liệu thủ tục hành chính từ PDF thành các JSON chunk có thể đưa vào bước tạo embedding và lập chỉ mục RAG:

```text
PDF
 └─ kiểm tra định dạng và dung lượng
     └─ PyMuPDF4LLM chuyển thành Markdown
         └─ chuẩn hóa và làm sạch Markdown
             └─ trích xuất mã và tên thủ tục
                 └─ nhận diện các section theo cấu trúc
                     └─ chia child chunk và gắn ngữ cảnh
                         └─ lưu một file JSON cho mỗi PDF
```

Hai thành phần chính là:

- `src/ingestion/parse.py`: tiếp nhận PDF, kiểm tra, trích xuất Markdown và ghi JSON.
- `src/chunking/markdown.py`: hiểu cấu trúc tài liệu, phân loại section và tạo chunk parent–child.

## Ingestion: PDF sang Markdown và JSON

Module `src/ingestion/parse.py` chịu trách nhiệm điều phối đầu vào và lưu kết quả.

### 1. Cấu hình

Các biến môi trường được đọc từ `.env`:

```env
OUTPUT_DIR=outputs
MAX_PDF_SIZE_MB=20
```

- `OUTPUT_DIR`: thư mục lưu JSON. Đường dẫn tương đối được tính từ thư mục gốc dự án.
- `MAX_PDF_SIZE_MB`: dung lượng PDF tối đa; giá trị phải lớn hơn `0` và không vượt quá `100` MB.

### 2. Kiểm tra đầu vào

Trước khi xử lý, `validate_pdf()` kiểm tra:

- đường dẫn tồn tại và có phần mở rộng `.pdf`;
- file không rỗng và không vượt giới hạn dung lượng;
- năm byte đầu tiên có chữ ký `%PDF-`.

### 3. Trích xuất Markdown

`local_markdown()` mở tài liệu bằng PyMuPDF và chuyển nội dung bằng PyMuPDF4LLM. OCR hiện đang tắt (`use_ocr=False`). Pipeline sẽ báo lỗi nếu:

- PDF được bảo vệ bằng mật khẩu;
- có trang không chứa lớp văn bản;
- PyMuPDF không thể đọc tài liệu.

Vì vậy, PDF scan chưa OCR phải được OCR trước khi đưa vào pipeline.

### 4. Làm sạch nội dung

`clean_markdown()` thực hiện các bước:

- chuẩn hóa ký tự xuống dòng;
- gộp nhiều dòng trống liên tiếp;
- loại ký tự thay thế Unicode bị lỗi;
- loại token backtick rỗng và các dòng bảng rỗng;
- giữ nguyên fenced code block và cấu trúc bảng Markdown hợp lệ.

Markdown sau làm sạch được chuyển cho `TTHCStructureAwareChunker` với giới hạn mặc định `1.500` ký tự cho toàn bộ `text_content`.

### 5. Lưu kết quả

Mỗi PDF sinh ra một file JSON cùng tên:

```text
Data/1.000005.pdf → outputs/1.000005.json
```

Khi đầu vào là một thư mục, chương trình tìm PDF đệ quy và giữ cấu trúc thư mục con tương ứng trong `outputs`. File được ghi vào một file tạm có UUID rồi thay thế file đích để hạn chế tạo JSON dở dang khi tiến trình bị gián đoạn.

Nếu JSON đã tồn tại, file được bỏ qua. Dùng `--overwrite` để xử lý lại.

### 6. Cách chạy ingestion

Cài dependency:

```powershell
python -m pip install -r requirements.txt
```

Xử lý một PDF:

```powershell
python main.py Data\pdf\1.000005.pdf
```

Xử lý toàn bộ PDF trong một thư mục:

```powershell
python main.py Data\pdf
```

Chọn thư mục đầu ra và cho phép ghi đè:

```powershell
python main.py Data\pdf --output-dir outputs\metadata --overwrite
```

## Chunking: Structure-Aware Hybrid Markdown

Module `src/chunking/markdown.py` triển khai `TTHCStructureAwareChunker`. Đây là phương pháp lai: ưu tiên cấu trúc ngữ nghĩa thể hiện qua heading, sau đó mới chia theo kích thước khi một section quá dài.

### 1. Trích xuất metadata tài liệu

`extract_metadata()` tìm:

- `source_code`: mã TTHC theo dạng `1.000005`;
- `procedure_name`: ưu tiên giá trị cùng dòng hoặc dòng văn bản đầu tiên ngay sau `Tên thủ tục`; nếu không có thì dùng heading cấp 1 đầu tiên. Heading trang `CHI TIẾT THỦ TỤC HÀNH CHÍNH` luôn bị bỏ qua.

Thiếu một trong hai trường bắt buộc sẽ phát sinh `TTHCChunkingError`. Điều này ngăn dữ liệu không đủ định danh đi vào vector index.

### 2. Nhận diện và phân loại section

`parse_sections()` nhận diện heading Markdown từ `#` đến `######` và dòng tiêu đề in đậm đứng riêng. Heading luôn được giữ ở đầu nội dung section tiếp theo, tránh tạo orphan heading.

Section được phân loại không phân biệt hoa thường hoặc dấu tiếng Việt:

| Từ khóa heading | `section_type` |
|---|---|
| Thông tin chung, Định danh | `metadata_identity` |
| Trình tự thực hiện, Các bước | `procedure_step` |
| Thành phần hồ sơ, Giấy tờ, Chứng từ phải nộp, Hồ sơ hải quan | `required_documents` |
| Cách thức thực hiện, Thời hạn giải quyết, Phí, Lệ phí | `submission_deadline_fee` |
| Căn cứ pháp lý | `legal_basis` |
| Không khớp nhóm trên | `other` |

### 3. Parent–child indexing

Mỗi section đầy đủ là một **parent**. Section được chia thành một hoặc nhiều **child chunk** dùng để tạo embedding:

```text
Parent section: toàn bộ mục "Thành phần hồ sơ"
 ├─ Child p1: nhóm giấy tờ đầu tiên
 ├─ Child p2: nhóm giấy tờ tiếp theo
 └─ Child p3: phần còn lại
```

- `text_content` là child text dùng để embedding và tìm kiếm.
- `parent_section` giữ nguyên toàn bộ section để cung cấp ngữ cảnh rộng hơn cho LLM sau khi truy xuất.
- Các child thuộc cùng parent có cùng giá trị `parent_section`.

### 4. Quy tắc kích thước và overlap

Cấu hình mặc định:

```python
TTHCStructureAwareChunker(
    target_chars=1200,
    max_chars=1500,
    overlap_chars=100,
)
```

- Chunk được đóng gói hướng tới khoảng `1.200` ký tự.
- `text_content`, bao gồm cả context prefix, không vượt quá `1.500` ký tự.
- Section dài được tách lần lượt theo paragraph, dòng và cuối cùng theo đơn vị nhỏ hơn nếu cần.
- Child chunk văn bản kế tiếp nhận tối đa `100` ký tự cuối của chunk trước, ưu tiên ranh giới từ.
- Overlap không được chèn khi chunk chứa bảng, nhằm tránh sao chép nửa hàng hoặc làm hỏng cú pháp bảng.

### 5. Bảo toàn bảng Markdown

Các dòng bắt đầu và kết thúc bằng `|` được xem là hàng của bảng:

- bảng vừa với phần dung lượng còn lại của chunk được giữ nguyên;
- bảng dài chỉ được tách giữa hai hàng;
- header và separator được lặp lại ở mỗi phần của bảng dài;
- một hàng đơn lẻ dài hơn hard limit sẽ phát sinh lỗi thay vì bị cắt giữa hàng.

Dung lượng thực tế dành cho nội dung bảng bằng `max_chars` trừ độ dài context prefix.

Sau khi chia, post-processing filter loại các child chunk có phần nội dung thực (không tính heading và context prefix) ngắn hơn `10` ký tự.

### 6. Contextual metadata injection

Mỗi child chunk nhận prefix:

```text
[Thủ tục: {procedure_name} | Mã TTHC: {source_code} | Mục: {section_title}]
```

Prefix được lưu riêng trong `context_prefix` và đồng thời đặt ở đầu `text_content`. Khi tạo embedding, sử dụng trực tiếp `text_content` để vector chứa cả nội dung lẫn định danh ngữ cảnh.

### 7. Schema JSON đầu ra

```json
{
  "chunk_id": "tthc_1_000005_sec_required_documents_2_p1",
  "source_file": "1.000005.pdf",
  "source_code": "1.000005",
  "procedure_name": "Cấp bản sao trích lục hộ tịch",
  "section_type": "required_documents",
  "context_prefix": "[Thủ tục: Cấp bản sao trích lục hộ tịch | Mã TTHC: 1.000005 | Mục: Thành phần hồ sơ]",
  "text_content": "[Thủ tục: ...]\n\n## Thành phần hồ sơ\n\n...",
  "parent_section": "## Thành phần hồ sơ\n\n..."
}
```

`chunk_id` có dạng:

```text
tthc_<mã thủ tục>_sec_<loại section>_<số section>_p<số child>
```

Số section được đưa vào ID để tránh trùng ID khi một tài liệu có nhiều section cùng loại.

### 8. Dùng chunker trực tiếp với Markdown

```python
from src.chunking.markdown import TTHCStructureAwareChunker

chunker = TTHCStructureAwareChunker()

# Đọc trực tiếp file .md
chunks = chunker.process_document("Data/1.000005.md")

# Hoặc xử lý chuỗi Markdown và chỉ định tên PDF nguồn
chunks = chunker.process_document(markdown_text, source_file="1.000005.pdf")
```

Kết quả là `list[dict]`, có thể ghi thành JSON hoặc chuyển tiếp sang bước embedding/vector indexing.

## Kiểm thử

Chạy bộ kiểm thử chunking:

```powershell
python -m unittest discover -s tests -v
```

Bộ kiểm thử hiện kiểm tra schema, context injection, phân loại section, bảo toàn bảng, hard limit, parent–child và lỗi khi thiếu metadata.

## Chạy trên Google Colab

Notebook `ipynb/main.ipynb` cung cấp phiên bản Colab của pipeline. Notebook thực hiện:

- cài dependency trong Colab runtime;
- clone hoặc cập nhật mã nguồn từ repository;
- nhận nhiều PDF bằng upload hoặc đọc đệ quy từ Google Drive;
- chạy ingestion và chunking cho từng file;
- hiển thị thống kê, lỗi và một chunk mẫu;
- đóng gói toàn bộ JSON thành ZIP để tải về.

Mở notebook trên Colab:

```text
https://colab.research.google.com/github/qtamtensor05/ViGovBot/blob/main/ipynb/main.ipynb
```

Pipeline PDF/chunking hiện dùng CPU. Việc bật GPU runtime chỉ cần thiết khi bổ sung bước tạo embedding, reranking hoặc chạy mô hình ngôn ngữ.

## Giấy phép

Mã nguồn của dự án được phát hành theo [giấy phép](LICENSE). Dữ liệu, tài liệu và mô hình của bên thứ ba được sử dụng trong dự án tuân theo giấy phép và điều kiện sử dụng riêng của từng nguồn.
