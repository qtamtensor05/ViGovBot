# TASK-20261004-05 — in_progress

- Giai đoạn 1: đang chạy env/Scripts/python.exe -m vigovbot.qa_v4.audit --dataset Data/qa_test_v4/rag_tthc_three_1500 --out outputs/result_qa/evaluation_upgrade/source_review; session 2420.
- Audit kiểm tra hash PDF, trang và nguyên văn; tách riêng trạng thái semantic/human review, không tự duyệt Gold.
- Tiếp theo: mapping, CLI scoring, semantic judgments và benchmark comparison.
- Bằng chứng sẽ lưu ở outputs/result_qa/evaluation_upgrade/.

# TASK-20261004-04 — partial

- Đã hoàn tất BERTScore 944/944 cặp: P=0,890979; R=0,891960; F1=0,891086.
- Model xlm-roberta-large, CPU, batch 1, no-IDF, không rescale; 5 reference vượt 512 token.
- Session 59548 đã kết thúc exit 0; thời gian script 932,48 giây. Không còn job chấm đang chạy.
- Artifact: outputs/result_qa/supplemental_single_1500/; báo cáo chính đã thêm mục 9.
- Kiểm chứng: ID, điểm hữu hạn, aggregate và SHA-256 đầu vào đạt.
- Còn lại: mapping retrieval đã duyệt; audit 1.461/3.313 chunk khớp nội dung chỉ là ứng viên. Chưa công bố Recall@5/MRR@5.
- Bước tiếp: hoàn thiện đối chiếu tài liệu/trang/đoạn của corpus RAG đã chạy và duyệt mapping; không đổi corpus ngầm.

# TASK-20261004-03 — completed

- Đã tạo outputs/result_qa/bao-cao-single-1500.md, phân tích đủ 1.500 lượt.
- Kết quả: 1.499 thành công thực thi; 459 đúng nhãn (30,60%); điểm nghẽn routing.
- Kiểm chứng: ID khớp view/CSV/scores, câu hỏi/reference/nhãn khớp dataset; số tổng và liên kết báo cáo đạt.
- Còn lại trong phạm vi: không. Chưa chạy lại model hoặc chấm ngữ nghĩa; đề xuất cải thiện chưa triển khai.
- Hồ sơ và trạng thái các task trước được giữ bên dưới.

# Current stage - giai đoạn hiện tại

- Task hiện tại: TASK-20261004-02 (2026-10-04), completed.
- Giai đoạn: đã chuyển notebook/CLI sang bộ `rag_tthc_three_1500`.
- Đã xong: xác nhận 3 view x 1.500 lượt khớp query/case và chuỗi
  multi hợp lệ; xác định CLI chạy được khi chọn dataset/view tường minh.
- Đã xong triển khai: notebook dùng dataset mới và ba view; CLI có alias,
  default single view; tài liệu và test đã đồng bộ.
- Còn lại: không có trong phạm vi. Resume là cải tiến riêng nếu cần
  chạy qua nhiều phiên Colab.
- Bằng chứng: loader hiện hành chọn 1.500/1.500 query/case cho single,
  multi, coverage; `validate_sequence` cho multi thành công.
- Kiểm chứng: 13 test QA/Colab đạt; Ruff, notebook artifact và diff-check đạt.
- Trở ngại: không có; chưa chạy model thật/4.500 lượt vì không
  thuộc phạm vi cập nhật cấu hình.

## Mục trước - TASK-20261004-01

- Task hiện tại: TASK-20261004-01 (2026-10-04), partial.
- Phạm vi đã chốt: chỉ ZIP thứ hai, 23 lượt; 4 lỗi generation, 7 lỗi dây chuyền.
- Đã sửa: schema generation, retry giới hạn, diagnostics, giữ câu hỏi gốc khi viết lại.
- Kiểm chứng: 54 test routing/QA/provider/pipeline/server/config đạt; bổ sung
  test giới hạn retry context, chạy lại 34 test routing/QA/provider đều đạt.
  Sau kiểm tra tính độc lập reference_history, 10 test QA v4 đạt; Ruff và
  git diff --check đạt.
  Session 15822 đã hoàn tất exit 0. ZIP gốc không bị ghi đè.
- Báo cáo: docs/project/colab-rag-2-assessment.md; 4/23 action đúng nhãn cục bộ.
- Còn lại: chạy smoke Qwen thật trên Colab với commit mới; xác nhận chất lượng
  ngữ nghĩa/retrieval, chưa thể suy ra các lỗi nội dung đã hết từ test mock.
- Trở ngại kiểm chứng model thật: localhost:11434 từ chối kết nối; không có
  runtime Colab kết nối trong phiên này. Không cần sửa notebook để nhận code mới.

## Mốc trước

- Cập nhật: 2026-10-03 (Asia/Saigon).
- Task: TASK-20261003-09.
- Giai đoạn: hoàn tất TASK-20261003-09, gồm yêu cầu bổ sung notebook Colab.
- Đã làm: runner tính ETA toàn bộ tập đã chọn từ tốc độ trung bình thực tế; hiển
  thị thời gian còn lại và giờ dự kiến xong trên terminal/log; báo cáo ghi mốc
  bắt đầu/kết thúc và phương pháp; cập nhật test và README QA v4.
- Còn lại: không còn hạng mục thuộc yêu cầu hiện tại.
- Trở ngại: chưa ghi nhận trở ngại ngăn hoàn tất task.
- Bước tiếp theo: commit/push mã nguồn rồi đặt `GIT_REF` tới commit đó khi chạy
  Colab; chạy benchmark thật nếu cần quan sát độ ổn định ETA trên toàn tập.
- Bằng chứng: QA v4 đạt 8 test, Colab runtime đạt 3 test; Ruff đạt; notebook tái
  sinh chứa `RUN_REPORT`, thông báo ETA và phần đọc báo cáo; diff-check đạt.
- Trạng thái ứng dụng: ETA áp dụng cho `qa-v4 run` và hiện trực tiếp trong notebook
  RAG Colab; không thay đổi truy hồi, sinh câu trả lời, dataset hoặc cách chấm điểm.
