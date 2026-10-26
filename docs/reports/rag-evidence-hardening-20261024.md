# Kiểm chứng đóng gói bằng chứng RAG — 24/10/2026

Task `TASK-20261024-07`. Đây là báo cáo source, hợp đồng dữ liệu và kiểm thử;
không phải benchmark chất lượng câu trả lời của model.

## Khảo sát và thay đổi

Luồng hiện tại: parser/chunker TTHC → corpus BGE-M3/FAISS → cache SQLite →
retriever → MiniLM → `build_messages` → generation/schema/retry → API/Web.
Core lưu trữ/prompt nay chấp nhận metadata tùy schema; parser PDF và router
ViGovBot vẫn theo nghiệp vụ TTHC. Chưa chuyển toàn ứng dụng thành chatbot mọi domain.

| Vị trí | Trước | Sau |
|---|---|---|
| Schema corpus | Bắt buộc tám trường, gồm metadata TTHC | Bắt buộc ID/nội dung; metadata tùy chọn, dữ liệu cũ tương thích |
| SQLite | Whitelist làm mất metadata mở rộng | Giữ metadata JSON, trừ nội dung parent lặp; cache v2 riêng |
| Source prompt | Header rời, cần source_code và nhiều khóa trace | Một JSON envelope, mỗi source giữ ID thực/metadata/content |
| Metadata | Không đóng gói đủ | Giữ type/nesting, không merge scope, bỏ null/rỗng, giữ false/0 |
| Budget | Token slicing có thể cắt ô bảng | Tính cả envelope; text đánh dấu truncation, bảng/JSON nguyên khối |
| Chunker | Không nhận separator thiếu pipe cuối | Lặp header ở child chunk đúng định dạng Markdown đó |
| Bằng chứng | Prompt dài, quy tắc lặp và đặc thù | Nhóm quy tắc tổng quát + reminder ngắn; policy router giữ nguyên |
| Ranh giới dữ liệu | Delimiter văn bản có thể bị giả mạo | JSON escaping, escape dấu góc; lịch sử chỉ user/assistant |
| Payload retrieval | Có thể ghi đè score/row_id | FAISS/SQLite là nguồn quyết định các trường nội bộ |
| Log lỗi | Có rejected model output trong diagnostics | Chỉ log số lần và số lỗi, không raw output/exception cause |

Formatter nằm tại `src/vigovbot/prompts/evidence.py`; các caller runtime và
oracle evaluation cùng đi qua `build_messages`. Không thêm dependency.
Không hardcode dữ kiện của ca `1.000183`, không tự thêm nội dung câu trả lời.

## Tương thích và vận hành

- Tên file corpus, manifest, table SQLite và response API giữ nguyên. Cache
  version nằm trong namespace thư mục mới; v1 không bị ghi đè/xóa. Cần thêm
  dung lượng cho bản sao index/cache; không cần tạo embedding lại.
- `retrieval.max_metadata_tokens=256` là giới hạn metadata mỗi nguồn, ngoài
  ngân sách `num_ctx - num_predict - 256`. ID chunk được giữ riêng trong envelope.
- Metadata document/chunk giữ namespace nguyên bản; giá trị mâu thuẫn không bị
  merge/ghi đè. Trường quá dài bị bỏ nguyên trường và báo `metadata_omitted`;
  heuristic ưu tiên định danh/phạm vi/phiên bản không hiểu mọi schema tương lai.
- `parent_section` là nội dung lặp bị loại khỏi cache như trước. Các khóa quan
  hệ parent/bảng/vị trí khác được giữ nếu corpus thực sự có.
- Bảng/JSON không vừa budget bị bỏ nguyên khối, có `omitted_sources` trong
  prompt; các nguồn sau vẫn được thử. Cần đánh giá tỷ lệ omission trên corpus
  trước khi tối ưu budget. Text dài có `content_truncated`, không âm thầm coi là đầy đủ.
- Panel Web vẫn hiển thị toàn văn reranked hits; `context_used.included_text`
  và `included_metadata` trong evaluation trace mới là đầu vào thực của model.
- Formatter nhận text/object/list; embedding hiện cần `text_content` chuỗi.
  Không tự suy diễn bảng từ binary/PDF hoặc metadata từ câu văn.

## Kiểm chứng

- Baseline host trước thay đổi: 49 test PASS.
- Host focused: prompt, evidence, routing, reranker, server/UI, chunker,
  retrieval benchmark, review và documentation: 77 test PASS.
- Docker image sẵn có, `--network none`, workspace read-only, `PYTHONPATH=/workspace/src`:
  test FAISS/SQLite thật, cache reuse/migration, generic metadata, exact code,
  prompt budget, multi-turn, router, config và API. Encoder/LLM được mock.
- Lượt container rộng: 92 test, 2 errors, 1 skip tại thời điểm chạy. Hai errors
  là notebook không có trong checkout và matplotlib không có trong runtime
  image. Lượt tập trung loại **chỉ hai test này**, công khai tên/lý do; skip v4
  dataset thiếu được giữ nguyên: lượt tập trung 91 test, 90 PASS và 1 SKIP.
  Không tuyên bố toàn bộ repository pass.
- Host discovery: 242 test, 4 errors, 17 skips do môi trường thiếu dependency;
  không phải các test hồi quy mới thất bại. Lỗi mới về budget và Ruff đã sửa.
- Tokenizer Qwen thực từ snapshot cache, network disabled: source
  `tthc_1_000183_sec_required_documents_3_p1` lấy từ artifact MiniLM cũ được giữ
  nguyên, có `56789...docx`, metadata không bị bỏ; prompt 1.103 token, 0 LLM call.
  Chỉ một source fixture, không phải đánh giá end-to-end Top-3 hay generation.

Các test đối kháng xác nhận JSON round-trip, không tạo message role mới, không
còn literal chat delimiter từ nguồn trong user envelope, source không ghi đè
row_id/score, và canary không lộ qua log lỗi generation. Chưa đo tỷ lệ model
làm theo prompt injection; serialization không phải cơ chế bảo mật tuyệt đối.

## Giới hạn kết luận

Không có số liệu mới về accuracy, completeness, faithfulness, Recall/MRR,
latency generation hoặc semantic injection. Thứ hạng retrieval bình thường
không đổi; không áp bộ lọc tên cứng có thể làm mất evidence của câu đa ý.
Các test xác nhận dữ kiện đi đến prompt, không chứng minh model nhắc lại đủ
mọi ô. Yêu cầu không mất dữ kiện ở câu trả lời vẫn cần đo A/B generation bằng
cùng input/context/model, đối chiếu trực tiếp giá trị với nguồn.

Docker services không chạy lúc kiểm tra; không triển khai lại Web hoặc tải
model. Source mới sẽ được dùng khi khởi động lại với mount/PYTHONPATH đúng.

[Mục lục tài liệu](../README.md) · [Prompt module](../../src/vigovbot/prompts/README.md)
