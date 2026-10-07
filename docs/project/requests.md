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
