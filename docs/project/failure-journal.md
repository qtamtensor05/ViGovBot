# Nhật ký vấp ngã

Chỉ ghi lỗi quan sát được; phân biệt nguyên nhân đã xác nhận với giả thuyết.

## ERR-20261015-21

- Task: TASK-20261015-13.
- Triệu chứng: CI Ubuntu/Windows fail; checkout sạch tái hiện link docs hỏng,
  `data stats` exit 2 và readiness `BLOCKED` khi thiếu dataset/artifact local.
- Nguyên nhân: ba test dùng trạng thái máy phát triển làm fixture dù `Data/` và
  `outputs/` chỉ theo dõi `.gitkeep`.
- Xử lý: tạo dataset/output tạm trong test; bỏ qua việc tồn tại của link target
  thuộc khu artifact runtime nhưng vẫn kiểm tra mọi link source/docs khác.
- Kết quả: full suite trong checkout sạch đạt 164 test, 1 optional skip.
- Phòng tránh: test CI phải tự tạo input; không dùng artifact ngoài Git làm
  precondition trừ khi workflow tải artifact một cách tường minh.

## ERR-20261006-05

- Task: TASK-20261006-03.
- Triệu chứng: kiểm tra sau vòng viết lại đầu phát hiện 339 chuỗi câu hỏi single
  bị trùng, tương ứng 821 case dư ngoài bản đầu tiên.
- Nguyên nhân đã xác nhận: tổ hợp biến thể quay vòng theo nhóm toàn cục, trong khi
  cùng một tên thủ tục xuất hiện lại đúng chu kỳ nên nhận cùng cách diễn đạt.
- Xử lý: giữ bản đầu và thêm tiền tố hỏi trung tính khác nhau cho các bản trùng.
- Kết quả: 0 input single trùng; checksum và test đều đạt.
- Phòng tránh: kiểm tra uniqueness trên câu hoàn chỉnh sau mọi phép paraphrase,
  không chỉ kiểm tra số mẫu chuẩn hóa.

## ERR-20261006-04

- Task: TASK-20261006-03.
- Triệu chứng: `git show HEAD:.../cases.jsonl` thất bại vì file tồn tại trên đĩa
  nhưng không có trong HEAD.
- Nguyên nhân đã xác nhận: dataset này không được Git theo dõi; không còn snapshot
  cùng hash cũ trong repository sau khi ghi.
- Xử lý: kiểm tra invariant hiện tại, checksum, phạm vi gán của script và công bố
  giới hạn; không giả vờ đã có diff độc lập với bản gốc.
- Phòng tránh: trước lần biến đổi dataset lớn tiếp theo, lưu snapshot bất biến hoặc
  patch question-only có hash trong khu vực artifact được bảo toàn.

## ERR-20261006-03

- Task: TASK-20261006-03.
- Triệu chứng: lệnh kiểm thử đầu tiên từ thư mục dataset không tìm thấy
  `env\Scripts\python.exe`.
- Nguyên nhân đã xác nhận: đường dẫn tương đối được tính từ thư mục dataset thay
  vì gốc repository.
- Xử lý: dùng đường dẫn tuyệt đối tới Python của môi trường dự án.
- Kết quả: kiểm tra invariant, 3 unit test và test resume chạy thành công.
- Phòng tránh: khi đổi `workdir`, dùng đường dẫn Python tuyệt đối hoặc tính lại
  đường dẫn tương đối trước khi chạy.

## ERR-20261006-02

- Task: TASK-20261006-02.
- Triệu chứng: lần chạy đầu `build_review.py` dừng với `SyntaxError` tại phần sinh
  báo cáo Markdown.
- Nguyên nhân đã xác nhận: ghép biểu thức nối chuỗi vào giữa f-string ba dấu nháy
  làm chuỗi kết thúc sớm.
- Xử lý: tính trước chuỗi phân bố/tổng hợp, sau đó nội suy biến vào một f-string.
- Kết quả kiểm chứng: script chạy lại exit 0; AST parse thành công và các kiểm tra
  count/ID/CSV đều đạt.
- Phòng tránh: không trộn phép cộng chuỗi với f-string nhiều dòng; chuẩn bị phần
  động phức tạp trong biến riêng.

## ERR-20261006-01

- Task: TASK-20261006-02.
- Triệu chứng: PowerShell trong sandbox báo `Access is denied` khi đọc
  `outputs/result_qa` dù đường dẫn thuộc workspace.
- Nguyên nhân đã xác nhận trong phạm vi task: ACL của `outputs/` không cho tiến
  trình sandbox đọc; không phải artifact bị thiếu.
- Xử lý: xin quyền thao tác trực tiếp đúng workspace cho các lệnh đọc/ghi cần thiết.
- Kết quả kiểm chứng: kiểm kê được artifact, sinh và đọc lại ba đầu ra thành công.
- Phòng tránh: nếu lỗi ACL này tái diễn, không suy luận file không tồn tại; kiểm tra
  lại bằng quyền workspace trực tiếp, giữ phạm vi lệnh ở dataset/artifact liên quan.

## ERR-20261003-10

- Task: TASK-20261003-09.
- Triệu chứng: lệnh kiểm thử đầu tiên không import được `vigovbot`.
- Bối cảnh tái hiện: `python -m unittest tests.test_qa_v4` dùng Python hệ thống.
- Nguyên nhân đã xác nhận: package dùng layout `src/` và Python hệ thống không
  cài editable package; đây là lỗi môi trường đã từng được ghi nhận.
- Xử lý: chuyển sang `env\Scripts\python.exe`, là môi trường dự án hiện có.
- Kết quả kiểm chứng: chạy lại đạt 8 test QA v4; Ruff cũng đạt.
- Phòng tránh: dùng Python trong `env/` cho kiểm thử repository.

## ERR-20261003-09

- Task: TASK-20261003-07.
- Triệu chứng: lượt đầu `scripts/smoke_routing_live.py oil` nhận HTTP 500 từ
  Ollama ở lần gọi router; chưa có response JSON model để validate.
- Nguyên nhân: chưa xác định; không có body lỗi/log runner trong traceback nên
  không khẳng định do schema, bộ nhớ hay tải model.
- Kiểm tra: gọi riêng /api/chat cùng schema với prompt ngắn, nhận HTTP 200 và
  JSON hợp lệ. Chạy lại nhóm oil thành công 2/2, nhóm basic thành công 4/4.
- Kết quả: lỗi API không còn tái hiện trong các lượt sau; không thêm retry HTTP
  tự động và không coi lỗi API là JSON sai dẫn đến fallback.
- Phòng tránh: khi lỗi tái hiện cần lấy body lỗi và log Ollama đúng thời điểm,
  phân biệt lỗi dịch vụ với lỗi schema/validator.

## ERR-20261003-08

- Task: TASK-20261003-06.
- Bối cảnh: probe Qwen thật với câu hỏi tràn dầu và history giả về hộ chiếu.
- Triệu chứng: cả initial/retry trả follow_up, query và clarification không rỗng;
  validator báo Retrieval route requires query and no clarification; fallback.
- Tái hiện: `env\Scripts\python scripts\probe_oil_spill_routing.py --with-history`.
- Thử giải pháp: cùng prompt/history dùng schema anyOf ép các trường theo nhánh.
- Kết quả: JSON hợp lệ ngay lần đầu, clarification rỗng; nhãn follow_up vẫn
  chưa đúng ý nghĩa câu hỏi chuyển chủ đề. Chưa sửa production, chưa chứng minh
  schema giải quyết mọi trường hợp. Artifact oil_spill_routing_probe_history.json.
- Phòng tránh đề xuất: schema + ví dụ phân loại + retry cụ thể + telemetry web.

## ERR-20261003-07

- Task: TASK-20261003-05.
- Triệu chứng: script xác thực lỗi UnicodeEncodeError khi in tiếng Việt.
- Lệnh: `env\Scripts\python scripts\verify_routing_artifact.py outputs\qa_v4\local_smoke.jsonl`.
- Nguyên nhân: stdout Windows dùng cp1252 không biểu diễn được tiếng Việt.
- Sửa: cấu hình stdout UTF-8; chạy lại thành công, kiểm tra đủ 10 dòng.
- Phòng tránh: script chẩn đoán in Unicode cần cấu hình encoding rõ ràng.

