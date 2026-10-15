# Yêu cầu dự án

## TASK-20261015-08

- Ngày tiếp nhận: 2026-10-15.
- Yêu cầu: chia rõ các cấu hình theo thư mục chức năng và sửa toàn bộ vị trí
  đang tham chiếu đến đường dẫn cấu hình cũ.
- Phạm vi: kiểm kê YAML và người dùng của chúng; tổ chức lại cấu hình training,
  ingestion và RAG; cập nhật code, script, notebook, test và tài liệu; giữ khả
  năng đọc artifact/run lịch sử và không thay đổi nội dung khoa học của cấu hình.
- Tiêu chí hoàn thành: không còn tham chiếu hoạt động tới đường dẫn YAML phẳng
  cũ; các loader giải quyết đúng đường dẫn tương đối sau khi di chuyển; test và
  static check đạt; không chạy training hoặc tải model.
- Trạng thái: completed; cấu hình đã chia theo ingestion/RAG/training, toàn bộ
  tham chiếu hoạt động đã chuyển sang đường dẫn mới; 157 test pass, 1 optional
  skip và static checks đạt. Không chạy training hoặc tải model.

## TASK-20261007-08

- Ngày: 2026-10-07 (Asia/Saigon).
- Yêu cầu: lưu kết quả phân tích và so sánh RAG vs Base của bộ dữ liệu `tthc_test_case_v1`
  thành tài liệu Markdown trong thư mục `docs/`.
- Phạm vi: tạo tài liệu báo cáo `docs/bao-cao-danh-gia-rag-vs-base-tthc-v1.md`,
  cập nhật bảng mục lục `docs/README.md`, liên kết đầy đủ artifact và số liệu kiểm chứng;
  không sửa đổi dữ liệu gốc.
- Tiêu chí: báo cáo đầy đủ phân tích tổng quan, thông lượng, điểm số text similarity
  (BLEU, ROUGE, BERTScore), action accuracy, retrieval metrics và phân tích chi tiết
  theo các nhóm `expected_action`, `noise`, `interaction`, `difficulty`; cập nhật
  hồ sơ task journal đúng quy định.
- Trạng thái: completed; báo cáo đã tạo tại `docs/bao-cao-danh-gia-rag-vs-base-tthc-v1.md`,
  mục lục `docs/README.md` đã cập nhật.

## TASK-20261007-07

- Ngày: 2026-10-07 (Asia/Saigon).
- Yêu cầu: sửa baseline Qwen không retrieval để dùng JSON Schema ràng buộc và
  retry một lần giống luồng RAG, giảm lỗi `Invalid structured answer/action`.
- Phạm vi: thay hợp đồng sinh baseline, lưu diagnostics, bổ sung unit test và
  smoke model thật với output mới; không ghi đè artifact baseline 1.000 ca cũ.
- Tiêu chí: schema chỉ cho phép answer không rỗng và năm action hợp lệ; output
  sai được retry đúng một lần; hai lần sai vẫn là failure có diagnostics; test,
  Ruff và smoke thật đạt.
- Trạng thái: completed; schema/retry/diagnostics đã triển khai, test và smoke
  Qwen thật 20/20 đạt, artifact baseline cũ không bị ghi đè.

## TASK-20261007-06

- Ngày: 2026-10-07 (Asia/Saigon).
- Yêu cầu: sửa lệnh chấm `tthc_test_case_v1` bị người dùng ngắt tại corpus BLEU
  trong SacreBLEU và cung cấp lại lệnh chấm chạy được.
- Phạm vi: tái hiện riêng bước lexical trên 1.000 prediction đã hoàn tất, xác
  định nguyên nhân hiệu năng, sửa evaluator kèm kiểm thử; sau đó smoke chấm thực.
- Tiêu chí: lexical score hoàn tất trong thời gian hợp lý, không đổi định nghĩa
  metric; test evaluator và kiểm tra mã đạt; không tự chạy BERTScore toàn tập nếu
  người dùng chưa yêu cầu tiếp tục chờ job dài.
- Trạng thái: completed; đã loại log cảnh báo lặp mà không đổi cách tính BLEU,
  thêm tiến trình phase và batch size BERTScore, lexical full hoàn tất 3,70 giây.

## TASK-20261007-05

- Ngày: 2026-10-07 (Asia/Saigon).
- Yêu cầu: thiết lập môi trường đúng với dự án trên máy hiện tại, chạy đánh giá
  QA RAG cho 1.000 ca test trong `Data/qa_test/tthc_test_case_v1/data/rag`, chấm
  theo evaluator tại `Data/qa_test/tthc_test_case_v1/evaluation`, và cung cấp
  lệnh chạy nhiều luồng tận dụng cấu hình máy.
