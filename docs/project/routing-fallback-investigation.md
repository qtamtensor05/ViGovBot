# Điều tra fallback routing — TASK-20261003-06

> Đây là kết quả trước bản sửa. TASK-20261003-07 đã triển khai schema/prompt/retry
> và chẩn đoán web; 6 ca smoke Qwen thật sau sửa đều đạt ngay lần đầu. Xem
> implementation-history.md và artifact routing_implemented_*.json.

## Kết quả kiểm tra ngày 2026-10-03

- Model Ollama cục bộ: qwen2.5:7b; cấu hình web hiện hành, temperature 0,
  seed 42, num_ctx 8192, num_predict 512; tokenizer cache cục bộ.
- Đúng câu hỏi tràn dầu trong ảnh, không history: JSON đầu chọn follow_up,
  query và clarification đều có nội dung. Validator báo thiếu history;
  retry sửa thành new_question và clarification rỗng, không fallback.
- Cùng câu hỏi, history giả gồm trao đổi về cấp hộ chiếu: cả hai lần chọn
  follow_up, query và clarification đều có nội dung. Validator từ chối cả hai;
  marker invalid_routing_after_retry và câu mặc định xuất hiện, tái hiện fallback.
- Schema anyOf theo nhánh với query/clarification bắt buộc đúng quy tắc:
  cả hai kịch bản hợp lệ ngay lần đầu. Có history vẫn chọn follow_up dù câu hỏi
  độc lập/chuyển chủ đề; schema sửa cấu trúc, không bảo đảm đúng phân loại ngữ nghĩa.
- Artifact: outputs/qa_v4/oil_spill_routing_probe.json và
  outputs/qa_v4/oil_spill_routing_probe_history.json.
- Lệnh: env\Scripts\python scripts\probe_oil_spill_routing.py và cùng lệnh
  với --with-history; cả hai thành công. Retriever rỗng có chủ ý: no_context
  trong probe không phải bằng chứng corpus thiếu tài liệu.
- Không có payload/history/raw response gốc của ảnh nên chưa xác nhận tuyệt đối
  nguyên nhân lượt cũ; đã tái hiện cơ chế lỗi với đúng câu hỏi và history giả.

## Kiểm tra web

- UI lưu history riêng theo model trong RAM và gửi histories[model_id] mỗi lượt.
  Backend validate rồi truyền đúng history vào answer_question. Không thấy lỗi
  bỏ history trong đường đi mã hiện tại; tải lại trang sẽ xóa history do không lưu bền.
- Backend chỉ trả answer/action/sources/latency, bỏ raw_routing, decision_reason
  và fallback_reason; fallback hợp lệ không được ghi như exception.
- UI đưa cả câu fallback vào history, có thể ảnh hưởng lượt sau; mức ảnh hưởng
  chưa đo. decision_reason hiện dùng ambiguous_question cho cả fallback và mơ hồ thật.

## Đề xuất ưu tiên

1. Dùng JSON Schema ràng buộc theo nhánh trong Ollama format, loại follow_up
   khi history rỗng. Vẫn giữ validator, một retry và fallback sau hai JSON sai.
   Với provider OpenAI-compatible phải xác nhận hỗ trợ json_schema; adapter
   hiện chỉ hỗ trợ json_object, không được âm thầm bỏ schema.
2. Bổ sung prompt phân loại: câu có tên thủ tục + yêu cầu rõ là new_question
   kể cả mở đầu "Tôi đang tìm hiểu" và kể cả có history chủ đề khác; thêm ví dụ
   đúng new_question/follow_up/ambiguous. Không dùng code đoán nhãn thay Qwen.
3. Retry cung cấp JSON bị từ chối, lỗi validator cụ thể và ví dụ sửa phù hợp;
   gửi như dữ liệu, giữ budget context. Hiện retry chỉ nhắc lại quy tắc chung.
4. Trả chẩn đoán tối thiểu trên web: fallback_reason, routing_attempts,
   decision_reason, relation; hiển thị phân biệt lỗi routing và hỏi làm rõ thật.
   Lưu raw response trong chế độ debug có kiểm soát để điều tra đúng lượt.
5. Phân biệt fallback kỹ thuật khỏi câu hỏi làm rõ ngữ nghĩa khi dựng history;
   giữ câu hỏi người dùng để hỗ trợ lượt bổ sung, tránh đưa câu fallback như
   thông tin thủ tục. Cần thiết kế riêng metadata thay vì làm mất lượt user.

## Kiểm chứng trước triển khai

- Bộ câu hỏi thật: tên thủ tục dài, không history, có history đổi chủ đề,
  follow-up thật, mơ hồ thật và ngoài phạm vi; kiểm cả nhãn và truy vấn độc lập.
- Đo tỷ lệ JSON sai đầu/retry, fallback, phân loại sai và latency. Hai kịch bản
  schema đạt ở đây chỉ là smoke test, chưa chứng minh độ ổn định toàn bộ.
- Sau router, chạy corpus thật để kiểm tra nguồn, đúng hàng trực tuyến, thời hạn,
  phí và mô tả; không dùng dữ liệu giả để suy ra đáp án thủ tục.
