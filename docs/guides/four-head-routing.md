# Routing PhoBERT bốn head và menu theo trạng thái

## Luồng đang vận hành

Các cấu hình `inference*.yaml` mặc định dùng `routing_contract: v2` và
`routing_backend: phobert`. PhoBERT thay việc gọi Qwen để phân loại và thay các
quy tắc ghi đè nhãn section theo từ khóa. Qwen vẫn sinh câu trả lời từ tài liệu.
Không tự fallback sang LLM khi checkpoint thiếu hoặc lỗi.

Checkpoint local: `outputs/phobert_v3_finetuned_20261028/checkpoint`.
Bốn head dự đoán phạm vi, câu mới/hỏi tiếp, nhiều thủ tục, và 11 mục nội dung.
Giữ thứ tự nhãn và ngưỡng sigmoid riêng từ `meta.json`; ba head đơn nhãn dùng
softmax/argmax. Nhãn mục rỗng giữ rỗng, không tự thêm Tổng quan. Bốn nhãn
`Kết quả thực hiện`, `Phí, lệ phí`, `Thời hạn giải quyết` và `Cách thức thực hiện`
ánh xạ lần lượt tới `result`, `fee`, `processing_time` và `submission_method`.
Corpus legacy còn `submission_deadline_fee` được đọc bằng fallback chỉ khi nhóm
mới không có hit; ingestion mới không phát sinh nhóm tổng hợp này. Các ánh xạ
nằm trong `sections.py`, không phải bộ phân loại từ khóa.

## Hợp đồng checkpoint

- NFC, gộp khoảng trắng, tách từ bằng PyVi như huấn luyện.
- Ba đoạn: câu hỏi hiện tại, tin nhắn liền trước trong lịch sử hợp lệ (thường là
  câu trả lời assistant), tên thủ tục đang chọn từ state có chữ ký. Không có dữ
  liệu thì để đoạn rỗng; không lấy tên thủ tục từ lời trả lời cũ chưa xác thực.
- Chuỗi `<s> question </s></s> previous </s></s> procedure </s>`, tối đa 128
  token theo metadata; cắt đoạn dài nhất trước, vẫn giữ đủ dấu phân cách.
- Encoder local, pooling token CLS, bốn linear head; eval/inference mode trên CPU.
  `heads.pt` nạp bằng `weights_only=True`, kiểm tra đủ và đúng key/shape.
- Cache một model theo path/thread setting, serialize inference. Mặc định đặt
  PyTorch CPU intra-op threads bằng 2 lúc nạp (cũng ảnh hưởng encoder CPU dùng
  chung process); không chiếm VRAM của Qwen/QLoRA. Không tải model thay thế.
- Trace API khi `evaluation_trace: true` có xác suất, ngưỡng, độ dài và hash
  checkpoint trong `evaluation_trace.routing_classifier`. Endpoint identity cũng
  cung cấp hash router. Trace này là bằng chứng chạy, không phải metric chất lượng.

## Xác định thủ tục và hội thoại

PhoBERT không sinh tên thủ tục, không viết lại truy vấn và không trả span thực thể.
Adapter lấy mã/tên từ corpus (chấp nhận thiếu tiền tố “Thủ tục”), giữ câu gốc và
chỉ dùng thủ tục đã chọn khi model dự đoán hỏi tiếp. Nhiều mã trùng tên mở menu
lựa chọn; chưa có section mở menu nội dung.

Menu web là văn bản; người dùng nhập số thứ tự hoặc tên mục (`direct_choice`).
Chọn trực tiếp từ menu có chữ ký không cần chạy PhoBERT classifier. Cơ chế
`direct_choice` chỉ kích hoạt khi phiên hội thoại đang có menu chờ phản hồi còn
hiệu lực. Đối với câu hỏi mới (khi không có menu đang chờ hoặc menu trước đó đã
hoàn tất), các câu hỏi có chứa chữ số (ví dụ: *"làm cccd cho người 14 tuổi"*,
*"đổi giấy phép lái xe lần 2"*) được chuyển tiếp bình thường vào router mà không bị
chặn nhầm thành lựa chọn menu sai cú pháp.

Tên hoặc mã khớp catalog chỉ kéo `OUT_OF_SCOPE` về `IN_SCOPE` khi xác suất
`Ngoài phạm vi` nằm trong `[0,50; 0,85)`. Từ `0,85` trở lên giữ quyết định ngoài
phạm vi; dưới `0,50` cũng không override vì nằm ngoài band đã cấu hình. Mỗi lần
arbitration ghi `p_out_of_scope`, band và outcome có cấu trúc trong
`adapter_decisions`. Quyết định này chỉ xác nhận thực thể, không thêm hoặc ghi đè
nhãn section của PhoBERT.

Curated alias trong `configs/rag/procedure-aliases.yaml` là ngoại lệ có kiểm
duyệt: alias duy nhất, dài ít nhất hai từ và trỏ tới mã có thật được phép xác nhận
scope trực tiếp khi truy vấn chính là alias đó. Alias chỉ được nhắc trong câu dài
không bỏ qua `P(OUT)` cao. Alias trùng giữa hai mã hoặc mã không có trong catalog
làm runtime fail closed. Truy vấn alias trần chỉ mở menu section, không tự truy xuất.