- Phạm vi: kiểm tra phần cứng/phần mềm, cài Python/dependency/Ollama/model cần
  thiết, tích hợp bộ dữ liệu v2 với RAG hiện hành mà không đưa gold vào inference,
  chạy smoke rồi toàn bộ test nếu smoke đạt, chấm các metric có dữ liệu thực và
  lưu artifact có thể tái lập.
- Tiêu chí hoàn thành: môi trường `pip check` đạt; CUDA/model/corpus/RAG hoạt động;
  prediction đủ 1.000 ID hoặc báo chính xác lỗi còn lại; evaluator sinh score;
  lệnh run/score nhiều luồng và cấu hình máy được ghi rõ.
- Giả định: “evalue” là thư mục `evaluation`; chế độ đánh giá chính là
  `reference_history` theo README bộ dữ liệu; semantic accuracy/completeness/
  faithfulness chỉ có khi có judgments, không tự suy từ lexical metric.
- Bổ sung: người dùng yêu cầu dừng full run tự động và chỉ bàn giao câu lệnh có
  progress/ETA để tự chạy và quan sát trên terminal.
- Trạng thái: partial; môi trường/cấu hình/smoke đã hoàn tất, full run được dừng
  theo yêu cầu ở 36 dòng đã ghi và chưa chấm toàn bộ 1.000 ca.

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

## TASK-20261005-01

- Yêu cầu: đánh giá hai kết quả mới multi và cover đã lưu; không chạy lại RAG.
- Thư mục thực tế: outputs/result_qa/multi và outputs/result_qa/cover.
- Tiêu chí: đối chiếu ID/dataset, điểm số, lỗi, giới hạn hội thoại và báo cáo Markdown.
- Trạng thái: completed; đã tạo báo cáo multi/cover và kiểm chứng ID, nhãn, reference, số tổng.

## TASK-20261005-02

- Yêu cầu: chấm bổ sung BERTScore, retrieval và đúng nội dung cho multi/cover nếu dữ liệu cho phép, không chạy lại RAG.
- Trạng thái: partial; BERTScore hoàn tất multi 1.143/cover 1.112 cặp. Document Recall@5/MRR@5 có trên tập nguồn xác minh được; semantic đã duyệt 360 multi + 3 cover. Chưa có evidence-unit retrieval và độ đúng nội dung toàn tập; cover thiếu 387 lượt. Báo cáo outputs/result_qa/bao-cao-bo-sung-multi-cover.md.


## TASK-20261005-03

- Yêu cầu: tổng kết ba kết quả single/multi/cover, tính kết quả cuối hiện có, giải thích cách tính từng chỉ số và có sử dụng AI chấm hay không.
- Phạm vi: tổng hợp offline, không chạy lại RAG/BERT; giữ riêng mẫu số và giới hạn của ba view. Không tự đặt composite score.
- Tiêu chí: bảng điểm từng bộ và phép tổng hợp truy vết được; công thức, AI provenance, mức độ hoàn tất và Markdown báo cáo.
- Trạng thái: in_progress.

## TASK-20261006-01

- Ngày: 2026-10-06 (Asia/Saigon).
- Yêu cầu: dọn `outputs/result_qa` vì có quá nhiều báo cáo đánh giá; rút gọn nội
  dung dư thừa và tạo một bản tổng kết rõ kết quả, ảnh hưởng và đánh giá của cả
  ba bộ single/multi/coverage.
- Phạm vi: kiểm kê artifact hiện có; giữ dữ liệu/chứng cứ cần tái lập, hợp nhất
  phần trình bày bị trùng và loại các báo cáo trung gian dư thừa trong thư mục
  kết quả. Không chạy lại RAG hoặc tự bổ sung điểm chưa có.
- Tiêu chí hoàn thành: có một báo cáo chính chỉ rõ từng loại chỉ số, mẫu số,
  nguồn/provenance và giới hạn; danh sách file sau dọn dễ hiểu; các liên kết và
  số liệu được kiểm chứng từ artifact còn giữ.
- Giả định: "3 bộ test" là single, multi và coverage của
  `rag_tthc_three_1500`; file dữ liệu gốc và bằng chứng chi tiết được ưu tiên giữ
  hơn các bản báo cáo Markdown trung gian.
- Bổ sung 06/10/2026 (người dùng chọn): lưu bản tóm tắt thành
  `outputs/result_qa/tong-hop-danh-gia.md` làm báo cáo chính; xóa 3 báo cáo
  `bao-cao-*`, README supplemental, cache/packet/mapping_candidates trung gian,
  `source_review` v1, ảnh duyệt PNG, log và script `*.py` trong thư mục kết quả.
  Giữ nguyên dữ liệu gốc của run (predictions/scores/comparison/config) và file
  kiểm chứng/provenance/retrieval_verified/judgments/BERTScore. Thư mục bị
  gitignore nên xóa là không khôi phục được qua git.
- Trạng thái: completed.

## TASK-20261006-02

