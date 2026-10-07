# Nhật ký vấp ngã

Chỉ ghi lỗi quan sát được; phân biệt nguyên nhân đã xác nhận với giả thuyết.

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

