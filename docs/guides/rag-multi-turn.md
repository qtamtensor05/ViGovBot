# RAG nhiều lượt với routing v2 và signed state v3

Hướng dẫn này mô tả hợp đồng hội thoại hiện hành. Router dùng PhoBERT bốn head;
client phải gửi lại `conversation_state` do server trả về ở lượt trước trong map
`conversation_states` theo model. Không dùng
hợp đồng `scope/relation` v1 hoặc quy trình `qa_test_v4` cũ.

## Luồng xử lý

```text
Câu hỏi + history + conversation_state
  -> xác thực signed state
  -> PhoBERT: scope / flow / procedure / section
  -> trả menu làm rõ, từ chối, hoặc truy xuất
  -> FAISS theo mã thủ tục và section intent
  -> đóng gói evidence
  -> sinh và kiểm tra câu trả lời
  -> trả state mới cho client
```

Các nhánh chính:

- `rag_answer`: câu hỏi đủ rõ để truy xuất và trả lời.
- `clarify`: cần người dùng chọn thủ tục hoặc bổ sung thông tin.
- `abstain`: ngoài phạm vi hoặc không có bằng chứng phù hợp.

## Bảo toàn câu hỏi khi chọn menu

Khi một câu hỏi tạo menu thủ tục, state v3 lưu yêu cầu đang chờ gồm câu hỏi gốc,
section intent và ràng buộc chi tiết. Ở lượt chọn tiếp theo, server:

1. xác thực chữ ký state;
2. ánh xạ lựa chọn tới mã thủ tục trong menu đã phát hành;
3. khôi phục yêu cầu đang chờ;
4. bỏ qua bước định tuyến lại câu lựa chọn;
5. truy xuất theo đúng mã thủ tục và section intent đã khôi phục.

Cơ chế này ngăn câu trả lời bị lệch từ yêu cầu như “hồ sơ”, “thời hạn” hoặc
“bước 2” sang phần tổng quan chỉ vì lượt sau chỉ chứa số thứ tự menu.

## Trách nhiệm của client

- Gửi `history` đúng thứ tự với các role `user` và `assistant`.
- Gửi nguyên `conversation_state` gần nhất; không tự sửa payload hoặc chữ ký.
- Khi hiển thị menu, gửi lựa chọn trong phạm vi menu hiện hành.
- Thay state cũ bằng state mới trong mỗi response thành công.
- Khi state hết hạn hoặc bị từ chối, bắt đầu lại yêu cầu thay vì tự tái tạo state.

Payload tối thiểu:

```json
{
  "question": "2",
  "models": ["qwen-rag"],
  "histories": {
    "qwen-rag": [
      {"role": "user", "content": "Hồ sơ đổi giấy phép lái xe gồm gì?"},
      {"role": "assistant", "content": "Bạn muốn chọn thủ tục nào?"}
    ]
  },
  "conversation_states": {
    "qwen-rag": {"version": 3, "signature": "<server-signature>"}
  }
}
```

Ví dụ rút gọn nội dung state để minh họa nguyên tắc round-trip; client phải gửi
nguyên object state server đã trả, không tự tạo hoặc chỉ gửi hai trường trên.

## Evidence và câu trả lời

Runtime chỉ phát hành câu trả lời sau khi kiểm tra schema và quan hệ giữa `action`
với trạng thái evidence. Nếu không có chunk thực sự được đưa vào prompt, hệ thống
phải từ chối thay vì để model tự suy đoán. Với mục nội dung trải trên nhiều chunk,
prompt và hậu kiểm bảo toàn thứ tự fragment và phát hiện phần bằng chứng bị bỏ sót.

## Kiểm tra tập trung

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='src'
python -m unittest tests.test_server tests.test_shared_contracts tests.test_procedure_discovery
```

Các kiểm tra source không chứng minh model live, GPU hoặc Docker. Khi cần kết luận
chất lượng model, chạy quy trình trong [đánh giá QA/RAG](qa-rag-evaluation.md) và
ghi artifact vào `result/`.

Xem thêm [routing PhoBERT bốn head](four-head-routing.md) và
[kiến trúc hệ thống](../architecture/architecture.md).
