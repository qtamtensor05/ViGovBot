# Chunking

`markdown.py` chuyển Markdown thành danh sách chunks theo schema `TTHCChunk`.

Luồng: làm sạch HTML → metadata → section theo heading → phân loại → chia nội dung
→ lặp header bảng → chèn context prefix → lọc chunk rỗng.
`parent_section` giữ section đầy đủ, `text_content` dùng cho embedding.

Đầu vào là Markdown/text của một tài liệu; đầu ra là danh sách `TTHCChunk`
được [ingestion](../ingestion/README.md) ghi thành JSON. Module chưa tạo vector.

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
Kích thước target/max tối thiểu 100 ký tự. Cơ chế so khớp từ khóa chuẩn hóa dấu và chữ hoa/thường.

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

ID gồm mã thủ tục, loại section, số section và số child. [Embeddings](../embeddings/README.md)
dùng `text_content` để tạo vector. `parent_section` lưu toàn bộ nội dung section cha; pipeline RAG hiện tại chưa dùng trường này và không chép nó vào SQLite.

## Giao diện và quan hệ với ingestion

`TTHCStructureAwareChunker` nhận cấu hình chia đoạn; `process_document()` đọc
tài liệu Markdown và trả danh sách chunks. Ingestion sử dụng kết quả này để ghi JSON.

Constructor không nhận settings sẽ đọc cấu hình mặc định. Các tham số kích thước
truyền trực tiếp có ưu tiên hơn YAML. `warnings` ghi nhận các trường hợp xử lý dự phòng.
Ingestion quyết định chính sách phục hồi định danh; chunker mặc định báo lỗi khi thiếu định danh.

[Kiến trúc tổng thể](../README.md)
