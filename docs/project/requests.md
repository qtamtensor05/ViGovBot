# Yêu cầu dự án

## TASK-20261003-07

- Ngày: 2026-10-03 (Asia/Saigon).
- Yêu cầu: triển khai phương án sửa routing đã đề xuất ở TASK-20261003-06.
- Phạm vi: schema routing theo nhánh, prompt phân loại, retry có lỗi/JSON cụ thể,
  adapter provider, chẩn đoán web và kiểm thử; giữ Qwen quyết định nhãn.
- Tiêu chí: JSON bị ràng buộc khi gọi model, retry không âm thầm sửa nhãn,
  hai JSON sai vẫn trả câu mặc định; web phân biệt fallback/mơ hồ thật;
  test offline và smoke Qwen thật có bằng chứng.
- Trạng thái: completed; 42 test offline đạt, 6 ca smoke Qwen thật hợp lệ và
  đúng nhãn ngay lần đầu; Ruff/pip check đạt. Chưa đo đáp án trên corpus thật
  hoặc gọi API OpenAI-compatible thật; cần restart web để nạp bản sửa.

## TASK-20261003-06

- Ngày: 2026-10-03 (Asia/Saigon).
- Yêu cầu: kiểm tra câu hỏi thủ tục ứng phó tràn dầu trên web và đề xuất giải pháp
  cho nghi vấn mất ngữ cảnh hoặc fallback.
- Phạm vi: kiểm tra đường truyền history; thử router Qwen thật với đúng câu hỏi,
  so sánh JSON mode với schema ràng buộc; không triển khai sửa hành vi production.
- Tiêu chí: có bằng chứng routing và phương án sửa ưu tiên, nêu giới hạn tái hiện.
- Trạng thái: completed; tái hiện fallback với đúng câu hỏi và history giả;
  schema trial hợp lệ ở hai kịch bản, đã ghi đề xuất và giới hạn kiểm chứng.

## TASK-20261003-05

- Ngày: 2026-10-03 (Asia/Saigon).
- Yêu cầu: xác thực Qwen có trả sai định dạng dẫn đến fallback hay không.
- Phạm vi: kiểm tra artifact Qwen thật, chạy lại validator hiện hành trên JSON
  đã lưu và phân biệt lỗi cú pháp với lỗi hợp đồng routing.
- Tiêu chí: xác định lượt fallback, JSON đầu/retry và nguyên nhân validator từ chối.
- Trạng thái: completed; artifact Qwen thật có 3 lượt fallback, đã tái kiểm tra
  JSON đầu/retry bằng validator hiện hành; nguyên nhân là sai hợp đồng routing.

## TASK-20261003-04

- Ngày: 2026-10-03 (Asia/Saigon).
- Yêu cầu: sửa lỗi web ở nhánh Qwen + RAG: `SQLite objects created in a thread
  can only be used in that same thread`.
- Phạm vi: sửa vòng đời/truy cập SQLite của `Retriever` để dùng an toàn từ thread
  xử lý HTTP, thêm kiểm thử hồi quy đa luồng và cập nhật hồ sơ kỹ thuật.
- Tiêu chí hoàn thành: truy hồi từ thread khác thread khởi tạo không lỗi; truy cập
  dùng chung được tuần tự hóa; toàn bộ test RAG/server liên quan thành công.
- Giả định: web tiếp tục dùng một `Retriever` read-only chung và xử lý chat tuần
  tự; không thay đổi schema corpus hoặc kết quả truy hồi.
- Trạng thái: completed; kết nối SQLite read-only cho phép dùng khác thread và
  Retriever tuần tự hóa truy cập; test hồi quy cùng 20 test liên quan đều đạt.

## TASK-20261003-03

- Ngày: 2026-10-03 (Asia/Saigon).
- Yêu cầu: giao diện web phải hiển thị và so sánh câu trả lời của Qwen base với
  Qwen sử dụng RAG cho cùng một câu hỏi.
- Phạm vi: mở rộng cấu hình model web với chế độ `base`/`rag`, triển khai nhánh
  gọi thẳng model không truy hồi, cấu hình sẵn hai lựa chọn Qwen, cập nhật UI,
  kiểm thử và tài liệu liên quan.
- Tiêu chí hoàn thành: chọn đồng thời hai chế độ trên web trả hai ô kết quả; nhánh
  base không gọi pipeline truy hồi, nhánh RAG vẫn trả nguồn; cấu hình được validate
  và có kiểm thử cho hai đường đi.
- Giả định: "Qwen base" là cùng model Ollama `qwen2.5:7b` nhận câu hỏi/lịch sử
  trực tiếp, không phải base checkpoint chưa instruction-tune.
- Trạng thái: completed; hai chế độ xuất hiện trong cấu hình mặc định, nhánh base
  bỏ qua truy hồi, nhánh RAG giữ nguồn; 19 test liên quan thành công.

## TASK-20261003-02

- Ngày: 2026-10-03 (Asia/Saigon).
- Yêu cầu: cập nhật nội dung tài liệu triển khai RAG theo mô hình RAG hiện tại.
- Phạm vi: đối chiếu `docs/trien-khai-rag-co-ban.md` với mã nguồn, cấu hình và
  kiểm thử hiện hành; cập nhật mô hình nhiều lượt, định tuyến/xét bằng chứng,
  giao diện web và cách vận hành liên quan. Không thay đổi hành vi ứng dụng.
- Tiêu chí hoàn thành: tài liệu mô tả đúng luồng RAG hiện tại, tham số và lệnh
  đang hỗ trợ; các liên kết/đường dẫn còn hợp lệ; kiểm tra Markdown và diff không
  có lỗi khoảng trắng.
- Giả định: "rag md" là `docs/trien-khai-rag-co-ban.md`, tài liệu vận hành RAG
  chính được README liên kết.
- Trạng thái: completed; tài liệu đã cập nhật, 16 liên kết tương đối hợp lệ và
  `git diff --check` thành công. Test RAG chưa chạy do môi trường thiếu `faiss`.

## TASK-20261003-01

- Ngày: 2026-10-03 (Asia/Saigon).
- Yêu cầu: tìm nguồn skill agent, bổ sung skill cho ViGovBot để mỗi task lớn
  lưu yêu cầu, triển khai, current stage, nhật ký lỗi; chờ lệnh dài hoàn tất
  và tránh đọc log liên tục.
- Phạm vi: quy trình agent và hồ sơ Markdown trong repository.
- Tiêu chí: có skill đúng định dạng, AGENTS.md dẫn chiếu, bốn hồ sơ được khởi
  tạo và quy tắc chờ phân biệt lệnh hữu hạn với server chạy liên tục.
- Trạng thái: completed; hai skill qua quick_validate.py, diff qua kiểm tra whitespace.