## ERR-20261003-06

- Task: TASK-20261003-05.
- Triệu chứng: 3 lượt trong artifact Qwen thật trả câu fallback mặc định.
- Bằng chứng: `outputs/qa_v4/local_smoke.jsonl`, dòng 8–10; raw response model
  `qwen2.5:7b`, initial_error/retry_error cùng marker fallback được lưu đầy đủ.
- Nguyên nhân xác nhận: JSON đúng cú pháp nhưng follow_up chứa clarification
  không rỗng; `parse_route` báo `Retrieval route requires query and no clarification`.
- Cách kiểm tra: script verify_routing_artifact chạy lại validator trên cả
  initial_text và retry_text, tái hiện đủ 6 lỗi hợp đồng của ba lượt fallback.
- Kết quả: xác nhận lỗi; task điều tra chưa sửa prompt/schema của ứng dụng.
- Phòng tránh đề xuất: schema có ràng buộc theo nhánh hoặc prompt retry chứa
  lỗi cụ thể và ví dụ JSON sửa; cần kiểm chứng model thật trước khi áp dụng.

## ERR-20261003-05

- Task: TASK-20261003-04.
- Triệu chứng: nhánh web `Qwen 2.5 7B + RAG` trả lỗi `SQLite objects created in
  a thread can only be used in that same thread`.
- Bối cảnh tái hiện: `Retriever` được tạo trong thread khởi động server, sau đó
  `ThreadingHTTPServer` xử lý `/api/chat` bằng thread worker và gọi `search()`.
- Nguyên nhân đã xác nhận: `sqlite3.connect` dùng mặc định
  `check_same_thread=True`, không phù hợp với vòng đời tài nguyên web hiện tại.
- Xử lý: mở database read-only với `check_same_thread=False`; bổ sung khóa nội bộ
  quanh toàn bộ `search()` và `close()` để tuần tự hóa encoder, FAISS và SQLite.
- Kết quả: test hồi quy tạo Retriever ở thread chính rồi truy hồi trong thread
  worker thành công; tổng cộng 20 test server/cấu hình/RAG đều đạt.
- Phòng tránh: mọi tài nguyên được tạo trước `ThreadingHTTPServer.serve_forever()`
  phải có hợp đồng thread rõ ràng và test gọi từ worker thread.

## ERR-20261003-04

- Task: TASK-20261003-03.
- Triệu chứng: lần chạy test đầu báo không tìm thấy package `vigovbot`; khi thêm
  `PYTHONPATH=src`, Python mặc định tiếp tục thiếu `filelock` và `yaml`.
- Bối cảnh tái hiện: chạy test bằng `python` hệ thống thay vì môi trường dự án.
- Nguyên nhân đã xác nhận: Python 3.14 mặc định chưa cài package/dependency dự án;
  workspace dùng virtual environment tại `env/`, không phải `.venv/`.
- Xử lý: chạy lại bằng `env\Scripts\python`.
- Kết quả: 19 test liên quan server, cấu hình và pipeline đều thành công.
- Phòng tránh: kiểm tra virtual environment có sẵn và dùng Python của môi trường
  dự án trước khi kết luận thiếu dependency.

## ERR-20261003-03

- Task: TASK-20261003-02.
- Triệu chứng: hai module test RAG không import được, `ModuleNotFoundError: No
  module named 'faiss'`.
- Bối cảnh tái hiện: chạy `python -m unittest tests.test_rag_config_cli
  tests.test_rag_pipeline -v`; workspace không có `.venv`, lệnh dùng Python 3.14
  mặc định.
- Nguyên nhân đã xác nhận: môi trường Python hiện tại chưa cài dependency
  `faiss-cpu` thuộc nhóm `rag`/`test`.
- Xử lý: không cài dependency vì task chỉ sửa tài liệu; chuyển sang kiểm tra tĩnh
  liên kết và `git diff --check`.
- Kết quả: kiểm thử ứng dụng chưa chạy được; lỗi không phát sinh từ thay đổi mã
  nguồn vì task không sửa code.
- Phòng tránh: dùng môi trường đã cài `.[test,dev]` hoặc `.[rag]` khi cần chạy bộ
  test RAG; không coi lỗi thiếu dependency là regression của ứng dụng.

## ERR-20261003-01

- Task: TASK-20261003-01.
- Triệu chứng: PowerShell in lỗi Set-PSReadLineOption về virtual terminal và
  invalid handle trước output của lệnh đọc file.
- Bối cảnh: exec_command dùng login mặc định, nạp PowerShell profile.
- Nguyên nhân: profile bật prediction của PSReadLine trong phiên không có
  terminal tương tác phù hợp; thông báo chỉ tới profile dòng 12–13.
- Xử lý: các lệnh tiếp theo dùng `login: false`.
- Kiểm chứng: lệnh đọc tài liệu và liệt kê skill sau đó không còn lỗi profile.
- Phòng tránh: dùng PowerShell không nạp profile cho lệnh agent không tương tác;
  không chỉnh profile cá nhân ngoài phạm vi task.

## ERR-20261003-02

- Task: TASK-20261003-01.
- Triệu chứng: quick_validate.py thất bại với `ModuleNotFoundError: No module named 'yaml'`.
- Tái hiện: chạy validator bằng Python mặc định cho một trong hai skill mới.
- Nguyên nhân: Python mặc định không có PyYAML mà validator import.
- Xử lý: cài PyYAML bằng pip --target vào thư mục tạm riêng; đặt PYTHONPATH và
  PYTHONUTF8 trong process kiểm chứng rồi chạy lại validator.
- Kết quả: cả hai skill đều trả `Skill is valid!`, exit code 0.
- Phòng tránh: kiểm tra dependency của công cụ validator; dùng môi trường riêng,
  không thêm dependency tooling vào ứng dụng chỉ để kiểm tra Markdown.

## ERR-20261004-01 — TASK-20261004-01: generation sai hợp đồng

- Bằng chứng: ZIP thứ hai có 4 lỗi `Evidence status and action do not match`
  (000033, 000084, 000211, 000271), gây 7 lượt free-running bị chặn.
- Nguyên nhân xác nhận ở code: generation chỉ dùng JSON mode, không ràng buộc
  cặp evidence/action, không retry; runner không lưu raw generation lỗi.
  Artifact không đủ để biết chính xác trường thiếu/sai của từng lượt.
- Sửa: schema theo cặp, giữ validator, retry một lần có budget; lưu diagnostics
  và blocked_by_id. Kiểm thử tái hiện JSON thiếu/sai/cắt dở, sửa thành công hoặc
  vẫn lỗi đều đạt. Giữ việc chặn chuỗi đã lỗi để không làm sai free_running.

## ERR-20261004-02 — TASK-20261004-01: lỗi ngữ nghĩa trong mẫu mới

- 000142 suy diễn trạng thái cá nhân từ quy trình; 000141 bỏ một phần câu hỏi;
  các ca 000059/000263 out_of_scope sai, 000072/000180 chọn thủ tục khi mơ hồ.
- Biện pháp: điều chỉnh prompt và giữ câu hỏi gốc cùng query đã viết lại.
- Chưa xác nhận hiệu quả bằng model thật: localhost:11434 từ chối kết nối;
  không có log Colab để xác định nguyên nhân artifact chỉ chứa 23 lượt.
- Báo cáo chi tiết: colab-rag-2-assessment.md; cần smoke lại, không tuyên bố
  các lỗi nội dung đã hết từ kiểm thử mock hoặc action accuracy.

## ERR-20261004-03 — TASK-20261004-03