- Ngày: 2026-10-06 (Asia/Saigon).
- Yêu cầu: liệt kê cụ thể các mẫu câu cần đa dạng hóa trong bộ test
  `rag_tthc_three_1500`, lập danh sách ca Gold cần duyệt, và gợi ý thay đổi để đa
  dạng hóa tập test.
- Phạm vi: phân tích offline `cases.jsonl` và artifact kết quả đã có; tạo báo cáo
  và danh sách CSV trong `outputs/testset_review/`. Không sửa dataset, không chạy
  lại RAG, không tự duyệt/đổi Gold.
- Tiêu chí hoàn thành: bảng mẫu câu theo bộ/nhãn có số lượng và ví dụ ID; danh
  sách ca Gold cần duyệt có lý do và mức ưu tiên; gợi ý đa dạng hóa có ví dụ cụ thể
  cho từng mẫu; số liệu được tính lại từ dữ liệu.
- Giả định: "mẫu câu" xác định bằng cách thay tên thủ tục/số trong câu hỏi bằng
  placeholder; tiêu chí chọn ca Gold dựa trên trạng thái verification và tín hiệu
  bất thường, không phải phán quyết đúng/sai.
- Trạng thái: completed.

## TASK-20261006-03

- Ngày: 2026-10-06 (Asia/Saigon).
- Yêu cầu: thay đổi và cập nhật các case trong `rag_tthc_three_1500` để câu hỏi
  đa dạng hơn dựa trên báo cáo rà soát mẫu câu đã tạo.
- Phạm vi: sửa cách diễn đạt trường `question` trong `cases.jsonl`, ưu tiên các
  khung lặp cao; giữ nguyên ID, bộ/view, lịch sử hội thoại, nhãn hành động, Gold,
  required facts, evidence và provenance. Đồng bộ checksum/báo cáo validation và
  hàng đợi human review nếu định dạng hiện hành yêu cầu. Không chạy lại RAG và
  không tự thay đổi/duyệt Gold.
- Tiêu chí hoàn thành: giảm rõ rệt mức tập trung của các mẫu lặp cao; câu viết lại
  giữ cùng ý định và hành vi mong đợi; 1.500 ID mỗi view và chuỗi multi vẫn hợp lệ;
  không sinh câu hỏi trùng trong single; có số liệu trước/sau và kiểm thử dataset.
- Giả định: chỉ đa dạng hóa bề mặt câu hỏi, không thêm dữ kiện tình huống mới có
  thể làm đổi Gold; các biến thể typo/no-diacritics hiện có phải giữ đúng loại.
- Bổ sung khi triển khai: để hội thoại multi nhất quán, đồng bộ message `role=user`
  trong history với câu hỏi mới của lượt trước; giữ nguyên toàn bộ message assistant/Gold.
- Trạng thái: completed.

## TASK-20261007-01

- Ngày: 2026-10-07 (Asia/Saigon).
- Yêu cầu: thiết lập môi trường cần thiết trên máy hiện tại để chạy đánh giá RAG
  với bộ test `rag_tthc_three_1500`.
- Phạm vi: kiểm tra phần cứng/phần mềm và dữ liệu sẵn có; tạo môi trường Python,
  cài dependency phù hợp; chuẩn bị model/dịch vụ và corpus/index theo cấu hình nếu
  còn thiếu; xác minh bằng kiểm tra dataset và một smoke run có giới hạn. Không chạy
  toàn bộ 4.500 lượt nếu chưa được yêu cầu.
- Tiêu chí hoàn thành: lệnh QA v4 nhận đúng ba view, dependency import được, backend
  sinh và tài nguyên retrieval sẵn sàng, smoke run/score thực tế tạo artifact hoặc
  ghi rõ trở ngại bên ngoài còn lại cùng lệnh tiếp tục.
- Giả định: "chạy đánh giá RAG" nghĩa là chạy pipeline hiện tại trong repository
  (không chỉ chấm lại prediction cũ); ưu tiên cấu hình Windows và GPU hiện tại,
  không sửa nội dung dataset hay ghi đè artifact đánh giá cũ.
- Trạng thái: completed; môi trường Python/Ollama/model/corpus đã sẵn sàng, ba
  view được xác minh và smoke RAG + score một ca chạy thành công.

## TASK-20261007-02

- Ngày: 2026-10-07 (Asia/Saigon).
- Yêu cầu: đánh giá khả năng tăng tốc benchmark `rag_tthc_three_1500` trên máy
  hiện tại bằng runner song song, embedding/retrieval GPU, serving vLLM/TGI và
  BERTScore/LLM-as-a-judge song song.
- Phạm vi: khảo sát code, phần cứng/runtime và tài liệu chính thức hiện hành;
  xác định hạng mục khả thi, giới hạn VRAM/Windows và thứ tự triển khai an toàn.
  Chưa thay đổi runner, môi trường CUDA hay backend serving trong bước đánh giá này.
