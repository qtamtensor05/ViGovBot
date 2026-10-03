# Yêu cầu dự án

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