- Bối cảnh: kiểm tra artifact theo đường dẫn người dùng gọi output/result_qa và in dữ liệu tiếng Việt bằng Python.
- Triệu chứng: đường dẫn không tồn tại; PowerShell profile báo PSReadLine khi redirect; Python stdout cp1252 gây UnicodeEncodeError; một truy vấn rg dùng glob đường dẫn Windows không hợp lệ.
- Xác nhận/sửa: thư mục thực là outputs/result_qa; dùng login=false, PYTHONIOENCODING=utf-8 và tìm trên đường dẫn thư mục với glob file. Các lần đọc tiếp theo thành công, dữ liệu gốc không bị sửa.
- Tránh lặp: xác nhận tên thư mục và encoding trước khi đọc artifact Unicode.
- Lỗi artifact quan sát riêng: single_0445 StructuredAnswerError sau 2 lần sinh JSON; chưa sửa runtime, chi tiết và giả thuyết cắt token nằm trong báo cáo.

## ERR-20261005-01 — TASK-20261005-01

- Assert kiểm chứng ban đầu giả định comparison.csv luôn đủ 1.500 dòng, thất bại ở cover.
- Xác nhận: CSV chỉ chứa 1.113 dòng đã chạy; scores per_case chứa đủ 1.500 mục. Sửa mẫu số kiểm chứng theo loại artifact; kiểm chứng lại đạt. Không có dữ liệu đầu vào bị sửa.


## ERR-20261005-02 — TASK-20261005-02

- Script retrieval bổ sung ban đầu giả định mọi source_file có PDF tương ứng và mã chunk luôn khớp tên nguồn; dừng ở 1.014955_D.pdf (thiếu file) và unverified_a2801127764a (khác tên 2.009182739.pdf).
- Đã sửa: giữ trạng thái unverified_source_identity, loại khỏi mẫu số đo được; không tự đoán ánh xạ _D/-Xoa hoặc mã unverified. Chạy lại exit 0; multi đo 1.142 ca, cover 1.110 ca.
- Lỗi nội dung Gold phát hiện riêng: coverage_0381 có trường cơ quan ghi Không có thông tin nhưng trình tự PDF có hỗ trợ câu trả lời. Correctness/completeness để null chờ phân xử; không sửa Gold ngầm.

## ERR-20261007-01 — TASK-20261007-01

- Triệu chứng: `test_evaluation.py` lỗi `ModuleNotFoundError: No module named
  'sacrebleu'` dù đã cài toàn bộ `locks/rag-windows-py314.txt`.
- Bối cảnh tái hiện: chạy test đi kèm dataset bằng `.venv/Scripts/python.exe`;
  hai test khác đạt, `test_resume.py` cũng đạt.
- Nguyên nhân đã xác nhận: lockfile RAG/evaluation Windows hiện tại không chứa
  `sacrebleu`, trong khi evaluator của dataset import package này và
  `pyproject.toml` khai báo nó trong extra `evaluation`.
- Xử lý: cài bổ sung `sacrebleu>=2.4,<3` vào `.venv`, không sửa lockfile trong
  task thiết lập máy; chạy lại test để kiểm chứng.
- Phòng tránh: khi tái sinh lock cần kiểm tra dependency trực tiếp của
  `evaluation` và chạy test dataset trong clean environment.

## ERR-20261007-02 — TASK-20261007-03

- Triệu chứng: BERTScore CUDA tính xong 3 cặp trong 9,41 giây nhưng scorer lỗi
  `ValueError: not enough values to unpack (expected 4, got 2)` và chưa ghi output.
- Bối cảnh: `bert-score==0.3.13`, `transformers==5.17.0`, gọi `score(...,
  return_hash=True)` trong `qa_v4/scoring.py`.
- Nguyên nhân xác nhận: API runtime trả `((P, R, F), hashcode)`, còn code giả định
  dạng cũ `(P, R, F, hashcode)`.
- Xử lý: chuẩn hóa cả hai dạng trả về, thêm unit test mock và chạy lại score CUDA.
  Prediction RAG không bị sửa và không cần chạy lại model.
- Phòng tránh: test đường BERTScore nên mock đúng nhiều contract phiên bản và có
  ít nhất một smoke thật sau khi nâng dependency.

## ERR-20261007-03 — TASK-20261007-03

- Triệu chứng: hai lệnh PowerShell gộp dùng `Start-Process` để restart Ollama bị
  policy terminal từ chối trước khi tạo process.
- Xử lý: tách đặt biến user, dừng đúng process Ollama đã xác minh, rồi chạy
  `ollama serve` trực tiếp trong session 99804; readiness và log cấu hình đạt.
- Ảnh hưởng: không mất dữ liệu; lần bị từ chối không thực thi thay đổi. Ollama
  hiện chạy với parallel=2, max loaded=1, Flash Attention và KV q8_0.
# ERR-20261007-03 — TASK-20261007-05

- Triệu chứng: `python Data/qa_test/tthc_test_case_v1/validation/validate_package.py`
  dừng với `FileNotFoundError` tại `data/train.jsonl`.
- Bối cảnh tái hiện: bộ dữ liệu hiện đặt case/query RAG trong `data/rag/` và SFT
  trong `data/fintuning/`, trong khi validator và `checksums.sha256` vẫn ghi đường
  dẫn phẳng `data/{split}.jsonl`, `data/{split}_queries.jsonl`,
  `data/{split}_sft.jsonl`.
- Nguyên nhân đã xác nhận: layout artifact không khớp đường dẫn được mã hóa trong
  validator/checksum; lỗi xảy ra trước khi kiểm tra nội dung split.
- Cách xử lý: không di chuyển hoặc sửa gold; benchmark dùng tường minh
  `data/rag/test_queries.jsonl` và `data/rag/test.jsonl`, đồng thời sẽ kiểm tra
  hash/nội dung theo layout thực tế. Chưa sửa package nguồn trong lúc chuẩn bị run.
- Kết quả kiểm chứng: ba file test/query/SFT tại layout thực tế khớp SHA-256 khai
  báo; evaluator synthetic đạt và 28 test RAG/QA đạt. Validator gốc vẫn lỗi nếu
  chưa sửa layout, nên không dùng kết quả đó để tuyên bố package validation đạt.

# ERR-20261007-04 — TASK-20261007-05

- Triệu chứng: smoke concurrency 4 liên tục retry HEAD tới Hugging Face với
  `WinError 10013`, dù BGE-M3 đã có trong cache.
- Bối cảnh: lượt smoke chạy trong sandbox không có mạng sau lượt tải model bằng
  quyền mạng; thư viện vẫn thử kiểm tra các file cấu hình tùy chọn trên Hub.
- Nguyên nhân: sandbox chặn socket, không phải thiếu trọng số hoặc lỗi CUDA.
- Cách xử lý: dừng đúng session trước khi tạo prediction, xác nhận output chưa tồn
  tại, chạy lại với `HF_HUB_OFFLINE=1` và `TRANSFORMERS_OFFLINE=1`.
- Kết quả: smoke c4 đạt 8/8, exit 0, wall 24,52 giây; dùng cùng cách cho full run.

# ERR-20261007-05 — TASK-20261007-06

- Triệu chứng: evaluator bị người dùng ngắt tại `BLEU.corpus_score`; trước đó
  terminal in lặp cảnh báo khuyến nghị `effective_order` cho sentence BLEU.
- Tái hiện: 1.000 prediction, 995 thành công; evaluator lexical gốc thực tế hoàn
  tất khoảng 3,75 giây nhưng phát hàng trăm dòng cảnh báo.
- Nguyên nhân: không phải deadlock/corpus quá lớn; SacreBLEU logger cảnh báo ở mỗi
  `sentence_score` khi hợp đồng hiện tại cố ý dùng `effective_order=False`.
- Cách sửa: đặt riêng logger `sacrebleu` ở ERROR, giữ nguyên tham số metric; thêm
  thông báo phase/progress và option batch BERTScore.
- Kết quả: lexical full hoàn tất 3,70 giây, không còn warning flood; synthetic
  evaluator và py_compile đạt. Tránh đổi `effective_order` ngầm vì sẽ đổi điểm
  sentence BLEU của câu ngắn.

# ERR-20261007-06 — TASK-20261007-06