- Tiêu chí: kết luận riêng cho single/coverage/multi, Ollama concurrency,
  embedding/FAISS, vLLM và scoring; không đưa cam kết tốc độ khi chưa benchmark.
- Trạng thái: completed; đã xác định runner và retriever đang khóa tuần tự, GPU
  16 GB có thể triển khai concurrency thận trọng và CUDA scoring, còn vLLM cần
  WSL2/Linux và không phải bước ưu tiên đầu tiên.

## TASK-20261007-03

- Ngày: 2026-10-07 (Asia/Saigon).
- Yêu cầu: triển khai phương án tăng tốc đánh giá `rag_tthc_three_1500` đã đề
  xuất, phù hợp máy Windows có RTX 5060 Ti 16 GB.
- Phạm vi: thêm `--concurrency` cho single/coverage và song song theo hội thoại
  cho multi; bảo toàn thứ tự output, lịch sử và lỗi dây chuyền; giảm vùng khóa
  retrieval; cấu hình Ollama parallel thận trọng; cài/xác minh Torch CUDA, chuyển
  BGE-M3 và BERTScore sang GPU với batch phù hợp; bổ sung test/tài liệu và benchmark
  smoke concurrency 1/2. Không dựng vLLM/WSL2 và không chạy đủ 4.500 lượt.
- Tiêu chí hoàn thành: test chứng minh không trộn history, output ổn định và CLI
  kiểm tra concurrency; CUDA hoạt động trên GPU hiện tại; smoke RAG/score thành
  công, có số đo trước/sau và không ghi đè artifact cũ.
- Giả định: ưu tiên tính tái lập/chính xác hơn throughput tối đa; bắt đầu parallel
  2, chỉ tăng 4 nếu đo VRAM/độ ổn định cho phép; giữ một model Ollama được nạp.
- Trạng thái: completed; runner/retriever concurrency, cấu hình CUDA/Ollama và
  BERTScore GPU đã triển khai, smoke single/multi cùng test/lint đều đạt.

## TASK-20261007-04

- Ngày: 2026-10-07 (Asia/Saigon).
- Yêu cầu: bổ sung hiển thị tiến trình cho lệnh `qa-v4 score` vì giai đoạn chấm
  hiện im lặng, khó biết còn chạy hay đã xong.
- Phạm vi: thông báo các phase, số cặp lexical/BERTScore, progress bar lexical và
  thời gian từng phase; giữ nguyên metric và artifact schema.
- Tiêu chí: CLI hiển thị rõ lúc nạp model, đang chấm, tổng hợp và đường dẫn output
  hoàn tất; test/lint đạt.
- Trạng thái: completed; CLI score hiển thị phase, progress lexical/BERTScore,
  thời gian và đường dẫn artifact hoàn tất; metric/schema không đổi.
## TASK-20261014-01

- Ngày: 2026-10-14 (Asia/Saigon).
- Yêu cầu: triển khai pipeline QLoRA production-ready cho
  `Qwen/Qwen2.5-7B-Instruct` theo hướng local-first, sau đó có thể chuyển
  nguyên repo/dữ liệu sang máy Linux GPU chưa biết phần cứng.
- Phạm vi: validation/leakage/preprocessing JSONL, assistant-only loss,
  config base/local/smoke/gpu, preflight GPU không tự áp setting, QLoRA train/resume,
  evaluation baseline/adapter, metrics/plots/report/artifact, checkpoint logic, CLI,
  interface nạp adapter cho chatbot, dependency/portable docs và unit test CPU.
- Tiêu chí: không tải model 7B; chạy toàn bộ test không cần CUDA/model;
  phân biệt local-tested, chờ GPU, chưa làm và giới hạn; không tuyên
  bố training thành công khi chưa chạy thật.
- Giả định: ba dataset hiện nằm trong
  `Data/tthc_test_case_v1/data/`; output/model/checkpoint/dataset/token không được
  Git theo dõi; hyperparameter thí nghiệm chỉ thay bằng config/CLI minh bạch.
- Trạng thái: partial; toàn bộ hạ tầng local-first và portable GPU đã
  triển khai, validator 5.000 record và test QLoRA/server liên quan đạt.
  Training/evaluation model 7B, CUDA/bitsandbytes và artifact thật chờ máy GPU.
## TASK-20261014-02

- Ngày: 2026-10-14 (Asia/Saigon).
- Yêu cầu: audit pre-GPU toàn diện implementation QLoRA local-first hiện
  có, sửa trực tiếp lỗi nghiêm trọng, bổ sung test CPU/checkpoint/early
  stopping, điều tra failure JSON mode so với JSON schema và lập báo cáo.
- Phạm vi kiểm tra: Qwen multi-turn/masking/EOS/truncation; NF4/PEFT/
  optimizer/checkpointing/precision; early stop/best restore/resume state; split
  isolation và leakage; metrics/parameter/VRAM/timing/plots; Windows-Linux
  portability; baseline so với PEFT chatbot.
