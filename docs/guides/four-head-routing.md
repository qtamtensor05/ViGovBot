# Routing bốn nhóm nhãn

Luồng mặc định (`conversation.routing_contract: v2`, `routing_backend: llm`):

```text
Tin nhắn + trạng thái → Có chọn trực tiếp mục trong menu đang hiển thị?
  Có → xác thực menu và lựa chọn bằng code, không gọi router
  Không → model base phân loại bốn nhóm nhãn
    OUT_OF_SCOPE → thông báo phạm vi
    IN_SCOPE / MIXED_SCOPE → giải quyết từng thủ tục và mục được hỏi
      nhiều ứng viên cho một thủ tục → menu thủ tục
      một thủ tục, sections=[] → menu section có Tổng quan
      thủ tục và section rõ → truy hồi đúng mã và mục, trả lời theo bằng chứng
      không tìm thấy → thông báo thiếu dữ liệu
→ cập nhật trạng thái, thay thế menu cũ
```

## Hợp đồng router

- `scope`: `IN_SCOPE`, `OUT_OF_SCOPE`, `MIXED_SCOPE`.
- `conversation`: `NEW`, `FOLLOW_UP`; không có nhãn `ambiguous`.
- `mixed_procedures`: boolean, chỉ true khi yêu cầu nhiều thủ tục khác nhau.
- `sections`: danh sách nhãn; `OVERVIEW` chỉ khi thực sự yêu cầu tổng quan.
- Điều phối: `query`, `needs_clarification`, `clarification`, `requests`.
- Mỗi request chứa `procedure`, `query`, `sections`, giữ liên kết riêng cho từng
  thủ tục. Nhiều ứng viên không đồng nghĩa người dùng muốn hỏi nhiều thủ tục.

JSON sai được sửa một lần; vẫn sai thì hỏi làm rõ. HTTP/model lỗi được báo riêng.
Router v2 chờ JSON đầy đủ, không dùng early exit của hợp đồng v1. Câu nối tiếp
thiếu trạng thái xác thực hoặc không xác định được đối tượng sẽ hỏi làm rõ.

## Nhãn section và dữ liệu hiện có

| Nhãn | Nhóm corpus |
|---|---|
| GENERAL_INFORMATION, AUTHORITY | metadata_identity |
| DOSSIER, FORM | required_documents |
| PROCEDURE | procedure_step |
| PROCESSING_TIME, FEE, SUBMISSION_METHOD | submission_deadline_fee |
| LEGAL_BASIS | legal_basis |
| ELIGIBILITY, OTHER_CONTENT | other |
| OVERVIEW | Các nhóm của thủ tục |

Rà soát metadata hiện có xác nhận sáu nhóm lưu trữ; phần điều kiện có heading
`YÊU CẦU, ĐIỀU KIỆN THỰC HIỆN`, biểu mẫu xuất hiện trong bảng hồ sơ. Menu chỉ
hiện FORM/ELIGIBILITY khi tìm thấy dấu hiệu tương ứng trong dữ liệu thủ tục.
Không tạo nhãn RESULT độc lập khi chưa có ánh xạ được xác minh; dùng nội dung
khác cho yêu cầu chưa thuộc nhóm cụ thể. Không thay đổi chunk hoặc chỉ mục.
Phí, thời hạn, cách nộp có nhãn riêng nhưng cùng nhóm truy hồi. Mỗi thủ tục nhận
tối đa `top_k` chunk, phân bổ giữa các nhóm yêu cầu; context nhiều thủ tục xen kẽ
để dành bằng chứng cho từng thủ tục trước khi hết ngân sách prompt.

## API và giao diện

`/api/chat` và `/api/chat/stream` giữ trường answer/sources và cách streaming.
Response bổ sung `classification`, `menu`, `conversation_state` theo từng model.
Request gửi lại `conversation_states: {model_id: state}` cùng histories.
Nút menu gửi `selections: {model_id: {menu_id, option_id}}`; chỉ tác động model
của menu đó. Số, mã hoặc tên khớp chính xác vẫn được chấp nhận qua question.
Câu tự nhiên phải qua router dù có nhắc tới từ trong menu.

Sau khi router chạy, section được người dùng nêu rõ như “Trình tự thực hiện”
được dùng thay section cũ trong trạng thái. Yêu cầu liệt kê “Các thủ tục …” dùng
catalog tên trước semantic search. Câu từ chối danh sách giữ menu; câu xác nhận
chung không chọn thay người dùng; “trường hợp khác” mở các biến thể cùng tên và
loại thủ tục vừa xem.

Với mô tả khái quát chưa chứa toàn bộ tên, catalog so khớp cụm hành động–đối
tượng và xếp hạng theo thứ tự/khoảng cách từ khóa. Có ứng viên catalog thì câu hỏi
được giữ trong phạm vi thủ tục ngay cả khi model base gán nhầm `OUT_OF_SCOPE`;
semantic retrieval không được dùng để tạo menu thủ tục khi catalog đã có kết quả.

Trạng thái được ký, gắn model, corpus và lịch sử chính xác. Số ngoài danh sách
giữ menu và báo lỗi; trạng thái cũ/sửa đổi không được dùng để chọn. Client chỉ
gửi text và lịch sử được hỗ trợ bởi cache 256 trạng thái gần nhất trong process.
Sau restart hoặc hết cache, client này phải nêu lại thủ tục; client gửi state
cũng phải chọn lại sau restart do khóa ký mới. Không lấy mã từ câu trả lời cũ
chưa xác thực làm nguồn có thẩm quyền.

## Cấu hình và thay model

Trong `llm`, đặt `routing_model` và `routing_base_url` độc lập model trả lời.
Hiện dùng `qwen2.5:7b` qua Ollama, context 4096, tối đa 768 token đầu ra router.
Đây là model base xuất bốn nhóm nhãn, chưa phải model bốn head đã huấn luyện.
Model thay thế qua Ollama phải tuân thủ cùng schema. Provider khác cần adapter
cho `router_fn`; phần điều phối không phụ thuộc nội bộ model.

FastText/hybrid bảy nhãn chỉ dùng khi đặt rõ `routing_contract: v1`; config v2
từ chối backend đó. Xem [router cũ](intent-router.md). Dataset golden và adapter
không bị thay đổi; test hồi quy nằm trong `tests/test_four_head_routing.py`.

Với Compose bind mount source/config, dùng `docker compose restart web` sau khi
sửa. Không cần build lại image hoặc embedding cho thay đổi này.