- Triệu chứng: BERTScore dừng trước khi nạp model với
  `LocalEntryNotFoundError`/`outgoing traffic has been disabled` cho
  `xlm-roberta-large`.
- Bối cảnh: cùng terminal trước đó đã đặt `HF_HUB_OFFLINE=1` và
  `TRANSFORMERS_OFFLINE=1` để chạy RAG bằng cache; model BERTScore chưa có cache.
- Nguyên nhân: chế độ offline còn hiệu lực trong process PowerShell, không phải
  lỗi CUDA, batch 32 hoặc evaluator.
- Cách xử lý: xóa hai biến môi trường khỏi session, cho phép tải model lần đầu;
  sau khi cache hoàn tất có thể dùng offline ở các lần sau.
- Kết quả kiểm chứng: nguyên nhân xác nhận trực tiếp từ traceback; người dùng tự
  chạy lại job dài theo yêu cầu trước, chưa có artifact BERTScore hoàn tất.

## ERR-20261014-01

- Task: TASK-20261014-01.
- Triệu chứng: test metric local lỗi `TypeError` vì `sentence_bleu()` không
  nhận tham số `effective_order`; Ruff đồng thời báo ba import thừa.
- Nguyên nhân: API SacreBLEU 2.6.0 dùng tên `use_effective_order` cho
  helper function, khác tên constructor metric; import còn sót sau khi tách module.
- Xử lý: đổi sang `use_effective_order=True`, xóa import thừa và chạy lại
  cùng bộ test/lint.

## ERR-20261014-02

- Task: TASK-20261014-01.
- Triệu chứng: validator 5.000 record không kết thúc sau hơn ba phút
  trong giai đoạn near-duplicate; không có output lỗi và chưa ghi report.
- Nguyên nhân: bucket theo 12 ký tự đầu gom quá nhiều câu hỏi hành chính
  có cùng cụm mở đầu, tạo quá nhiều lần `SequenceMatcher`.
- Xử lý: dừng đúng session, thay bằng chỉ mục character 5-gram, xếp
  hạng và giới hạn 50 candidate/record trước so khớp chính xác; exact
  duplicate vẫn kiểm tra toàn phần và báo cáo riêng.
- Lần chạy lại vẫn quá hai phút do 50 candidate/record còn nặng; đã
  dừng trước khi ghi artifact và giảm xuống top 10 kèm Jaccard token prefilter.

## ERR-20261014-03

- Task: TASK-20261014-01.
- Triệu chứng: ba test server cũ mất trường `answer` do `_settings()` truy
  cập trực tiếp thuộc tính adapter mới trên `SimpleNamespace` fixture cũ.
- Nguyên nhân: thay đổi tích hợp không giữ tương thích với model config
  duck-typed trong test/API nội bộ.
- Xử lý: dùng `getattr` với default cho ba option mới, giữ nguyên hành vi
  provider cũ; bổ sung test mock xác nhận adapter được bọc qua PEFT.

## ERR-20261014-04

- Task: TASK-20261014-01.
- Triệu chứng: full suite có 1 failure/125 test tại
  `test_multiturn.MultiTurnTests.test_rewrite_and_answer_receive_history`:
  test mong `response_format == "json"`, runtime hiện trả JSON schema.
- Phân loại: không phát sinh từ file QLoRA/provider/config đã sửa trong
  task; 124 test còn lại đạt, 1 skipped. Không hạ contract schema hiện tại
  xuống JSON mode chỉ để làm test cũ qua.
- Bước sau: báo cáo là known limitation/pre-existing regression của nhánh;
  test QLoRA và server integration liên quan vẫn phải đạt riêng.

## ERR-20261014-05

- Task: TASK-20261014-01.
- Triệu chứng: validator official Qwen tokenizer offline chạy exit 0 nhưng
  P50/P90/P95/P99/max đều bằng 2 cho mọi split, không hợp lý.
- Nguyên nhân: Transformers 5.17 trong môi trường trả `BatchEncoding`/
  mapping hai khóa từ `apply_chat_template`; code lấy `len(mapping)` thay vì
  `len(input_ids)`. Cùng contract có thể làm sai masking.
- Xử lý: thêm bộ chuẩn hóa output list/tensor/mapping/batch một mẫu,
  dùng chung cho thống kê và assistant-only masking; thêm regression test.

## ERR-20261014-06

- Task: TASK-20261014-02.
- Triệu chứng: official Qwen tokenizer cho thấy assistant header
  `<|im_start|>assistant` đang có label khác `-100`; truncation chỉ từ chối
  khi toàn bộ target biến mất, nên có thể cắt answer cuối.
- Nguyên nhân: boundary assistant được suy ra từ end của prefix trước
  thay vì end của generation prompt; truncation áp sau khi tạo label.
- Xử lý: target bắt đầu sau `add_generation_prompt=True`, giữ assistant
  content và `<|im_end|>`; từ chối toàn mẫu vượt max sequence.
- Kiểm chứng: official tokenizer cache-only và regression multi-turn/EOS đạt.

## ERR-20261014-07

- Task: TASK-20261014-02.
- Triệu chứng: resume tạo run directory mới; validator chỉ yêu cầu
  adapter/trainer state, không chứng minh optimizer, scheduler, RNG, callback,
  config hay dataset không đổi.
- Nguyên nhân: checkpoint path chỉ được chuyển cho Trainer sau khi
  artifact run mới đã tạo; callback restore dùng default false.
- Xử lý: resume run directory gốc, validate đủ state/hash/config/global step,
  bật callback restore, giữ data skip và full trainer checkpoint.
- Kiểm chứng: simulated complete/corrupt/config-drift/dataset-drift checkpoint
  tests đạt; resume thật vẫn chờ GPU smoke.

## ERR-20261014-08

- Task: TASK-20261014-02.
- Triệu chứng: teacher-forced loss được trung bình theo example; BLEU/
  chrF aggregate là trung bình sentence score; generalization gap trộn final
  training log loss với validation evaluation loss.
- Nguyên nhân: aggregation ban đầu không giữ denominator target token và
  không tách corpus metric; hai loss lấy từ hai loại event Trainer.
- Xử lý: weighted target-token loss/perplexity, corpus BLEU/chrF và evaluate
  cả train/validation bằng best-restored model trước khi tính gap.
- Kiểm chứng: metric fixture và reference-exclusion/token-weight test đạt.

## ERR-20261014-09

- Task: TASK-20261014-02.
- Triệu chứng: `test_multiturn` mong `response_format == "json"` trong khi
  structured answer runtime truyền `answer_schema(False)`.
- Nguyên nhân xác nhận: expectation của test lỗi thời; schema là hành vi
  chủ ý được các test routing/provider khác bảo vệ.
- Xử lý: cập nhật assertion sang `answer_schema(False)`; không đổi runtime.
  Provider vẫn xử lý chuỗi `json` cho caller cũ nên backward compatibility giữ nguyên.
- Kiểm chứng: full suite 136 test đạt, 1 optional skip, 0 failure.

## ERR-20261014-10

- Task: TASK-20261014-02.
- Triệu chứng: test threshold early stopping với improvement đúng bằng
  0,01 bị reset patience do sai số floating-point.
- Nguyên nhân: biểu thức `best_loss - loss > threshold` tạo giá trị nhỉnh
  lớn hơn 0,01 trong binary float.
- Xử lý: so sánh `loss < best_loss - threshold`; test patience/threshold/tie
  và callback Transformers state transition đều đạt.

## ERR-20261014-11

- Task: TASK-20261014-03.
- Triệu chứng: smoke train thành công nhưng hai phép evaluate cuối với prefix
  `final_validation`/`final_training` khiến `EarlyStoppingCallback` cảnh báo thiếu
  `eval_loss` và tự vô hiệu ở phase hậu kiểm.
- Nguyên nhân: callback chỉ hiểu metric key của evaluation trong training, nhưng
  vẫn còn gắn vào Trainer khi chạy audit loss với prefix riêng sau khi train xong.
- Xử lý: tháo `EarlyStoppingCallback` sau khi đã chọn/restore best checkpoint và
  trước hai final evaluation; không thay đổi callback state đã lưu trong checkpoint.