- Tiêu chí: không tải model weights, không chạy training 7B; test/static
  checks được chạy thật; tạo `docs/qlora-pre-gpu-audit.md`; kết luận
  minh bạch READY hoặc NOT READY cho GPU smoke.
- Trạng thái: partial; audit local và các fix critical/high đã hoàn
  tất, full suite/static/data validation đạt và báo cáo đã tạo. Dự
  án READY có điều kiện cho GPU smoke; CUDA smoke/resume thật còn pending.

## TASK-20261014-08

- Ngày: 2026-10-14 (Asia/Saigon).
- Yêu cầu: đánh giá các artifact QLoRA hiện có trong `outputs/qlora` và viết
  lệnh vẽ các biểu đồ loss.
- Phạm vi: kiểm kê run/checkpoint/trạng thái/metric và log history thực tế;
  phân tích train/eval loss, xu hướng hội tụ, best checkpoint và dấu hiệu
  overfit nếu dữ liệu cho phép; xác định cách gọi công cụ vẽ biểu đồ hiện có
  hoặc bổ sung tối thiểu nếu còn thiếu. Không chạy lại training 7B.
- Tiêu chí hoàn thành: kết luận dựa trên artifact thật, nêu rõ giới hạn đánh
  giá; cung cấp lệnh PowerShell chạy được để sinh biểu đồ loss và kiểm chứng
  lệnh/công cụ ở mức phù hợp mà không ghi đè artifact huấn luyện.
- Giả định: `output/qlora` trong yêu cầu là thư mục thực tế `outputs/qlora` của
  repository.
- Trạng thái: completed; đã đánh giá full run bằng artifact thực, xác minh best
  adapter/checkpoint, sinh 9 biểu đồ (gồm 3 biểu đồ loss) và kiểm thử công cụ vẽ.
## TASK-20261014-03

- Ngày: 2026-10-14 (Asia/Saigon).
- Yêu cầu: trực tiếp thiết lập và kiểm chứng QLoRA cho
  `Qwen/Qwen2.5-7B-Instruct` trên Windows 10, RTX 5060 Ti 16 GB (Blackwell),
  gồm môi trường Python/PyTorch CUDA, dependency, bitsandbytes 4-bit, dữ liệu,
  cấu hình phần cứng, preflight, smoke train thật, checkpoint/resume, metric,
  báo cáo và acceptance gate.
- Phạm vi: giữ nguyên pipeline hiện có trừ khi phát hiện lỗi tương thích/đúng đắn;
  không chạy full training, không xóa dữ liệu/checkpoint, không tự cài toolkit CUDA,
  WSL2, driver hoặc thay đổi hệ thống cần quyền quản trị/reboot.
- Tiêu chí hoàn thành: CUDA tensor hoạt động trên SM 12.0; dependency nhất quán;
  NF4/double-quant/BF16 và backward thật đạt; ba split/hash/tokenizer/format/loss
  được kiểm chứng; smoke tối thiểu 3 optimizer step có checkpoint-2; resume giữ
  optimizer/scheduler/RNG/callback và tăng đúng global step; acceptance report JSON
  và Markdown phân loại PASS/FAIL/BLOCKED; kết luận READY/READY WITH LIMITATIONS/BLOCKED
  dựa trên bằng chứng thực thi.
- Giả định: có thể tạo `.venv-qlora`, cài package trong venv và tải model từ
  Hugging Face khi đủ dung lượng/truy cập; mọi thay đổi cấp hệ điều hành sẽ dừng
  để xin phê duyệt.
- Trạng thái: completed; environment/CUDA/bitsandbytes/dataset/preflight/smoke 4
  step/checkpoint-resume/metrics/plots/acceptance đã chạy thật và đạt. Kết luận
  máy `READY WITH LIMITATIONS` cho full training có giám sát; không chạy full
  training theo phạm vi task.
## TASK-20261014-04

- Ngày: 2026-10-14 (Asia/Saigon).
- Yêu cầu: chuẩn bị bộ điều khiển PowerShell để người dùng tự chạy full QLoRA
  độc lập với Codex/ChatGPT, gồm start/status/stop/TensorBoard/resume, log/PID/run
  metadata, kiểm tra trước khi chạy, chống chạy trùng và dry-run/mock test.
- Phạm vi: giữ pipeline/config RTX 5060 Ti đã smoke-test; bổ sung live status,
  GPU TensorBoard metrics và graceful stop tại ranh giới optimizer step. Không
  khởi chạy full training, không tự đổi hyperparameter, không tự restart OOM,
  không xóa checkpoint hoặc tải lại model ngoài hành vi cache chuẩn của HF.
