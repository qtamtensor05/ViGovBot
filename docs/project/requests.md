# Yêu cầu dự án

## TASK-20261004-02

- Ngày: 2026-10-04 (Asia/Saigon).
- Yêu cầu: chuyển luồng đánh giá QA/Colab sang bộ
  `rag_tthc_three_1500` (người dùng gọi `test_rag_three_1500`) và làm rõ
  option chạy riêng các bộ single, multi và coverage.
- Phạm vi: đối chiếu cấu trúc dataset, cập nhật alias/giá trị mặc định
  phù hợp cho CLI và notebook Colab, tài liệu hóa lệnh chạy/chấm từng
  view; không chạy 4.500 lượt model thật trong task này.
- Tiêu chí: ba view 1.500 lượt chọn được tường minh; run và score dùng
  cùng dataset/view/split; notebook sinh lại và kiểm thử CLI liên quan đạt.
- Giả định: thư mục chuẩn trong repository là
  `Data/qa_test_v4/rag_tthc_three_1500`; `test_rag_three_1500` là tên người
  dùng dùng để chỉ cùng bộ dữ liệu.
- Bổ sung: người dùng yêu cầu triển khai luôn thay đổi cho notebook.
  Cập nhật dataset/view mặc định, alias CLI, tài liệu và test; không
  thay đổi cơ chế resume của runner trong phạm vi này.
- Trạng thái: completed; notebook đã chuyển mặc định sang bộ ba tập,
  dropdown có single/multi/coverage, CLI có alias và default view phù hợp;
  test và kiểm tra notebook sinh lại đều đạt.

## TASK-20261004-01

- Ngày: 2026-10-04 (Asia/Saigon).
- Yêu cầu: đánh giá mẫu Colab và giải quyết lỗi; người dùng điều chỉnh chỉ xét
  `2000_main_smoke_rag_2-20261003T171220Z-1-001.zip`, bỏ ZIP đầu vì là RAG cũ.
- Phạm vi: phân tích 23 lượt trong ZIP thứ hai, sửa lỗi đầu ra có bằng chứng,
  kiểm thử hồi quy và báo cáo giới hạn của mẫu chưa hoàn tất.
- Tiêu chí: xác định lỗi gốc/lỗi dây chuyền; sửa hợp đồng generation và lưu
  chẩn đoán; kiểm chứng offline, không suy ra chất lượng toàn bộ 2.000 câu.
- Trạng thái: partial; đã đánh giá 23 lượt, sửa schema/retry/diagnostics và
  kiểm thử offline đạt; chưa chạy lại Qwen/Colab để xác nhận chất lượng ngữ nghĩa.

## TASK-20261003-09

- Ngày: 2026-10-03 (Asia/Saigon).
- Yêu cầu: cập nhật mã nguồn đánh giá QA RAG để tính thời gian dự kiến hoàn
  thành toàn bộ bộ test.
- Phạm vi: runner QA v4 tuần tự, hiển thị tiến độ trên terminal tương tác và
  log thường, báo cáo tổng kết cùng kiểm thử hồi quy; không thay đổi nội dung
  dataset, cách gọi RAG hoặc cách chấm điểm.
- Tiêu chí: sau mỗi ca đã xử lý có thời gian còn lại và giờ hoàn thành dự kiến
  dựa trên tốc độ trung bình thực tế; báo cáo cuối ghi thời điểm bắt đầu/kết thúc
  và phương pháp ước lượng; kiểm thử liên quan thành công.
- Giả định: "tổng bộ test" là toàn bộ danh sách `queries` được chọn bởi lệnh
  `python -m vigovbot.qa_v4 run`, sau khi áp dụng view/split/limit.
- Bổ sung: cập nhật cả notebook Colab QA RAG và nguồn sinh notebook để hiển thị
  ETA của runner, chỉ rõ file báo cáo thời gian và đọc tóm tắt sau khi chạy.
- Trạng thái: completed; runner và notebook Colab đã đồng bộ ETA/báo cáo thời
  gian; 8 test QA v4, 3 test Colab, Ruff và kiểm tra artifact đều đạt.

## TASK-20261003-08

- Ngày: 2026-10-03 (Asia/Saigon).
- Yêu cầu: cập nhật tài liệu theo nội dung triển khai RAG hiện tại.
- Phạm vi: đồng bộ hướng dẫn vận hành, README dự án, kiến trúc, roadmap và README
  module RAG với web UI/API, Qwen base so với Qwen + RAG, hội thoại nhiều lượt,
  routing schema/fallback/diagnostics và truy hồi an toàn qua thread HTTP.
- Tiêu chí: không còn mô tả sai rằng chưa có web hoặc chỉ hỏi đáp một lượt; tài
  liệu module liệt kê đủ cấu hình/đầu ra hiện tại; liên kết hợp lệ và diff sạch.
- Giả định: cập nhật tài liệu theo mã nguồn và bằng chứng hoàn tất TASK-20261003-07,
  không thay đổi hành vi ứng dụng hoặc chạy lại model/corpus.
- Trạng thái: completed; sáu tài liệu kỹ thuật đã đồng bộ, 45 liên kết tương đối
  hợp lệ và `git diff --check` thành công.

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

## TASK-20261004-03

- Ngày: 2026-10-04 (Asia/Saigon).
- Yêu cầu: phân tích kết quả single_1500 và tạo báo cáo Markdown tại thư mục kết quả.
- Phạm vi: outputs/result_qa/three1500_single_smoke_rag_1; kiểm tra tính đầy đủ, cách chấm, thống kê và mẫu lỗi.
- Tiêu chí: báo cáo có số liệu đối chiếu artifact, giới hạn và khuyến nghị có bằng chứng.
- Giả định: output/result_qa trong yêu cầu là outputs/result_qa thực tế.
- Trạng thái: completed; báo cáo đã tạo, đối chiếu đủ 1.500 ID và các tổng hành vi, kiểm tra liên kết và UTF-8 đạt.

## TASK-20261004-04

- Yêu cầu: chấm bổ sung các chỉ số cho single_1500 từ artifact đã lưu.
- Phạm vi: BERTScore và kiểm tra tính khả thi mapping retrieval; không chạy lại Qwen.
- Tiêu chí: lưu điểm thực tế cùng cấu hình, kiểm chứng mẫu số; chỉ công bố retrieval khi mapping đủ tin cậy; cập nhật báo cáo.
- Trạng thái: partial; đã chấm BERTScore đủ 944 cặp và cập nhật báo cáo. Retrieval chưa có mapping đã duyệt, không công bố Recall@5/MRR@5.

## TASK-20261004-05

- Yêu cầu: thực hiện theo thứ tự các bước hoàn thiện đánh giá RAG, AI duyệt dựa trên Data/pdf gốc.
- Phạm vi: single_1500; duyệt nguồn/case, mapping retrieval, CLI metric, chấm ngữ nghĩa, provenance/citations và cấu hình so sánh baseline/RAG/oracle.
- Tiêu chí: artifact duyệt truy vết được; không nhầm AI review với human gold; metric có mẫu số và mapping kiểm chứng; test và tài liệu tái lập; chạy phần khả thi, nêu rõ phần cần runtime model.
- Trạng thái: in_progress.