- Kiểm chứng: sẽ chạy resume thật từ checkpoint-2 và kiểm state/hashes; test tĩnh
  cùng smoke sau sửa được ghi ở implementation history khi hoàn tất.

## ERR-20261014-12

- Task: TASK-20261014-03.
- Triệu chứng: sau resume từ checkpoint-2, adapter/scheduler/RNG hash, loss, gradient,
  LR và best metric khớp run không gián đoạn, nhưng hash byte `optimizer.pt` khác.
- Giả thuyết: Torch pickle có biểu diễn byte không ổn định dù state tensor giống nhau;
  chỉ so hash toàn file là tiêu chí quá chặt và chưa chứng minh optimizer bị reset.
- Xử lý: giữ kết quả ban đầu là FAIL, chạy thêm một smoke không gián đoạn cùng seed,
  rồi so sánh đệ quy key/dtype/shape/value tensor của optimizer state; chỉ PASS nếu
  state ngữ nghĩa và adapter cuối đều bằng nhau.

## ERR-20261014-13

- Task: TASK-20261014-03.
- Triệu chứng: sau resume checkpoint-2→4, metric time/optimizer-step lấy runtime
  của riêng invocation resume nhưng chia cho global step 4, làm thời gian bị thấp
  hơn thực tế khoảng hai lần.
- Nguyên nhân: code không lưu global step bắt đầu từ checkpoint.
- Xử lý: đọc `trainer_state.json` đã validate, lưu `resume_start_global_step`,
  tính số step thực thi trong invocation và dùng mẫu số đó cho timing.
- Kiểm chứng: chạy lại resume thật và acceptance gate sau sửa.

## ERR-20261014-14

- Task: TASK-20261014-03.
- Triệu chứng: full suite trong `.venv-qlora` chạy 116 test, 12 error/2 skip;
  toàn bộ error do `ModuleNotFoundError: faiss`, trong khi 21 test QLoRA đã đạt.
- Nguyên nhân: requirements QLoRA cố ý không kéo stack RAG, nhưng full suite có
  test artifact/embedding/RAG cần dependency `faiss-cpu` thuộc extra test của repo.
- Xử lý: cài package editable với extra `test` trong chính venv để kiểm toàn repo,
  sau đó chạy lại `pip check` và full suite; lượt hai còn 1 error do
  `sentence_transformers` thuộc extra `embedding`, nên cài thêm đúng extra này.
  Không thay pin QLoRA production.

## ERR-20261014-15

- Task: TASK-20261014-04.
- Triệu chứng: `start_qlora.ps1 -DryRun` lỗi parse trên Windows PowerShell 5.1;
  chuỗi tiếng Việt UTF-8 không BOM bị giải mã theo ANSI, tạo ký tự phá cú pháp.
- Nguyên nhân: Windows PowerShell 5.1 không mặc định đọc source `.ps1` UTF-8
  không BOM, trong khi repository lưu text UTF-8 chuẩn.
- Xử lý: giữ tài liệu tiếng Việt nhưng dùng chuỗi ASCII trong toàn bộ `.ps1`,
  tương thích cả Windows PowerShell 5.1 và PowerShell 7; chạy lại AST/dry-run.

## ERR-20261014-16

- Task: TASK-20261014-04.
- Triệu chứng: phép thử status mock bằng cách tạo rồi xóa đệ quy artifact tạm bị
  policy công cụ chặn trước thực thi.
- Nguyên nhân: command test chứa `Remove-Item -Recurse`; không phải lỗi script.
- Xử lý: không retry/xóa bằng đường vòng; dùng AST parse, start/TensorBoard dry-run
  read-only và unit mock callback/stop protocol. Không có artifact mock được tạo.

## ERR-20261014-17

- Task: TASK-20261014-05.
- Triệu chứng: lệnh kiểm tra cuối gọi `git` theo PATH thất bại với
  `CommandNotFoundException`; các lệnh test trước đó vẫn hoàn tất.
- Nguyên nhân: Git đã cài nhưng thư mục executable không có trong PATH của PowerShell
  hiện tại.
- Xử lý: gọi trực tiếp `C:\Program Files\Git\cmd\git.exe` cho `diff --check` và
  `status --short`; diff-check đạt. Không sửa PATH hệ thống.

## ERR-20261014-18

- Task: TASK-20261014-07.
- Triệu chứng: mock test backend QLoRA thất bại khi so chuỗi đường dẫn temp tuyệt đối;
  Windows trả một phía dạng tên dài và phía còn lại dạng 8.3 (`EZYCLO~1`).
- Nguyên nhân: hai biểu diễn trỏ cùng thư mục nhưng chuỗi không bằng nhau.
- Xử lý: assertion kiểm đúng tên artifact `best_adapter`, không giả định cách Windows
  chuẩn hóa phần thư mục cha. Chạy lại full suite đạt.

## ERR-20261014-19

- Task: TASK-20261014-07.
- Triệu chứng: run QLoRA QA-v4 đầu tiên có 9/9 failed; nội dung sinh hợp lệ nhưng
  parser báo JSON decode và mỗi câu bị generate hai lần nên chậm.
- Nguyên nhân: adapter được SFT bằng plain assistant answer, trong khi backend mới
  áp contract JSON/action của baseline Ollama mà model không được train để sinh.
- Xử lý: dùng đúng plain-answer contract, bỏ retry; ghi `action_status=unavailable`,
  sửa scorer/paired compare không bịa action metric. Dùng output filename mới vì
  artifact lỗi cũ được giữ lại, không ghi đè/xóa tự động.
- Kiểm chứng: 29 test QA-v4 và full suite 139 passed, 2 skipped, 40 subtests; Ruff,
  compileall và diff-check đạt.

# ERR-20261014-20

- Task: TASK-20261014-08.
- Triệu chứng: lần gọi công cụ vẽ đầu tiên bằng
  `.venv-qlora\Scripts\python.exe` bị PowerShell hiểu `.venv-qlora` là module;
  đồng thời checkout hiện tại không có thư mục `.venv-qlora`.