- Tiêu chí hoàn thành: script PowerShell kiểm đúng venv/GPU/data/config/resume;
  tiến trình worker độc lập có stdout/stderr/exit code/PID; status hiển thị step,
  epoch, loss, elapsed/ETA/VRAM; stop chỉ tác động đúng run và xác minh checkpoint;
  TensorBoard localhost:6006; README có lệnh chính xác; dry-run/mock và test/static
  checks đạt mà không chạy full training.
- Trạng thái: completed; đã tạo start/status/stop/TensorBoard/worker, live status,
  graceful checkpoint stop, resume validation, log/PID/exit metadata, README và
  kiểm thử dry-run/mock; không khởi chạy full training.

## TASK-20261014-05

- Ngày: 2026-10-14 (Asia/Saigon).
- Yêu cầu: audit cuối pipeline ghi log, metric, trực quan hóa và báo cáo của thí
  nghiệm QLoRA Qwen2.5-7B-Instruct; bảo đảm dữ liệu thực nghiệm đủ cho báo cáo kỹ
  thuật/luận văn và dữ liệu đã đo được vẫn còn sau khi run bị gián đoạn.
- Phạm vi: log có cấu trúc liên tục; loss/LR/gradient/timing/throughput/GPU/parameter;
  cấu hình và provenance; token-weighted loss/perplexity; đánh giá baseline so với
  adapter trên cùng test set; metric theo mẫu và tổng hợp; plot/report/status,
  checkpoint/resume; readiness check nhẹ. Không chạy full training, không tự tải
  model weights và không chạy generation evaluation trong validation loop.
- Tiêu chí hoàn thành: ba CLI `training.plot`, `training.report`, `training.evaluate`
  hoạt động theo contract; readiness check xác minh schema/thư mục/config và khả
  năng tạo plot/report bằng artifact tổng hợp; metric thiếu được ghi rõ unavailable;
  tạo `docs/qlora-experiment-readiness.md`; test liên quan đạt.
- Trạng thái: completed; đã bổ sung event log append-only, history epoch/checkpoint/
  resume, evaluation theo split, plot manifest, report availability và readiness
  gate. Readiness RTX trả READY; full training/model download không được khởi chạy.
## TASK-20261014-06

- Ngày: 2026-10-14 (Asia/Saigon).
- Yêu cầu: xác định có thể đánh giá adapter QLoRA trên
  `Data/tthc_test_case_v1/data/rag/test_queries.jsonl` mà không cần cấu hình thêm,
  tương tự benchmark base model đã chạy hay không.
- Phạm vi: đối chiếu schema/ID/nội dung giữa query, gold case và SFT test; không chạy
  generation evaluation hoặc tải model.
- Tiêu chí: nêu rõ lệnh dùng được ngay và khác biệt giữa evaluator QLoRA với QA-v4.
- Trạng thái: completed; 1.000/1.000 ID và message/history/reference của SFT test khớp
  chính xác phép ghép `rag/test_queries.jsonl` + `rag/test.jsonl`.

## TASK-20261014-07

- Ngày: 2026-10-14 (Asia/Saigon).
- Yêu cầu: bổ sung đánh giá model QLoRA vừa train theo cùng benchmark đã dùng cho
  Qwen base và RAG, xuất cùng hoặc nhiều metric hơn để so sánh ba model.
- Phạm vi: backend inference adapter cho QA-v4, cùng query/history/gold/scorer,
  artifact riêng và lệnh run/score/compare; không tự chạy evaluation 1.000 câu.
- Tiêu chí: không đưa gold vào prompt; không gán giả metric/action/retrieval; mock
  test và smoke CLI không tải model đạt; tài liệu nêu lệnh chính xác.
- Trạng thái: completed; backend QLoRA QA-v4, lệnh run/score/paired compare, provenance,
  tài liệu và mock test đã hoàn tất; không chạy evaluation 1.000 câu.

## TASK-20261014-08

- Ngày: 2026-10-14 (Asia/Saigon).
- Yêu cầu: đánh giá full run `qlora-full-20261014-153839-desktop-7pkpjrj-ea78be2d` từ event/log/metrics/checkpoint thật; chạy plot biểu đồ.
- Trạng thái: completed.

## TASK-20261014-09

- Ngày: 2026-10-14 (Asia/Saigon).
- Yêu cầu: viết báo cáo phân tích triển khai QLoRA của dự án, bao gồm cấu hình tham số, kiến trúc triển khai, kết quả phân tích train loss, val loss, các chỉ số đo đạc thực tế; nêu rõ hiện chưa có kết quả test và sẽ bổ sung sau.
- Phạm vi: tạo tài liệu báo cáo `docs/bao-cao-phan-tich-qlora-qwen2-5-7b.md` dựa trên dữ liệu thực tế từ run `outputs/qlora/qlora-full-20261014-153839-desktop-7pkpjrj-ea78be2d`. Không bịa số liệu, không tự ý gán kết quả test khi chưa chạy.
- Tiêu chí hoàn thành: báo cáo đầy đủ các mục yêu cầu, số liệu đối chiếu chuẩn xác với `training_metrics.json`, `config.yaml`, `parameter_report.json`, `timing_report.json` và `training_log.csv`.
- Trạng thái: completed.
## TASK-20261015-01