Nếu vẫn là `OUT_OF_SCOPE`, cụm tìm kiếm tối đa sáu từ được chấm BM25 + exact
cosine trên catalog. Candidate chứa qualifier hẹp mà câu hỏi không có (`người
nước ngoài`, `quân sự`, `công an`, `ngoại giao`, `chuyên dùng`, `quá hạn`, `tạm
thời`) chịu hệ số phạt `0,5`. Chỉ khi Top 1 đạt `0,70` và cách Top 2 ít nhất
`0,08`, hệ thống mở menu xác nhận 2–3 thủ tục. Lượt này không retrieval và không
generation. Chọn một thủ tục mới nâng state sang `IN_SCOPE`; phủ nhận giữ
`OUT_OF_SCOPE`. Raw BM25, cosine, penalty, gated score và margin nằm trong trace.
Các ngưỡng là policy ban đầu, chưa được coi là calibrated nếu chưa benchmark trên
tập ánh xạ câu hỏi–mã thủ tục có nhãn thật.

State gắn model, corpus, lịch sử và chữ ký HMAC SHA-256. State sửa đổi/hết hạn
không được dùng làm nguồn xác định thủ tục. Hội thoại mới bỏ state cũ; đổi thủ tục
có tên rõ được xác định từ câu mới. Cache hỗ trợ client chỉ gửi text và lịch sử
chính xác tối đa 256 state; restart làm mất state/cache trong process.

## Xử lý phạm vi hỗn hợp (Mixed Scope)

Checkpoint chỉ có nhãn section toàn câu, không có liên kết mục–thủ tục. Khi head
báo nhiều thủ tục, hệ thống yêu cầu hỏi riêng từng thủ tục thay vì ghép union nhãn
vào mọi nguồn. Đây là giới hạn của checkpoint/adapter hiện tại, không phải khả
năng phân rã như router LLM cũ.

Với hỗn hợp phạm vi (`MIXED_SCOPE`):
1. **Phân rã bằng regex và PhoBERT:** Adapter phân rã câu hỏi thành các mệnh đề
   bằng regex (`_SPLIT_PATTERN` tách theo dấu câu/“và”/“đồng thời”, tối đa 8 mảnh).
   PhoBERT phân loại độc lập từng mệnh đề; nếu tìm thấy đúng một mệnh đề thuộc
   phạm vi (`IN_SCOPE`), hệ thống dùng mệnh đề này để truy xuất.
2. **Extractive Rewrite qua LLM (Fallback có kiểm chứng):** Khi regex phân tách
   thành $\le 8$ mảnh nhưng không có mảnh nào được PhoBERT xếp loại `IN_SCOPE` độc
   lập (`len(parts) <= 8 and not supported`), adapter gọi Qwen với giới hạn 128
   token để trích đúng một đoạn nguyên văn liên tiếp thuộc phạm vi hỗ trợ. Đoạn
   trích phải giữ nguyên mã hoặc qualifier hẹp. Đoạn trích sau đó bắt buộc phải
   được PhoBERT phân loại lại thành một yêu cầu `IN_SCOPE` duy nhất mới được kích
   hoạt retrieval.
3. Khi được chấp nhận, scope tổng thể vẫn là `MIXED_SCOPE` để câu trả lời có ghi
   chú phần nằm ngoài phạm vi. Nếu LLM lỗi/trả rỗng, câu không phải đoạn trích
   nguyên văn, hoặc PhoBERT không xác nhận, hệ thống dừng lại, yêu cầu người dùng
   làm rõ và không truy xuất. Nhánh này không được gọi cho `IN_SCOPE` hoặc `OUT_OF_SCOPE`.

## Dự phòng tìm kiếm ngữ nghĩa khi thiếu danh tính thủ tục (Semantic Fallback)

Khi PhoBERT phân loại câu hỏi là `IN_SCOPE` (hoặc `MIXED_SCOPE` trích xuất thành công)
nhưng catalog procedure discovery không xác định được mã TTHC cụ thể (`unresolved`):
- Hệ thống không làm rỗng kết quả hay từ chối câu hỏi.
- FAISS vector retriever thực hiện tìm kiếm ngữ nghĩa trên toàn bộ corpus thủ tục,
  giữ lại các đoạn văn bản tương đồng cao nhất (`unresolved_semantic_hits`).
- Bằng chứng ngữ cảnh được chuyển tới LLM Qwen để sinh câu trả lời có căn cứ,
  đồng thời trace ghi nhận rõ `retrieval_strategy: "semantic"` thay vì `procedure_filtered`.

## Cấu hình và Docker

```yaml
conversation:
  routing_contract: v2
  routing_backend: phobert
  routing_phobert_path: ../../outputs/phobert_v3_finetuned_20261028/checkpoint
  routing_phobert_threads: 2
  state_secret: "change-me-in-production"
  procedure_aliases_path: configs/rag/procedure-aliases.yaml
  procedure_confirmation_score_threshold: 0.70
  procedure_confirmation_margin_threshold: 0.08
  procedure_confirmation_bm25_weight: 0.50
  procedure_confirmation_cosine_weight: 0.50
  unresolved_semantic_retrieval_enabled: true
```

Path tương đối được giải theo file YAML. Cài môi trường host bằng extras
`.[rag,phobert]`. Docker có lớp dependency PyVi riêng trong
`locks/phobert-linux-py312.txt`, giữ cache lớp Torch/CUDA. Cả web và web-gpu mount
checkpoint chỉ đọc và không tự tạo thư mục model nếu thiếu. Lần đầu đổi dependency
và mount cần build/recreate web; sửa Python sau đó chỉ cần restart.

```powershell
docker compose build web
docker compose up -d --no-deps web
```

Backend `llm` v2 và hợp đồng v1 còn cho cấu hình tương thích tường minh,
không tham gia routing mặc định hoặc fallback PhoBERT. Các quy tắc section cũ
chỉ áp dụng đường LLM cũ.