- Nguyên nhân: thiếu tiền tố đường dẫn tương đối `.\` và môi trường QLoRA từng
  dùng trên máy tạo artifact không được chuyển vào checkout này.
- Xử lý: kiểm tra các venv hiện có, dùng `.\env\Scripts\python.exe` đã có đủ
  matplotlib/pandas để chạy `training.plot`; lệnh hoàn tất exit 0 và sinh đủ plot.
- Phòng tránh: trên PowerShell luôn gọi executable tương đối bằng `.\`; kiểm tra
  `Test-Path` trước và thay tên venv trong lệnh theo môi trường thực tế.

# ERR-20261015-01

- Task: TASK-20261015-01.
- Triệu chứng: PowerShell không nhận
  `.\.venv-qlora\Scripts\python.exe` khi chạy QA-v4 score.
- Nguyên nhân xác nhận: checkout hiện tại không có `.venv-qlora`; terminal dùng
  `env`. `env` có Python 3.14.7, `bert-score` 0.3.13 và package editable, nhưng
  Torch là `2.14.0+cpu`, `torch.cuda.is_available()` trả false.
- Xử lý: không chỉ thay đường dẫn rồi giữ `--bert-device cuda`, vì sẽ lỗi tiếp.
  Có thể chạy CPU bằng interpreter `env`, hoặc cài Torch CUDA tương thích rồi
  xác minh CUDA trước khi chạy scorer. Chưa tự thay dependency môi trường.

# ERR-20261015-02

- Task: TASK-20261015-01.
- Triệu chứng: `qa-v4 score --dataset Data\tthc_test_case_v1 --split test` báo
  không tìm thấy cases dù `data\test.jsonl` tồn tại.
- Nguyên nhân: resolver chỉ hỗ trợ layout cũ `data\rag\test.jsonl`, chưa hỗ trợ
  layout phẳng hiện tại `data\test.jsonl`.
- Xử lý: bổ sung candidate layout phẳng sau candidate `data\rag`, thêm regression
  test cho cả cases và queries. Lượt test đầu gọi nhầm Python hệ thống nên không
  import được package; chạy lại bằng `env\Scripts\python.exe` đạt 2/2 test.
- Kiểm chứng: resolver trả đúng `data\test.jsonl` và `data\test_queries.jsonl`.

# ERR-20261015-03

- Task: TASK-20261015-01.
- Triệu chứng: sau khi sửa resolver dataset, scorer báo không tồn tại
  `outputs\tthc_test_case_v1\predictions_qwen_qlora_batch4.jsonl`.
- Nguyên nhân: artifact thực tế nằm lồng thêm một cấp tại
  `outputs\tthc_test_case_v1\tthc_test_case_v1\...`.
- Xử lý/kiểm chứng: file thực có 1.000 dòng; run report ghi 1.000 successful,
  0 failed. SHA-256 của query hiện tại khớp provenance
  `f4e180b70af50fc69fd39f236ecc2f3e77a028de6e30dbe8d4991cc24b01d4f4`.
  Không di chuyển hoặc đổi tên artifact; dùng đúng đường dẫn lồng khi chấm.

# ERR-20261015-04

- Task: TASK-20261015-03.
- Triệu chứng: phép kiểm tra overlap bằng hashtable PowerShell phát sinh nhiều lỗi
  `Index operation failed; the array index evaluated to null`.
- Nguyên nhân: các ca `clarify` hợp lệ có `document_id` và `procedure_family_id`
  bằng null; lệnh đầu dùng trực tiếp hai giá trị này làm khóa hashtable.
- Xử lý/kiểm chứng: lọc null trước khi tạo tập ID và đếm lại. Kết quả xác nhận
  564/1.000 ca test trùng document với train và 571/1.000 trùng procedure family.

# ERR-20261015-05

- Task: TASK-20261015-04.
- Triệu chứng: test chuyển backend đầu tiên gọi một request có danh sách model
  `[local, qlora, local]` và bị từ chối với `Danh sách model bị trùng`.
- Nguyên nhân: API chủ ý không cho cùng model ID xuất hiện hai lần trong một request;
  test đã mô phỏng lần chuyển ngược không đúng hợp đồng API.
- Xử lý/kiểm chứng: tách thành request đầu `local → qlora` và request kế tiếp
  `local`; xác nhận Ollama unload một lần và cache Transformers release một lần.

# ERR-20261015-06

- Task: TASK-20261015-05.
- Triệu chứng: lựa chọn QLoRA trên web trả lỗi `Using a device_map ... requires
  accelerate` khi `AutoModelForCausalLM.from_pretrained(..., device_map="auto")`.
- Nguyên nhân xác nhận: interpreter chạy web là `env\Scripts\python.exe` nhưng
  không có `accelerate`; kiểm kê tiếp cho thấy cũng thiếu `peft` và `bitsandbytes`,
  là hai dependency bắt buộc tiếp theo cho adapter PEFT/NF4.
- Xử lý/kiểm chứng: cài đúng các phiên bản đã ghim vào `env`; import, `pip check`,
  NF4 CUDA forward và smoke adapter thật sau các sửa tiếp theo đều đạt.

# ERR-20261015-07

- Task: TASK-20261015-05.
- Triệu chứng: sau khi cài dependency, `device_map="auto"` báo một số module bị
  dispatch sang CPU/disk vì không đủ VRAM 6 GB.
- Nguyên nhân: model Qwen 7B NF4 cùng adapter/overhead vượt quyết định đặt tự động
  trên khoảng 4,9 GiB VRAM đang trống.
- Thử sửa chưa thành công: bật CPU offload và giới hạn 4,5 GiB GPU/3 GiB CPU.
  Transformers 5.17.0 lỗi `Params4bit ... _is_hf_initialized`; bản 4.57.3 tiếp
  tục lỗi `Tensor.item() cannot be called on meta tensors` trong Accelerate hook.
- Xử lý cuối: không dùng CPU offload; ép NF4 lên GPU đơn bằng `device_map={"": 0}`.
  Smoke thật PASS, allocated 5,35 GiB; cần đóng ứng dụng GPU khác để có biên nhớ.

# ERR-20261015-08

- Task: TASK-20261015-05.
- Triệu chứng: stack ban đầu có Transformers 5.17.0, lệch với requirements và run
  đã xác minh, gây lỗi hook bitsandbytes khi thử CPU offload.
- Nguyên nhân: môi trường `env` phục vụ RAG/BERTScore đã nâng Transformers, trong
  khi QLoRA artifact/tooling ghim `transformers==4.57.3`.
- Xử lý/kiểm chứng: hạ riêng Transformers về 4.57.3 (hub 0.36.2, tokenizers
  0.22.2), giữ Torch CUDA 2.14.0; `pip check`, import, test và smoke thật đạt.

# ERR-20261015-09

- Task: TASK-20261015-06.
- Triệu chứng: lệnh `rg` dùng glob Windows trực tiếp
  `Data/tthc_test_case_v1/data/*_sft.jsonl` báo filename syntax không hợp lệ.
- Nguyên nhân: PowerShell/rg trên Windows không nhận glob đó như đường dẫn literal
  ở vị trí file argument.
- Xử lý: dùng các đường dẫn split cụ thể đã kiểm tra và corpus/meta trực tiếp;
  không ảnh hưởng kết luận document `1.009646` không có trong SFT.

# ERR-20261015-10

- Task: TASK-20261015-07.
- Triệu chứng: baseline readiness trả `BLOCKED`; full suite có 1 failure vì ba
  file SFT dưới `data/fintuning` không tồn tại.
- Nguyên nhân: profile RTX 5060 Ti giữ layout từ host tạo artifact, trong khi
  checkout hiện tại lưu ba file SFT trực tiếp dưới `data/`.
- Xử lý: profile canonical dùng layout thực tế; alias cũ kế thừa profile mới.
  Không sửa snapshot config trong run lịch sử. Full suite sau sửa đạt 150 test,
  1 optional skip.

# ERR-20261015-11

- Task: TASK-20261015-07.
- Triệu chứng: lệnh kiểm tra AST PowerShell đầu tiên lỗi parser tại chuỗi
  `"$script: $_"` trước khi chạy test.
- Nguyên nhân: dấu hai chấm ngay sau tên biến làm PowerShell hiểu sai variable
  reference trong chính lệnh kiểm chứng, không phải lỗi script dự án.
- Xử lý: đổi thành `"${script}: $_"`; lần chạy lại 18 test tập trung, Ruff và AST
  sáu script đều pass.

# ERR-20261015-16

- Task: TASK-20261015-11.
- Triệu chứng: `quick_validate.py` lỗi `UnicodeDecodeError` khi đọc SKILL.md có
  tiếng Việt trên Windows mặc định CP1252; các test dự án vẫn đạt.
- Nguyên nhân đã xác nhận: validator dùng `Path.read_text()` không chỉ định
  encoding và interpreter chưa bật UTF-8 mode.
- Xử lý: chạy lại với `PYTHONUTF8=1`; validator trả `Skill is valid!`.
- Phòng tránh: chạy các validator skill chứa Unicode với UTF-8 mode trên Windows.

# ERR-20261015-15

- Task: TASK-20261015-10.
- Triệu chứng: `vigov ask --help` lỗi `UnicodeEncodeError` trên Windows CP1252
  khi Rich render mô tả argument tiếng Việt; các help khác và routing test đạt.
- Nguyên nhân đã xác nhận: console script Typer render help trước khi compatibility
  entry point gọi `configure_console`, và CP1252 không mã hóa được ký tự tiếng Việt.
- Xử lý: đổi mô tả argument mới sang English/ASCII nhất quán với command tree và
  thêm test `--help` riêng cho web, ask, ingest, embed.
- Phòng tránh: mọi command/leaf mới phải có test help trực tiếp trên Windows,
  không chỉ kiểm tra help của group cha.

# ERR-20261015-14

- Task: TASK-20261015-09.
- Triệu chứng: kiểm tra link mới ban đầu phát hiện 5 link chết sau khi tăng độ
  sâu thư mục; hai lần thay đường dẫn dataset đầu chưa bỏ được đoạn `data/rag`.
- Nguyên nhân đã xác nhận: liên kết tương đối vẫn tính từ gốc `docs/`; một số
  đường dẫn dataset/artifact lịch sử vốn không còn tồn tại trong checkout, và
  thứ tự thay thế trong hashtable PowerShell không được bảo đảm.
- Xử lý: sửa link theo vị trí thật `Data/tthc_test_case_v1/data`, đổi artifact
  vắng mặt thành ghi chú provenance không clickable, rồi thêm test link local.
- Kết quả: test link và full suite đều đạt; không còn link local bị hỏng.
- Phòng tránh: mọi lần di chuyển Markdown phải chạy `tests.test_documentation`;
  khi nhiều replacement chồng nhau phải thay chuỗi cụ thể trước chuỗi chung.

# ERR-20261015-13

- Task: TASK-20261015-08.
- Triệu chứng: lượt test tập trung đầu tiên có 2 error và 1 failure vì còn tìm
  `configs/base.yaml` và `configs/experiments/smoke.yaml`; lệnh kiểm tra YAML
  training riêng cũng lỗi cú pháp do escape quote trong PowerShell one-liner.
- Nguyên nhân đã xác nhận: ba tham chiếu trong `doctor`/test chưa được thay ở
  lượt tìm kiếm đầu; lỗi one-liner thuộc lệnh kiểm chứng, không thuộc loader.
- Xử lý: cập nhật `doctor` và test sang `configs/training/...`; chạy lại kiểm tra
  YAML bằng script ngắn không phụ thuộc escape lồng nhau.
- Phòng tránh: sau migration đường dẫn phải tìm cả chuỗi dựng bằng `Path(...)`,
  không chỉ tìm literal hoàn chỉnh có dấu gạch chéo.

# ERR-20261015-12

- Task: TASK-20261015-07.
- Triệu chứng: session test tập trung từ lượt trước không còn tồn tại khi tiếp tục,
  `write_stdin` trả `Unknown process id 71625`.
- Nguyên nhân: handle công cụ đã hết hiệu lực qua ranh giới lượt; không có bằng
  chứng process test còn sống và không phải lỗi mã nguồn.
- Xử lý: chạy lại đúng gate tập trung một lần; 20 test và Ruff đều pass, sau đó
  full suite cuối đạt 156 test, 1 optional skip.

# ERR-20261015-20 - TASK-20261015-12

- Triệu chứng: lần sửa assertion đầu vẫn fail với description hợp lệ dùng
  `Use before` thay vì `Use for/when`.
- Nguyên nhân: test tiếp tục kiểm tra wording cụ thể thay vì invariant là mô tả
  phải có điều kiện sử dụng.
- Khắc phục: kiểm tra marker trung lập `Use`, còn semantic boundaries được kiểm
  qua positive/negative scenario trong báo cáo.

# ERR-20261015-19 - TASK-20261015-12

- Triệu chứng: test manifest đầu tiên fail vì assertion chỉ chấp nhận cụm
  `Use for`, trong khi một description hợp lệ dùng `Use when`.
- Bối cảnh: `python -m unittest tests.test_agent_skills tests.test_documentation`;
  15 lần `quick_validate.py` trước đó đều đạt.
- Nguyên nhân: test local hẹp hơn quy tắc mô tả skill thực tế, không phải lỗi
  frontmatter hoặc discovery.
- Khắc phục: assertion chấp nhận cả `Use for` và `Use when`; chạy lại toàn bộ gate.

# ERR-20261015-18 - TASK-20261015-12

- Triệu chứng: patch tạo docs bị hủy vì tìm tiêu đề `# Tài liệu ViGovBot`, trong
  khi file hiện tại dùng `# Hệ thống tài liệu ViGovBot`; không có file partial.
- Nguyên nhân: context patch không khớp nội dung UTF-8 thực tế.
- Khắc phục: đọc lại heading, chia patch thành nhóm nhỏ và áp lại đúng context.

# ERR-20261015-17 - TASK-20261015-12

- Triệu chứng: lệnh PowerShell lấy metadata GitHub báo `An empty pipe element is
  not allowed` tại pipeline ngay sau `foreach`.
- Nguyên nhân: khối `foreach` chưa được bọc thành collection trước pipeline.
- Khắc phục: bọc bằng `@(foreach (...){...})`, sau đó pipe collection sang JSON;
  metadata bảy repository được lấy thành công.

# ERR-20261015-22 - TASK-20261015-14

- Triệu chứng: `quick_validate.py` PASS 13 skill migration nhưng ném
  `UnicodeDecodeError` khi đọc ba `SKILL.md` tiếng Việt thuộc workflow dự án.
- Bối cảnh: Windows, Python 3.14; validator gọi `Path.read_text()` không chỉ định
  encoding nên tiến trình mặc định CP1252.
- Nguyên nhân xác nhận: cùng file đọc được bằng UTF-8 trong repository/test;
  lỗi xuất hiện trước bước parse manifest và byte báo lỗi là UTF-8 hợp lệ.
- Cách sửa/thử lại: chạy validator với biến tiến trình `PYTHONUTF8=1`, không đổi
  nội dung skill hoặc encoding file.
- Kết quả: chạy lại với `PYTHONUTF8=1` PASS 16/16 skill; đây là lỗi locale của
  công cụ, không phải manifest không hợp lệ.
- Tránh lặp: trên Windows bật UTF-8 mode khi chạy validator upstream chưa ghim
  encoding.

# ERR-20261016-01

- Task: `TASK-20261016-01`.
- Triệu chứng: container `web` chuyển sang `unhealthy` sau ba phút; HTTP cổng
  8000 chưa bind, trong khi process Python vẫn chạy và dùng CPU/I/O.
- Bối cảnh: lần khởi động Docker đầu tiên với volume `rag-cache` trống.
- Nguyên nhân xác nhận: `prepare_corpus()` đang sao chép index và xây metadata
  cache; volume đã có 688 MB và file `metadata_*.partial`. `start_period=180s`
  ngắn hơn thời gian khởi tạo thực tế, không có exception ứng dụng.
- Xử lý: tăng healthcheck `start_period` lên 10 phút; giữ nguyên process
  hiện tại để hoàn tất cache, không xóa volume hay khởi động job trùng.
- Phòng tránh: phân biệt thời gian warm-up volume trống với readiness của
  các lần chạy sau; chỉ đọc log/artifact sau khi mốc health bị vượt.

# ERR-20261016-02

- Task: `TASK-20261016-01`.
- Triệu chứng: lệnh unittest targeted báo `ModuleNotFoundError` cho
  `tests.test_rag_config`; bảy test còn lại PASS.
- Nguyên nhân: gọi nhầm tên module; file thực tế là
  `tests/test_rag_config_cli.py`.
- Xử lý: chạy lại với `tests.test_rag_config_cli` và giữ kết quả lần
  sai là FAIL công cụ, không ghi thành lỗi sản phẩm.
- Phòng tránh: liệt kê `rg --files tests` và dùng đúng basename trước
  khi ghép lệnh unittest targeted.

# ERR-20261016-03

- Task: `TASK-20261016-02`.
- Triệu chứng: công cụ chặn lệnh PowerShell gộp uninstall Ollama và xóa ba
  thư mục trước khi process được tạo.
- Nguyên nhân: một lệnh gộp nhiều thao tác destructive và biến target bị
  policy an toàn từ chối dù các path đã được preflight.
- Xử lý: chưa có thay đổi; tách uninstall và từng lệnh xóa với path
  tuyệt đối đã xác minh.
- Phòng tránh: không gộp uninstall với recursive delete trong cùng process.

# ERR-20261016-04

- Task: `TASK-20261016-05`.
- Triệu chứng: hai lệnh PowerShell `Remove-Item -Recurse` để dọn `__pycache__`
  dưới hai cây shim bị policy công cụ từ chối trước khi tạo process.
- Nguyên nhân: thao tác recursive delete bị chặn dù target đã được giới hạn trong
  workspace; source được track trước đó đã xóa thành công bằng patch.
- Xử lý: dùng `git clean -ndX -- training src/training` để xem trước đúng hai cache,
  sau đó `git clean -fdX` cho đúng hai path và xóa hai thư mục rỗng không recursive.
- Kết quả: `training/` và `src/training/` không còn trên filesystem; không có
  file ngoài hai cache ignored bị xóa.

# ERR-20261016-05

- Task: `TASK-20261016-05`.
- Triệu chứng: targeted test trong image inference chạy 59 ca với 1 fail tại
  assertion ROUGE-L, 55 pass và 3 optional skip.
- Lệnh: `docker run --rm --gpus all -v "${PWD}:/workspace" ... vigovbot-web
  python -m unittest ...`.
- Nguyên nhân xác nhận: image `vigovbot-web` cài extra `rag,gpu`, không cài
  `rouge-score`; `generation_metrics()` trả `rouge_l=None`. Không phải lỗi import
  sau migration namespace.
- Xử lý: giữ nguyên metric contract và image inference; chạy verification migration
  không phụ thuộc dependency tùy chọn, đồng thời ghi full suite là chưa đạt trong
  môi trường image inference hiện tại.
- Phòng tránh: không dùng image inference để tuyên bố full test PASS khi chưa cài
  extra `test`/`evaluation`; phân biệt dependency thiếu với regression source.

# ERR-20261016-06

- Task: `TASK-20261016-05`.
- Triệu chứng: lệnh `docker run ... /bin/sh -lc` gộp install, test và wheel kết
  thúc ngay với `Syntax error: Unterminated quoted string`.
- Nguyên nhân: chuỗi PowerShell, shell Linux và Python `-c` lồng ba tầng quote.
  Container kiểm thử chưa chạy và source không bị thay đổi.
- Xử lý: tách thành container tạm chạy nền và từng lệnh `docker exec` độc lập để
  giữ quoting/exit code rõ ràng; xóa container sau kiểm chứng.
- Phòng tránh: không gộp Python inline có quote phức tạp vào `sh -lc` qua PowerShell.

# ERR-20261017-01

- Task: `TASK-20261017-01`.
- Triệu chứng: full suite đầu tiên trong image inference có 1 fail do
  thiếu `rouge-score` và 1 error do test patch module evaluation phụ thuộc thứ
  tự import; wheel đầu tiên còn chứa `vigovbot/qa_v4`.
- Nguyên nhân: image production không có extra test; test dùng chuỗi patch
  khi submodule chưa được import; `build/lib` cũ còn source đã xóa.
- Xử lý: patch trực tiếp module đã import, chạy suite trong container tạm
  có `.[test,dev]`, dọn chính xác `build`/`dist`/egg-info và build lại sạch.
- Kết quả: 168 test pass, wheel có 0 file qa_v4; không xóa dataset,
  checkpoint, prediction hay artifact lịch sử.

# ERR-20261018-01

- Task: `TASK-20261018-01`.
- Triệu chứng: regression `tests.test_qa_v4` không import được trên
  Python host do thiếu `tqdm`; Ruff trong image inference báo `No module named ruff`.
  Full suite image có failure ROUGE-L `None != 1.0`.
- Nguyên nhân: runtime host đã được dọn dependency; image `vigovbot-web`
  chỉ có dependency inference, không có extra `dev` và `rouge-score`. Failure
  ROUGE-L trùng giới hạn đã ghi tại `ERR-20261016-05`, không do v2.
- Xử lý: chạy source mount read-only trong image cho các nhóm test không
  phụ thuộc ROUGE; 30 test evaluation/QA/docs và 8 test v2 đều pass.
- Kết quả: compileall/diff-check pass; Ruff và full suite được ghi
  SKIPPED/không đạt trong image hiện tại, không cài thêm dependency.
# ERR-20261018-02 - Cổng host 8000 đã được Laravel sử dụng

- Task: TASK-20261018-04.
- Triệu chứng: `docker compose up --build -d` build image thành công sau 750,7
  giây nhưng container web không start do không bind được `127.0.0.1:8000`.
- Tái hiện: Docker báo `Only one usage of each socket address ... permitted`.
- Nguyên nhân xác nhận: `Get-NetTCPConnection` trả PID 9224; tiến trình là
  `C:\php\php.exe -S 127.0.0.1:8000` của dự án Laravel Personal-blog.
- Hướng sửa: không dừng tiến trình ngoài phạm vi; chuyển cổng host mặc định của
  ViGovBot sang 8001 và cho phép ghi đè bằng biến môi trường Compose.

# ERR-20261018-03 - Test host thiếu đường dẫn src trong PYTHONPATH

- Task: TASK-20261018-04.
- Triệu chứng: lần đầu chạy `python -m unittest tests.test_evaluation_v2` trên
  host lỗi `ModuleNotFoundError: No module named 'vigovbot'`.
- Nguyên nhân: source-layout chưa được cài vào Python 3.14 đang gọi và shell
  kiểm chứng chưa đặt `PYTHONPATH=src`; không phải lỗi source Evaluation v2.
- Xử lý và kết quả: đặt `$env:PYTHONPATH='src'`, chạy lại 11 test v2 đều pass;
  không cài thêm dependency và không thay đổi Python hệ thống.

## ERR-20261018-04 — Môi trường kiểm chứng thiếu dependency

- Task: TASK-20261018-07.
- Python 3.14 host không có pydantic/Ruff. Image inference hiện có thiếu matplotlib,
  làm test_pipeline_smoke_evaluate_resume_and_report lỗi khi import evaluation.report.
- Tái hiện: python -m unittest tests.test_rag_config_cli tests.test_documentation -q
  trong image vigovbot-web:latest; kết quả 6 test, 1 error (ModuleNotFoundError).
- Xử lý: chạy 4 test cấu hình/CLI cùng documentation/artifact safety bằng image offline;
  18 test pass. Dùng uvx ruff==0.15.6 kiểm tra hai file thay đổi hành vi: pass.
- Giới hạn: chưa xác nhận bài test pipeline/full suite hoặc môi trường cài từ lock mới.
  Muốn chạy toàn bộ cần môi trường extras test/dev/evaluation phù hợp.

## ERR-20261018-05 — Lỗi trung gian khi refactor helper

- Task: TASK-20261018-08.
- Ruff phát hiện import đặt trước docstring và regex replacement chưa thay hết
  caller scoring. Đã sửa import và dùng helper chung; Ruff pass sau sửa.
- Script sửa file dùng encoding mặc định CP1252 gặp UnicodeDecodeError; đặt
  PYTHONUTF8=1 trước chạy lại. Không thay văn bản bằng ký tự replacement.
- Kiểm chứng cuối: 61 test pass; không còn lỗi import/helper trong phạm vi test.

## ERR-20261018-06 — Import json còn được pipeline sử dụng

- Task: TASK-20261018-09.
- Sau tách routing retry, Ruff báo F821 vì json vẫn phục vụ manifest/report CLI.
- Khôi phục import json trong pipeline; Ruff pass, regression 103 test pass.

## ERR-20261018-07 — Import thừa trong test runtime mới

- Task: TASK-20261018-10. Ruff phát hiện tempfile/Path không được dùng.
- Đã bỏ hai import; Ruff pass và 62 test runtime/regression pass.

## ERR-20261018-08 — Shell wrapper coverage mất exit code

- Task: TASK-20261018-11. Suite đầu ghi OK (194, skip 3), nhưng shell exit lỗi
  Illegal number do nội suy biến PowerShell khi truyền sh -c.
- Thay wrapper bằng scripts/verify_tests.py sử dụng subprocess.returncode;
  chạy lại full suite, exit 0, report đủ và skip ghi rõ. Không dùng exit lỗi
  ban đầu để tuyên bố cả quy trình verification đã pass.

## ERR-20261018-09 — Import sys không còn dùng trong clean-env

- Task: TASK-20261018-13. Bỏ gate sys.platform/version khiến sys dư thừa.
- Ruff F401 phát hiện; bỏ import, Ruff và kiểm tra script pass.