- Ngày: 2026-10-15 (Asia/Saigon).
- Yêu cầu: đánh giá cấu hình máy hiện tại có đủ khả năng chạy nốt các bước chấm
  QLoRA còn thiếu hay không, sau khi đã sinh đủ 1.000/1.000 prediction.
- Phạm vi: kiểm tra GPU/VRAM/RAM/đĩa, môi trường Python và tiến trình hiện tại;
  kiểm kê prediction/run report, scorer và lệnh compare/evaluate/plot/report;
  ước lượng tính khả thi, thứ tự chạy và rủi ro. Chưa tự khởi chạy workload dài.
- Tiêu chí hoàn thành: kết luận rõ bước nào chạy được ngay, bước nào tốn VRAM/
  thời gian hoặc thiếu dữ liệu/judgment; đưa lệnh an toàn dựa trên artifact thật.
- Trạng thái: completed; máy tạo run RTX 5060 Ti 16 GB đủ chạy các bước còn lại
  theo thứ tự, nhưng controlled HF evaluation là workload dài. Phiên kiểm tra hiện
  tại là máy RTX 4050 6 GB và không có venv/prediction được nêu, nên không tự chạy.
- Bổ sung người dùng: máy cần đánh giá chính là RTX 4050 Laptop 6 GB đang được
  kiểm tra trực tiếp, không phải host RTX 5060 Ti được ghi trong artifact training.
- Trạng thái hiệu chỉnh: partial; lexical/compare/plot/report chạy được, BERTScore
  nên hạ batch và controlled HF evaluation cần smoke riêng vì VRAM/RAM hạn chế.

## TASK-20261015-02

- Ngày: 2026-10-15 (Asia/Saigon).
- Yêu cầu: cập nhật báo cáo phân tích triển khai QLoRA sau khi đã có kết quả chạy kiểm thử và chấm điểm 1.000 ca test trên `tthc_test_case_v1` (`scores_qwen_qlora_batch4.json`).
- Phạm vi: cập nhật `docs/bao-cao-phan-tich-qlora-qwen2-5-7b.md`, bổ sung mục phân tích kết quả test thực tế (1.000 ca, N=810 ca tính độ tương đồng văn bản), bảng so sánh 3 chiều giữa Qwen Base vs RAG vs QLoRA, phân tích theo từng nhóm hành động (answer, partial, correct_premise, clarify, abstain) và hiệu năng suy luận (latency, throughput, batching).
- Trạng thái: completed; đã đối chiếu toàn bộ số liệu benchmark từ `scores_qwen_qlora_batch4.json` và cập nhật Mục 6 cùng bảng so sánh 3 chiều vào `docs/bao-cao-phan-tich-qlora-qwen2-5-7b.md`.

## TASK-20261015-03

- Ngày: 2026-10-15 (Asia/Saigon).
- Yêu cầu: xác minh vì sao kết quả QLoRA tốt hơn Qwen Base và Base + RAG; làm rõ
  khác biệt trong huấn luyện và đánh giá giữa ba cấu hình.
- Phạm vi: đối chiếu artifact prediction/score/provenance, dữ liệu test, prompt và
  hợp đồng đầu ra, scorer, cấu hình train QLoRA và pipeline RAG. Không chạy lại
  generation/benchmark dài và không thay đổi model/checkpoint.
- Tiêu chí hoàn thành: tách rõ nguyên nhân đã được bằng chứng xác nhận với giả
  thuyết; xác định mức độ so sánh công bằng, các metric tạo ra kết luận và hạn
  chế/rò rỉ dữ liệu nếu có; nêu khác biệt train/evaluate bằng ngôn ngữ dễ hiểu.
- Trạng thái: completed; đã xác minh cùng query hash/reference history, đối chiếu
  scorer và phân tầng test theo tài liệu đã/chưa xuất hiện trong train. Kết luận
  QLoRA vượt trội về độ giống đáp án trong miền đã biết, nhưng chưa có action,
  retrieval hay semantic judgment để khẳng định thắng toàn diện.

## TASK-20261015-04

- Ngày: 2026-10-15 (Asia/Saigon).
- Yêu cầu: tích hợp model QLoRA đã huấn luyện vào web demo hỏi đáp hiện có để
  người dùng có thể chọn và so sánh cùng Qwen Base và Qwen + RAG.
- Phạm vi: thêm cấu hình/model mode QLoRA, luồng inference local adapter, nhãn UI,
  quản lý chuyển backend phù hợp GPU 6 GB, kiểm thử server/UI/config và cập nhật
  hướng dẫn vận hành. Không thay đổi hoặc huấn luyện lại adapter.
