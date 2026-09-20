# Chunking

`markdown.py` chuyển Markdown thành danh sách chunks theo schema `TTHCChunk`.

Luồng: làm sạch HTML → metadata → section theo heading → phân loại → chia nội dung
→ lặp header bảng → chèn context prefix → lọc chunk rỗng.
`parent_section` giữ section đầy đủ, `text_content` dùng cho embedding.

Xem [hướng dẫn xử lý dữ liệu](../README.md) để chạy toàn bộ pipeline.

## Metadata và section

Tên thủ tục được lấy sau `Tên thủ tục`, hoặc từ heading cấp 1; tiêu đề trang
`CHI TIẾT THỦ TỤC HÀNH CHÍNH` không được dùng làm tên. Mã TTHC theo mẫu `1.000005`.
Ingestion có thể bật phục hồi định danh: lấy mã từ tên file đúng chuẩn hoặc tạo
ID `unverified_…`; kết quả cần xác minh được đưa vào review, không tự sửa chữ số.

Heading `#`–`######` và dòng in đậm đứng riêng tạo section. Phân loại mặc định:

| Nhóm heading | Nhãn |
|---|---|
| Thông tin chung, Định danh, Chi tiết thủ tục hành chính, Cơ quan thực hiện, Kết quả xử lý | `metadata_identity` |
| Trình tự thực hiện, Các bước | `procedure_step` |
| Thành phần hồ sơ, Giấy tờ, Chứng từ phải nộp, Hồ sơ hải quan | `required_documents` |
| Cách thức thực hiện, Thời hạn giải quyết, Phí, Lệ phí | `submission_deadline_fee` |
| Căn cứ pháp lý | `legal_basis` |
| Không khớp | `other` |

HTML entity được giải mã; `<br>` và các biến thể được đổi thành khoảng trắng trước
khi tạo metadata và prefix. Chunk ít nội dung bị lọc, không tính heading/header.

## Cấu hình

[config.yaml](config.yaml) được tham chiếu qua `modules.chunking` trong config gốc.

| Khóa | Ý nghĩa |
|---|---|
| `target_chars` | Kích thước mục tiêu khi đóng gói nội dung |
| `max_chars` | Giới hạn cuối cùng, bao gồm prefix/header |
| `overlap_chars` | Overlap tối đa cho văn bản; có thể giảm để vừa ngân sách |
| `min_content_chars` | Ngưỡng loại chunk ít nội dung, không tính heading/header |
| `section_keywords` | Từ khóa cho từng nhãn; so khớp không phân biệt hoa/thường và dấu |

Điều kiện: `0 <= overlap_chars < target_chars <= max_chars`.
Kích thước target/max tối thiểu 100 ký tự. Từ khóa nên dùng dạng không dấu như mẫu.

Bảng vừa ngân sách giữ hàng nguyên vẹn và lặp header. Khi hàng/header quá dài,
section được chuyển sang khóa–giá trị rồi chia văn bản; parent vẫn giữ bảng gốc.
Prefix dài được rút gọn, không rút gọn tên thủ tục trong metadata.

Header bảng gần nhất được lặp cho phần văn bản tiếp nối đến hết section theo
heuristic xử lý PDF mất cấu trúc. Mỗi bảng mới dùng header riêng. Có quy tắc hẹp
nối lỗi trích xuất `chứng t` / `ừ …`; không suy đoán mọi từ bị đứt.
Văn bản dài được chia theo dòng, khoảng trắng và cuối cùng theo ký tự khi cần.
Overlap tối đa theo cấu hình, không áp dụng như một bảo đảm cho mọi chunk/fallback.

## Schema JSON

Mỗi section là parent; các child cùng section có chung `parent_section`.
Prefix được đặt ở đầu `text_content` để tạo embedding có ngữ cảnh.

```json
{
  "chunk_id": "tthc_1_000005_sec_required_documents_2_p1",
  "source_file": "1.000005.pdf",
  "source_code": "1.000005",
  "procedure_name": "Cấp bản sao trích lục hộ tịch",
  "section_type": "required_documents",
  "context_prefix": "[Thủ tục: Cấp bản sao trích lục hộ tịch | Mã TTHC: 1.000005 | Mục: Thành phần hồ sơ]",
  "text_content": "[Thủ tục: Cấp bản sao trích lục hộ tịch | Mã TTHC: 1.000005 | Mục: Thành phần hồ sơ]\n\nTờ khai theo mẫu và giấy tờ tùy thân.",
  "parent_section": "## Thành phần hồ sơ\n\nTờ khai theo mẫu và giấy tờ tùy thân."
}
```

ID gồm mã thủ tục, loại section, số section và số child. Dùng `text_content` để
embedding, dùng `parent_section` để bổ sung ngữ cảnh khi sinh câu trả lời.

## Sử dụng trực tiếp

```python
from src.configuration import load_configuration
from src.chunking.markdown import TTHCStructureAwareChunker

_, _, settings = load_configuration('config.yaml')
chunker = TTHCStructureAwareChunker(settings=settings)
chunks = chunker.process_document('Data/example.md')
```

Constructor không truyền settings tự đọc config mặc định của dự án.
Các tham số `max_chars`, `target_chars`, `overlap_chars` truyền trực tiếp có ưu tiên
hơn YAML. `warnings` ghi các fallback. Metadata recovery do ingestion quyết định;
gọi chunker trực tiếp mặc định vẫn báo lỗi nếu thiếu định danh.
