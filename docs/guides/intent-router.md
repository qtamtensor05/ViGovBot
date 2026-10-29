# Intent router siêu nhẹ

Tài liệu này dành cho `conversation.routing_contract: v1`. Mặc định hiện tại là
[routing v2 bốn nhóm nhãn](four-head-routing.md), dùng backend `phobert`.
Muốn dùng artifact FastText bảy nhãn phải đặt rõ `routing_contract: v1`.

Chế độ tương thích v1 hỗ trợ ba backend tại `conversation.routing_backend`:

- `llm`: dùng router Qwen khi được chọn tường minh.
- `fasttext`: dùng classifier để benchmark. Chỉ hai nhánh đủ tin cậy
  `in_scope.new_question` và `out_of_scope.new_question` được quyết định trực
  tiếp; trường hợp khác trả yêu cầu làm rõ bảo thủ.
- `hybrid`: quyết định trực tiếp hai nhánh trên và chuyển sang Qwen khi confidence
  thấp hoặc cần xử lý `follow_up`, `mixed`, `ambiguous` hay viết lại truy vấn.

Nếu model, metadata, SHA-256 hoặc dependency FastText không hợp lệ, runtime tự
chuyển về Qwen. API diagnostics công bố backend và confidence nhưng chỉ công bố
chi tiết artifact/model khi bật `web.debug_routing`.

## Dữ liệu

File JSONL phải có các trường sau cho mỗi dòng:

```json
{"id":"route-001","split":"train","group":"passport-fee","question":"Lệ phí cấp hộ chiếu là bao nhiêu?","history":[],"scope":"in_scope","relation":"new_question"}
```

- `split`: `train`, `validation` hoặc `test`.
- `group`: định danh thủ tục/chủ đề/template. Một group không được xuất hiện ở
  nhiều split, nhằm ngăn leakage.
- `scope`: `in_scope`, `mixed` hoặc `out_of_scope`.
- `relation`: `new_question`, `follow_up` hoặc `ambiguous`; `out_of_scope` chỉ đi
  cùng `new_question`.
- `history`: danh sách message `{role, content}` giống API chat.

Dataset cần cân bằng các tình huống, có hard negative gần miền hành chính và
không được tạo test bằng cùng template với train. Golden hiện tại không đủ cân
bằng để dùng trực tiếp làm routing dataset.

## Huấn luyện và đánh giá

Cài extra tùy chọn rồi chạy:

```powershell
python -m pip install -e ".[routing]"
vigov rag train-router --dataset Data/routing/intents.jsonl --output-dir outputs/routing
vigov rag evaluate-router --dataset Data/routing/intents.jsonl --split test
```

Artifact gồm `intent-router.bin` và `intent-router.metadata.json`. Metadata lưu
taxonomy, threshold, hash dataset/model và tham số huấn luyện. Lệnh đánh giá trả
macro-F1, recall từng nhãn, confusion matrix, fallback rate, latency p50/p95 và
ước tính tỷ lệ giảm lượt gọi Qwen; lệnh thoát mã 2 nếu không đạt các quality gate
đã định nghĩa. Artifact dùng vector 32 chiều và bucket cố định để giữ model dưới
mục tiêu 20 MB; lệnh test artifact kiểm tra giới hạn này.

Chỉ đổi hai profile sang `routing_backend: hybrid` sau khi test độc lập đạt gate.
Để rollback, đặt lại `routing_backend: llm`; không cần đổi API hoặc xóa artifact.