- Tiêu chí hoàn thành: UI hiển thị ba lựa chọn Base/RAG/QLoRA; QLoRA không chạy
  retrieval, dùng đúng `best_adapter`; lịch sử hội thoại tách theo model; chuyển
  Ollama/Transformers không giữ đồng thời model trên GPU theo mặc định; test liên
  quan đạt. Chỉ tuyên bố chạy model thật nếu có kiểm chứng trực tiếp.
- Trạng thái: completed; UI/config/server đã có ba chế độ Base, RAG và QLoRA;
  test liên quan đạt. Chưa chạy inference model thật hoặc browser QA trong task
  này nên runtime GPU/hiển thị trực quan vẫn là giới hạn kiểm chứng.

## TASK-20261015-05

- Ngày: 2026-10-15 (Asia/Saigon).
- Yêu cầu: khắc phục web demo QLoRA lỗi thiếu `accelerate` khi nạp model.
- Phạm vi: xác minh đúng interpreter, bổ sung dependency runtime QLoRA còn thiếu,
  kiểm tra tương thích môi trường và smoke loader; không thay checkpoint.
- Tiêu chí hoàn thành: `accelerate`, `peft`, `bitsandbytes` import được trong
  `env`; `pip check` đạt; lỗi dependency không còn. Chỉ xác nhận inference model
  thật nếu loader/generation thực sự chạy thành công.
- Trạng thái: completed; đã cài dependency thiếu, đưa Transformers về stack ghim
  4.57.3 và cấu hình NF4 single-GPU. Smoke thật nạp đúng `best_adapter` và sinh
  8 token thành công trên RTX 4050; cần restart web process đang chạy.

## TASK-20261015-06

- Ngày: 2026-10-15 (Asia/Saigon).
- Yêu cầu: chẩn đoán QLoRA trên web liên tục yêu cầu nêu tên/mã/nội dung cụ thể
  khi người dùng nhập tên hồ sơ, mã `1.004696` và tên thủ tục đầu tư.
- Phạm vi: kiểm tra lịch sử web, dữ liệu SFT và corpus; không sửa model hoặc suy
  diễn nội dung thủ tục khi chưa có câu hỏi cụ thể.
- Tiêu chí hoàn thành: xác định đây là lỗi history, thiếu tri thức, sai mã hay hành
  vi clarify đúng; nêu cách hỏi/chế độ phù hợp.
- Trạng thái: completed; history được gửi đúng. Mã nhập sai so với corpus
  (`1.009646`), thủ tục này không có trong SFT nhưng có trong corpus RAG, và các
  lượt chỉ nêu định danh chưa hỏi thuộc tính cụ thể.
- Bổ sung kết quả thực tế: khi hỏi đúng mã và thuộc tính hồ sơ, QLoRA sinh một
  giấy tờ chung chung không có trong nguồn và bỏ sót danh sách ba mục. Kết quả
  này được phân loại là sai/thiếu, không phải câu trả lời đúng dù diễn đạt trôi chảy.

## TASK-20261015-07

- Ngày: 2026-10-15 (Asia/Saigon).
- Yêu cầu: refactor toàn bộ ViGovBot thành dự án Python sạch, dễ bảo trì với CLI
  thống nhất `vigov`; có thể giữ nguyên mã hiện tại và tạo cấu trúc riêng rồi di
  chuyển dần đến khi đồng bộ hoạt động.
- Phạm vi: kiểm kê repository và baseline; lập ánh xạ đường dẫn; hợp nhất CLI và
  cấu hình; tổ chức application/training/evaluation/reporting; quản lý tiến trình
  training nền Windows/Linux; giữ tương thích chatbot, checkpoint và artifact;
  bổ sung kiểm thử và tài liệu `docs/refactor-summary.md`.
- Tiêu chí hoàn thành: các tiêu chí acceptance trong yêu cầu đính kèm, gồm CLI,
  cấu hình, lifecycle, test/static check, tài liệu và lệnh GPU tiếp theo đều dựa
  trên triển khai thực tế; không chạy full training hoặc tải lại model.
- Giả định an toàn: triển khai tăng dần trên nhánh `codex/ref-clean`; không xóa,
  đổi tên hoặc sao chép checkpoint/dataset/adapter/output lớn; giữ entry point cũ
  trong giai đoạn tương thích cho đến khi test chứng minh đường mới tương đương.
- Trạng thái: in_progress; đang kiểm kê mã nguồn và ghi baseline trước thay đổi.
- Kết quả: completed; đã triển khai CLI `vigov`, cấu hình phân lớp, package
  `vigovbot.training`, lifecycle nền Windows/Linux, run layout, compatibility,
  CI và tài liệu. Full suite 156 pass, 1 optional skip; không chạy full training.
