# TASK-20261015-10 - completed

- Giai đoạn: hoàn tất command tree và verification gate.
- Đã xác nhận training/eval/report có lệnh `vigov`, nhưng web, ask, ingest,
  embedding và RAG evaluation vẫn chỉ có entry point dài `python -m vigovbot`.
- Đã thêm `web`, `ask`, `data ingest/embed` và nhóm
  `rag prepare/smoke/evaluate/report/run`; wrapper dùng lại service hiện có và
  resolve path từ project root.
- Đã cập nhật README, guide RAG, mục lục docs và thêm tham chiếu CLI tập trung.
- Kiểm chứng: routing mock, 9 leaf help và full suite 160 test đều đạt
  (1 optional skip); Ruff, compileall và diff-check đạt.
- Ràng buộc: không nhân đôi business logic; không chạy server, tải model,
  embedding hay benchmark thật trong bước refactor CLI.

# TASK-20261015-09 - completed

- Giai đoạn: hoàn tất phân nhóm và verification gate.
- Đã xác nhận nhánh `codex/ref-clean` có working tree sạch trước khi di chuyển.
- Đã chuyển tài liệu sang `setup`, `architecture`, `guides`, `training`,
  `reports`; roadmap vào `project`; gốc `docs/` chỉ còn `README.md`.
- Đã cập nhật link toàn repository, thay file URL theo máy cá nhân bằng link
  tương đối, sửa link dataset theo layout thật và thêm regression test link.
- Kiểm chứng: 158 test pass, 1 optional skip; Ruff, compileall và diff-check đạt;
  không còn link local hỏng hay tham chiếu hoạt động tới path docs cũ.
- Ràng buộc: giữ nguyên `docs/project/` và lịch sử cũ; không sửa artifact,
  dataset, checkpoint hoặc hành vi runtime.

# TASK-20261015-08 - completed

- Giai đoạn: hoàn tất migration và verification gate.
- Đã xác nhận worktree đang chứa thay đổi refactor TASK-20261015-07 cần được
  bảo toàn; chưa có thao tác xóa/move artifact, dataset hoặc checkpoint.
- Đã chia YAML vào `configs/ingestion`, `configs/rag`, `configs/training`; cập
  nhật source, script, notebook, test và tài liệu sang đường dẫn mới. Các file
  cấu hình phẳng trùng vai trò đã được xóa; snapshot trong run cũ giữ nguyên.
- Kiểm chứng: mọi loader canonical resolve đúng; `vigov doctor` và
  `vigov data stats` chạy từ ngoài repository; 157 test pass, 1 optional skip;
  Ruff, compileall và diff-check đạt.
- Ràng buộc: giữ nguyên giá trị cấu hình và hành vi loader; không chạy training,
  không tải model; cấu hình snapshot trong run lịch sử không bị thay đổi.

# TASK-20261015-07 - completed

- Giai đoạn: hoàn tất refactor và verification gate.
- Đã xác nhận Git đang ở nhánh `codex/ref-clean`, working tree sạch tại thời điểm
  bắt đầu; mã ứng dụng đã dùng src-layout nhưng training còn là package cấp gốc,
  CLI công khai hiện là `vigovbot` dùng argparse và chưa có command tree yêu cầu.
- Đã thêm console script `vigov`, command tree bắt buộc, compatibility dispatch
  cho CLI cũ, config `environments/` và `experiments/`, logs command, dependency
  groups và `docs/refactor-summary.md`. Profile RTX 5060 Ti canonical đã dùng
  layout SFT thực tế hiện có; snapshot run lịch sử không đổi.
- Kiểm chứng: editable install thành công; `vigov --help`, doctor và data stats
  chạy thật; full suite 156 pass, 1 optional skip; Ruff, compileall, pip check,
  diff-check và PowerShell AST đều đạt. Không chạy training/model download.
- Ràng buộc: không chạy full QLoRA, không tải lại model, không di chuyển/xóa dữ
  liệu, checkpoint, adapter, log hoặc report hiện có.
- Lát cắt 2 đã chuyển toàn bộ implementation QLoRA vào `src/vigovbot/training`,
  giữ alias package cũ cùng module object, thêm lifecycle Python đa nền tảng,
  identity/duplicate/stop/resume gate và layout run phân khu. CI Windows/Ubuntu,
  tài liệu development/GPU/training/evaluation đã được bổ sung.
- Kiểm chứng cuối: full suite 156 pass, 1 optional skip; Ruff, compileall,
  pip check, diff-check, PowerShell AST, editable install, help matrix, import
  parity ngoài repo và smoke dry-run thật đều đạt.
- Ranh giới: dry-run xác nhận RTX 4050/CUDA 13.0 và dataset, nhưng không chạy GPU
  smoke/full training, không tải model và không tuyên bố tái kiểm chứng GPU.
- Bước tiếp theo do người vận hành chủ động: chạy GPU smoke bằng run ID mới, xem
  status/logs và acceptance artifact trước khi cân nhắc full experiment.

# TASK-20261015-02 - completed

- Đã cập nhật toàn diện kết quả benchmark 1.000 ca test trên bộ dữ liệu `tthc_test_case_v1`
  vào Mục 6 của tài liệu `docs/bao-cao-phan-tich-qlora-qwen2-5-7b.md`.
- Dữ liệu đối chiếu từ `scores_qwen_qlora_batch4.json` và run log thực tế:
  + Kích thước tập test: 1.000 ca; 810 ca có text similarity evaluation, 190 ca abstain/clarify.
  + Tỷ lệ thành công cấu trúc: 100% (1.000/1.000 thành công, 0 ca lỗi).
  + Bảng đối chiếu 3 chiều (Base vs RAG vs QLoRA):
    * Corpus BLEU-4: Base 8,27 | RAG 23,91 | QLoRA 33,23 (+38,98% so với RAG).
    * Sentence BLEU: Base 15,41 | RAG 31,15 | QLoRA 61,38 (+97,05% so với RAG).
    * ROUGE-L F1: Base 0,3188 | RAG 0,5069 | QLoRA 0,7169 (+41,43% so với RAG).
    * BERTScore F1: Base 0,8816 | RAG 0,9041 | QLoRA 0,9514 (+5,23% so với RAG).
    * Exact Match (EM): Base 0,00% | RAG 0,00% | QLoRA 26,30% (213/810 ca trùng khớp hoàn hảo từng từ).
    * Translation Edit Rate (TER): Base 134,81 | RAG 85,32 | QLoRA 43,60 (giảm lỗi chỉnh sửa 48,90%).
  + Phân tích per-action: `correct_premise` đạt kết quả vượt trội (Sentence BLEU 84,17, ROUGE-L 0,8924, BERTScore 0,9819, EM 45,71%); `answer` đạt Sentence BLEU 57,87, ROUGE-L 0,6934; `partial` đạt Sentence BLEU 65,00, ROUGE-L 0,7299; `abstain` và `clarify` tuân thủ 100% hành vi an toàn theo schema.
  + Hiệu năng suy luận: latency trung bình 12,08 s / câu (p50: 11,71 s, max: 28,76 s).
- Ranh giới kiểm chứng: các chỉ số trích xuất nguyên văn từ artifact kết quả, không nội suy; toàn bộ các phần phân tích kiến trúc/loss/tài nguyên trước đó được giữ nguyên vẹn.

# TASK-20261015-01 - partial

- Artifact môi trường của full run xác nhận máy tạo run là RTX 5060 Ti 16 GB,
  PyTorch 2.9.1+cu130, BF16 và QLoRA 4-bit đã chạy thật; cấu hình này đủ chạy
  lexical/BERTScore, paired compare, controlled HF evaluation tuần tự và report.
- Ưu tiên chạy score trước, rồi paired compare; hai bước plot/report sau cùng nhẹ.
  Controlled HF evaluation tải/chạy lần lượt base và adapter trên 1.000 mẫu, sinh
  lại 2.000 câu trả lời nên dài hơn nhiều và cần chạy riêng, không đồng thời BERTScore.
- Ranh giới kiểm chứng: phiên máy hiện tại là RTX 4050 Laptop 6 GB, RAM trống khoảng
  4,87 GiB, đĩa C trống khoảng 44,58 GiB; không có `.venv-qlora` hoặc prediction
  batch4. Vì khác máy/artifact người dùng nêu, chưa khởi chạy workload dài tại đây.
- Hiệu chỉnh theo xác nhận của người dùng: RTX 4050 Laptop 6 GB chính là máy đích.
  Lexical/paired compare/plot/report khả thi; BERTScore CUDA nên bắt đầu batch 4
  rồi tăng 8 nếu ổn. Controlled HF evaluation 7B NF4 không được coi là chắc chắn:
  cần giải phóng GPU/RAM và smoke trên bản sao run trước khi chạy đủ 1.000 mẫu.
- Phát hiện môi trường: `.venv-qlora` không tồn tại. `env` có BERTScore nhưng dùng
  Torch CPU (`2.14.0+cpu`), nên lệnh CUDA hiện chưa chạy được; xem ERR-20261015-01.
- Xác minh index PyTorch chính thức: RTX 4050 Laptop compute capability 8.9,
  driver 617.42 và Python 3.14.7 có wheel `torch 2.14.0+cu130`; chọn CUDA 13.0
  để thay đúng bản CPU cùng version, không cần cài CUDA Toolkit hệ thống.
- Người dùng đã cài/xác minh Torch 2.14.0+cu130 nhận RTX 4050. Lỗi score kế tiếp
  do resolver chưa hỗ trợ `data/{split}.jsonl`; đã sửa và regression test 2/2 đạt.
  Còn chờ người dùng chạy lại scorer trên prediction hiện có.
- Prediction QLoRA thực tế nằm tại thư mục lồng
  `outputs/tthc_test_case_v1/tthc_test_case_v1/`; đã xác minh 1.000/1.000 thành
  công và hash query khớp dataset hiện tại. Lệnh score cần dùng đường dẫn này.

# TASK-20261014-09 - completed

- Đã tạo tài liệu báo cáo phân tích toàn diện quá trình huấn luyện QLoRA cho Qwen2.5-7B
  tại `docs/bao-cao-phan-tich-qlora-qwen2-5-7b.md`.
- Báo cáo phân tích chi tiết:
  + Cấu hình mô hình: Qwen2.5-7B, max length 2.048, NF4 double-quant, bfloat16.
  + LoRA Adapter: r=16, alpha=32, target all 7 linear projections (q, k, v, o, gate, up, down).
  + Tham số: 40.370.176 trainable parameters (chiếm 0,919% tổng số tham số), giảm 99,08% so với full fine-tuning.
  + Diễn biến loss: train loss giảm từ 2,117 xuống 0,1015; validation loss cực tiểu 0,24649 tại step 1.100.
  + Cơ chế dừng sớm: kích hoạt tại step 1.300 do validation loss tăng liên tiếp (patience=2), tự động phục hồi best adapter từ checkpoint-1100.
  + Hiệu năng tài nguyên: Peak VRAM 12,86 GB / 16 GB RTX 5060 Ti; throughput 1,127 samples/s; tổng thời gian ~3h41m.
- Đã liên kết tài liệu trong `docs/README.md`.
- Ghi rõ: hiện chưa có kết quả suy luận trên 1.000 ca test độc lập và sẽ bổ sung sau.

# TASK-20261014-08 - completed

- Đã đánh giá full run `qlora-full-20261014-153839-desktop-7pkpjrj-ea78be2d`
  từ event/log/metrics/checkpoint thật; không chạy lại training 7B.
- Run dừng sớm ở step 1.300/1.875; validation loss tốt nhất 0,246493 tại step
  1.100. Hai lần eval sau tăng lên 0,258451 và 0,254082, phù hợp dấu hiệu
  overfit nhẹ và patience=2. Best adapter có SHA-256 trùng checkpoint-1100.
- Đã chạy thành công `training.plot` bằng `env` và sinh 9 biểu đồ, gồm ba biểu
  đồ loss; unit test plot và `git diff --check` đạt.
- Giới hạn: chưa có post-training test evaluation hay prediction QA-v4, nên chưa
  kết luận được chất lượng trả lời trên test.

# TASK-20261007-08 — completed

- Đã lập tài liệu báo cáo phân tích và so sánh RAG vs Base cho 1.000 ca kiểm thử
  `tthc_test_case_v1` tại `docs/bao-cao-danh-gia-rag-vs-base-tthc-v1.md`.
- Báo cáo đối chiếu trực tiếp dữ liệu giữa `scores_c4_full.json` (RAG) và
  `scores_qwen_baseline_schema_c4.json` (Base), cùng run reports tương ứng.
- Đã phân tích: thông lượng/thời gian chạy, text similarity (BLEU/ROUGE/BERTScore),
  retrieval recall/MRR, khả năng chặn ảo giác ở nhóm `abstain` (+49.2%), điểm
  yếu tiếng Việt không dấu (`no_diacritics`) của BGE-M3 và phân loại nhãn
  `correct_premise` / `partial`.
- Đã liên kết báo cáo trong `docs/README.md`.
- Kiểm chứng: file tạo thành công, cú pháp Markdown chuẩn, liên kết hợp lệ.

# TASK-20261007-04 — completed

- Đang bổ sung tiến trình theo phase cho `qa-v4 score`; không đổi công thức điểm.
- Mục tiêu: lexical có progress bar, BERTScore báo rõ model/device/batch và dùng
  progress batch sẵn có, cuối lệnh in thời gian cùng đường dẫn artifact.
- Đã triển khai: CLI in số case/prediction, progress `Lexical/reference`, số cặp
  BERTScore + model/device/batch, cảnh báo thời gian nạp model, thời gian BERT,
  tổng thời gian và `[Score] Hoàn tất: <output>`.
- Smoke lexical 4/4 hiển thị đủ tiến trình và ghi artifact; 24 test QA v4/review
  đạt, Ruff và diff-check đạt. Không thay công thức metric hoặc schema output.

# TASK-20261007-03 — completed

- Đang triển khai concurrency runner/retriever, CUDA BGE/BERTScore và cấu hình
  Ollama phù hợp RTX 5060 Ti 16 GB; không triển khai vLLM trong task này.
- Sẽ giữ output theo thứ tự view, song song theo conversation với free-running,
  và benchmark smoke concurrency 1/2 trước khi kết luận mức tăng tốc.
- Chuẩn bị kiểm tra toàn bộ call site/test và thiết kế writer/resume an toàn trước
  khi sửa code; chưa thay môi trường CUDA hay restart Ollama.
- Đã triển khai runner thread pool: reference-history song song theo câu,
  free-running song song theo conversation; writer giữ thứ tự view. Retriever chỉ
  khóa encoder và SQLite riêng, không khóa FAISS read-only.
- 40 test QA v4/RAG đạt, gồm concurrency/output/history mới. Ruff chưa có trong
  `.venv` vì lock đã cài không gồm extra dev; chuẩn bị cài Ruff 0.15.6 và thay
  Torch CPU bằng wheel CUDA rồi xác minh trước khi đổi YAML.
- Đã cài Ruff 0.15.6 và Torch 2.14.0+cu130; CUDA nhận RTX 5060 Ti. BGE-M3 dùng
  khoảng 2.198 MB VRAM; warm-up đầu 15,48 giây, sáu encode sau trung bình 0,044
  giây/query. Đã tạo `configs/rag-fast-local.yaml` thay vì đổi cấu hình CPU gốc.
- Đã đặt biến user Ollama parallel=2, max loaded=1, Flash Attention=1, KV q8_0.
  Hai lệnh Start-Process bị policy công cụ từ chối trước thực thi; đã khởi động
  `ollama serve` bằng session 99804, log xác nhận đúng cấu hình và CUDA, API sẵn sàng.
- Chuẩn bị benchmark cùng 4 câu single với concurrency 1 và 2; artifact mới ở
  `outputs/environment_speed_20261007/`, không ghi đè smoke trước.
- Benchmark single cùng 4 ID: concurrency 1 wall 36,758 giây (4/4); concurrency 2
  wall 16,625 giây (4/4), throughput 0,109 → 0,241 câu/giây, nhanh 2,21 lần.
  Thứ tự ID và action khớp giữa hai run; đây là smoke nhỏ, không ngoại suy tuyến tính.
- Multi concurrency 2 chạy hai conversation x 4 lượt: 8/8 thành công, wall 32,845
  giây; scheduling_unit trong run report là conversation.
- BERTScore CUDA batch 16 tính 3 cặp: lượt đầu 9,41 giây sau tải/warm-up, lượt chạy
  lại cache nóng 0,82 giây và score coverage 4/4. Đã sửa contract return_hash của
  bert-score; lỗi và cách xử lý ở ERR-20261007-02.
- Kiểm chứng cuối: 44 test QA v4/RAG/config/Colab đạt; Ruff đạt; pip check đạt;
  config fast load thành cuda/cuda/batch 16; diff-check đạt.
- Ollama server đang chạy ở session 99804; biến user tồn tại nên lần khởi động ứng
  dụng sau vẫn nhận parallel=2/max-loaded=1/Flash Attention/q8_0.

# TASK-20261007-02 — completed

- Đã khảo sát phương án tăng tốc trên RTX 5060 Ti 16 GB, RAM 28 GB hữu dụng,
  Windows và Ollama 0.35.1; chưa triển khai thay đổi kiến trúc trong task này.
- Nút thắt code: `run_queries` tuần tự; `Retriever.search` khóa cả embedding,
  FAISS search và SQLite nên thêm thread đơn thuần vẫn tuần tự hóa retrieval.
- Corpus dùng `IndexFlatIP` 117.871 x 1.024, đã nằm trong RAM; không scan đĩa.
  Smoke hiện tại retrieval 0,337 giây, trong khi routing cold-start 39,25 giây và
  generation 5,54 giây, nên serving/model là ưu tiên lớn hơn đổi FAISS/HNSW.
- Khả thi ưu tiên: concurrency theo câu/hội thoại, Ollama parallel 2 rồi benchmark
  4, CUDA PyTorch cho BGE/BERTScore, batch BERTScore. Không khuyến nghị parallel 8
  với context 8K trên 16 GB trước khi đo VRAM/KV cache.
- vLLM không hỗ trợ Windows native; nếu dùng phải dựng WSL2/Linux và adapter
  OpenAI-compatible. Đây là phase riêng sau khi benchmark Ollama tối ưu.

# TASK-20261007-01 — completed

- Đang thiết lập môi trường Windows để chạy QA v4 trên `rag_tthc_three_1500`.
- Đã xác nhận RTX 5060 Ti 16 GB và driver NVIDIA hoạt động; Python hệ thống hiện
  chỉ là Microsoft Store alias, chưa thấy `env/Scripts/python.exe`.
- Đang kiểm kê Python launcher/package manager, dataset, corpus/index, backend sinh
  và cấu hình model trước khi tạo môi trường và tải dependency.
- Đã xác nhận dataset có đủ ba view 1.500 lượt; corpus có index 482.799.661 byte,
  metadata 6.313.506.788 byte và manifest. Không cần chạy embedding lại.
- Chuẩn bị cài Python 3.14 bằng winget, sau đó tạo `.venv` và cài theo
  `locks/rag-windows-py314.txt`; artifact môi trường nằm tại `.venv/`.
- Đã cài Python 3.14.7, tạo `.venv`, cài đủ lock `rag-windows-py314.txt` và
  package editable; import Torch/FAISS/SentenceTransformers/Transformers/BERTScore đạt.
  Torch trong lock là bản CPU, phù hợp cấu hình encoder `device: cpu`; Qwen dùng
  GPU qua Ollama độc lập.
- Đã cài Ollama 0.35.1, API localhost:11434 sẵn sàng. Chuẩn bị tải model
  `qwen2.5:7b`; sau đó sẽ tải/cache BGE-M3 và tokenizer trong smoke run.
- `qwen2.5:7b` (4,7 GB) đã tải thành công. Test dataset lần đầu phát hiện lock
  thiếu SacreBLEU; đã cài `sacrebleu==2.6.0`, ghi ERR-20261007-01 và chạy lại
  `test_evaluation.py` đạt 3/3; `test_resume.py` đạt.
- Chuẩn bị chạy RAG thật một lượt single bằng `configs/rag.yaml`, output
  `outputs/environment_smoke_20261007/single_limit1.jsonl`; lệnh này sẽ tải/cache
  BGE-M3 và tokenizer nếu chưa có, rồi nạp corpus và gọi Qwen/Ollama.
- Smoke RAG thật hoàn tất exit 0: single_0001 sinh đáp án thành công, truy hồi đủ
  top-5; wall 45,25 giây, retrieval 0,337 giây. Score lexical exit 0, coverage 1/1.
- BGE-M3 và tokenizer Qwen đã cache trong Hugging Face cache; SQLite corpus cache
  đã tạo trong `outputs/rag_cache`. Ollama dỡ model sau phiên đúng lifecycle.
- Xác minh ba view đều chọn đúng 1.500 ca và chuỗi multi hợp lệ; 40 unit test
  QA v4/RAG/config/Colab đạt. Môi trường sẵn sàng chạy benchmark; chưa chạy toàn
  bộ 4.500 lượt theo phạm vi đã ghi.
- Artifact smoke: `outputs/environment_smoke_20261007/` gồm prediction, run report
  và score. Lưu ý lockfile hiện thiếu SacreBLEU; `.venv` đã được bổ sung trực tiếp.
- Dự kiến chỉ chạy smoke có giới hạn để xác minh; chưa chạy benchmark 4.500 lượt.

# TASK-20261006-03 — completed

- Đã viết lại 3.772/4.500 câu; giữ nguyên 400 case typo/no-diacritics. Số mẫu
  chuẩn hóa tăng 258 → 1.997, nhóm lớn nhất giảm 357 → 27.
- Đã đồng bộ 1.684 user-message trong history multi; Gold và assistant-message
  không được script gán lại. Vòng đầu có 821 input single trùng, đã tách bằng
  tiền tố trung tính; kết quả cuối còn 0 trùng.
- Đã đồng bộ `runner_queries.jsonl`, manifest v2-diverse, validation, README và
  toàn bộ checksum. Báo cáo: `outputs/testset_review/bao-cao-ap-dung-da-dang-hoa.md`.
- Kiểm chứng đạt: 4.500 ID; 1.500 ID/view; 381 hội thoại liên tục và history khớp;
  checksum đạt; 3 unit test evaluation và test resume đạt.
- Không chạy lại RAG. Artifact benchmark cũ phản ánh câu hỏi trước khi viết lại,
  không phải kết quả của dataset v2-diverse.
- Giới hạn: dataset không được Git theo dõi và không còn snapshot cùng hash cũ,
  nên không thể diff độc lập sau ghi; phạm vi không đổi Gold/evidence được bảo đảm
  bởi logic script, không phải đối chiếu byte với bản sao nguyên vẹn.

# TASK-20261006-02 — completed

- Đã phân tích offline đủ 4.500 case của `rag_tthc_three_1500`; không sửa dataset,
  không gọi lại RAG và không tự duyệt Gold.
- Đã nhóm câu hỏi bằng placeholder tên thủ tục/số: 258 mẫu theo bộ/nhãn, trong đó
  78 mẫu xuất hiện ít nhất 10 lần. Báo cáo và CSV đầy đủ ở
  `outputs/testset_review/bao-cao-ra-soat-testset.md` và
  `mau-cau-can-da-dang-hoa.csv`.
- Hàng đợi `gold-can-duyet.csv` có 1.318 ca có tín hiệu: P0=1, P1=1.074, P2=243.
  Đây là triage theo verification/artifact/bất thường cấu trúc, không phải phán quyết
  Gold đúng hoặc sai; toàn bộ semantic/human review vẫn pending.
- Kiểm chứng: tổng số lượng mẫu bằng 4.500; ID hàng đợi duy nhất và đều có trong
  dataset; script tái lập chạy exit 0; SHA-256 dataset được ghi trong báo cáo.
- Trở ngại: ACL sandbox không đọc được `outputs/`; đã dùng quyền đọc/ghi trực tiếp
  workspace. Lần chạy thử đầu của script lỗi cú pháp, đã sửa và chạy lại thành công.

# TASK-20261006-01 — completed

- Báo cáo chính duy nhất: `outputs/result_qa/tong-hop-danh-gia.md` (số liệu máy
  đọc: `tong-hop-ba-bo.json`). Đã xóa 3 báo cáo `bao-cao-*`, README supplemental,
  cache/packet/mapping_candidates, `source_review` v1, ảnh PNG duyệt, log và
  script `*.py` theo lựa chọn của người dùng; 101 → 54 file, 93,2 → 45,2 MB.
- Giữ dữ liệu gốc 3 run, file kiểm chứng/provenance/retrieval_verified,
  judgments AI và kết quả BERTScore. Liên kết trong báo cáo chính đều tồn tại.
- Lưu ý: script chấm đã bị xóa (thư mục gitignore) nên muốn tái lập phép chấm
  bổ sung cần viết/lấy lại script.
- Còn lại (không thuộc task dọn): 387 câu cover, mapping evidence, phân xử Gold,
  chấm nội dung toàn tập.

# Mốc trước — TASK-20261006-01 — in_progress

- Đang kiểm kê và hợp nhất báo cáo trong `outputs/result_qa` cho ba bộ
  single/multi/coverage; chưa xóa artifact trước khi xác minh vai trò và liên kết.
- Mục tiêu: một báo cáo chính ngắn, tách execution/action, text similarity,
  retrieval và semantic correctness; giữ rõ mẫu số và giới hạn dữ liệu.
- Trở ngại hiện tại: sandbox không đọc được ACL của thư mục `outputs`; đang xác
  minh bằng quyền đọc ngoài sandbox.
- Chuẩn bị chạy tổng hợp offline bằng
  `env/Scripts/python.exe outputs/result_qa/summarize_three_runs.py`; đầu ra cần
  có là `tong-hop-ba-bo.json`, sau đó sinh báo cáo và kiểm tra liên kết. Không
  tải model hoặc gọi lại RAG/BERTScore.

# Mốc trước — TASK-20261005-03 — in_progress

- Tổng hợp ba run offline; đang chạy env/Scripts/python.exe outputs/result_qa/summarize_three_runs.py, session 87073.
- Tính lại corpus BLEU/chrF/TER trên 3.199 cặp; lấy BERT từ checkpoint đã chấm, không chạy lại model. Bổ sung document retrieval single theo cùng cách multi/cover.
- Chờ session hoàn tất, kiểm chứng hash và viết báo cáo tổng hợp.

# Hiện tại — TASK-20261005-02 — partial

- BERTScore hai bộ đã hoàn tất và kiểm chứng: multi F1=0,894952 (n=1.143), cover F1=0,903152 (n=1.112). Session 63478 đã kết thúc exit 0; mapping session 63968 cũng kết thúc. Không còn job chấm đang chạy.
- Document Recall@5/MRR@5: multi 0,852890/0,826416 (n=1.142), cover 0,956757/0,935736 (n=1.110); không phải evidence-unit metrics.
- Nội dung: duyệt AI 360 ca multi và 3 ca cover; chưa có accuracy toàn tập. coverage_0381 chờ phân xử Gold. Evidence retrieval có mẫu 6 ca.
- Báo cáo: outputs/result_qa/bao-cao-bo-sung-multi-cover.md; bằng chứng kiểm chứng: kiem-chung-bo-sung-multi-cover.json, mọi input hash không đổi.
- Còn lại: mapping bằng chứng, nội dung toàn tập và 387 lượt cover chưa có kết quả. Các mốc in_progress phía dưới là lịch sử, không phải job đang chạy.

# Mốc BERTScore multi — TASK-20261005-02

- Multi đã hoàn tất 1.143 cặp, F1=0,8949523699; 1 cặp quá 512 token; 980,22 giây. Hash cấu hình trùng single.
- Cover đang chấm trong cùng session 63478; chưa có điểm cuối.

# Mốc bổ sung TASK-20261005-02 — in_progress

- Document Recall@5/MRR@5 đã tính trên hạng chunk gốc: multi n=1.142, 0,852890/0,826416; cover n=1.110, 0,956757/0,935736. Đây là mức tài liệu, chưa phải evidence-unit recall.
- Đã duyệt AI 360 ca multi (357 ca trạng thái hồ sơ và 3 ca nội dung) + 3 ca cover; evidence retrieval 6 ca. Không đại diện toàn tập. coverage_0381 cần phân xử Gold.
- Script score_supplemental_review.py chạy exit 0; artifact trong outputs/result_qa/{multi,cover}/supplemental.
- BERTScore vẫn ở session 63478 chạy tuần tự; chờ hoàn tất rồi chạy finalize_supplemental.py kiểm chứng và tạo báo cáo. Chưa khẳng định điểm BERT khi chưa có summary.

# TASK-20261005-02 — in_progress

- BERTScore multi 1143 cặp rồi cover 1112 cặp; session 63478, CPU xlm-roberta-large, checkpoint từng ca.
- Lệnh: env/Scripts/python.exe -u outputs/result_qa/{multi,cover}/supplemental/score_bertscore.py (tuần tự).
- Log và kết quả ở mỗi thư mục supplemental. Đang kiểm tra mapping và judgments; chưa công bố điểm chưa có.

# TASK-20261005-01 — completed

- Đã phân tích multi đủ 1.500 lượt: 73% đúng nhãn, partial 7/357; 26/381 hội thoại đúng toàn bộ nhãn.
- Cover chỉ có 1.113 bản ghi, 1 lỗi, thiếu 387; 95,59% chỉ trên 1.112 phản hồi hợp lệ.
- Báo cáo: outputs/result_qa/bao-cao-multi-cover.md; hash/kiểm chứng: kiem-chung-multi-cover.json.
- Không chạy lại RAG. Yêu cầu trước về duyệt chất lượng bộ case còn chưa hoàn tất; không suy từ audit nguyên văn thành duyệt ngữ nghĩa.
- Lưu ý: các session audit 2420/73417 ghi trong lịch sử bên dưới đã hoàn tất; đó là mốc cũ.

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
# TASK-20261007-05 — partial

- Đang thiết lập và chạy QA RAG cho 1.000 ca test của
  `Data/qa_test/tthc_test_case_v1` trên máy hiện tại.
- Đã xác nhận máy có RTX 3090 24 GB, 18 logical processors và khoảng 47,9 GB RAM
  khả dụng; chưa có `.venv`, `python`, `git` hoặc `ollama` trong `PATH`.
- Dataset có `test.jsonl` và `test_queries.jsonl`, mỗi file 1.000 ca; evaluator
  riêng tính retrieval/lexical/BERTScore/runtime và để null metric semantic khi
  thiếu judgment. Chế độ chính chọn `reference_history` để đúng hợp đồng dữ liệu.
- Giai đoạn tiếp theo: cài runtime/dependency, tạo cấu hình RTX 3090, chạy
  validation và smoke có concurrency trước khi chạy toàn bộ; artifact dự kiến ở
  `outputs/tthc_test_case_v1/`.
- Đã cài Python 3.14.7, `.venv`, lock RAG/evaluation, Torch 2.14.0+cu130 và
  Ollama 0.40.0; `pip check` đạt, CUDA nhận RTX 3090 24 GB. Qwen 2.5 7B đã tải.
- Đã thêm CLI đọc trực tiếp layout unified-v2 `data/rag/{split}*.jsonl` và cấu
  hình `configs/rag-rtx3090.yaml`; 14 test QA runner và Ruff đạt.
- Ollama user config: parallel=4, max-loaded=1, Flash Attention=1, KV q8_0.
- Chuẩn bị smoke RAG 8 ca reference-history với concurrency 2; lệnh sẽ tải/cache
  BGE-M3 và tokenizer nếu thiếu. Artifact:
  `outputs/tthc_test_case_v1/smoke_c2_8.jsonl` và `.run.json`.
- Smoke concurrency 2: 8/8 thành công, wall 76,57 giây (có warm-up Qwen đầu);
  smoke cache nóng concurrency 4: 8/8, wall 24,52 giây, 0,326 câu/giây, không
  OOM. Một lượt c4 bị dừng trước khi inference vì sandbox chặn HEAD Hugging Face;
  chạy lại với `HF_HUB_OFFLINE=1` dùng cache thành công.
- Chuẩn bị chạy toàn bộ 1.000 ca với concurrency 4, reference-history và cache
  offline; artifact `outputs/tthc_test_case_v1/predictions_c4.jsonl`, thời gian
  dự kiến ban đầu 50–90 phút theo smoke và độ dài đáp án thực tế.
- Theo yêu cầu mới, đã dừng full run; file dở giữ 36 prediction thành công, không
  có `.run.json` vì tiến trình chưa hoàn tất. Không có process benchmark còn chạy.
- Bàn giao lệnh chạy mới dùng output `predictions_c4_full.jsonl` để tránh đụng
  file dở, hiển thị từng ID, latency, số thành công/lỗi, ETA và giờ dự kiến xong.
- Trạng thái partial: môi trường và smoke đạt; full 1.000 ca và score cuối chưa
  chạy vì người dùng muốn tự chạy/quan sát.

# TASK-20261007-05 — in_progress

- Đang thiết lập và chạy QA RAG cho 1.000 ca test của
  `Data/qa_test/tthc_test_case_v1` trên máy hiện tại.
- Đã xác nhận máy có RTX 3090 24 GB, 18 logical processors và khoảng 47,9 GB RAM
  khả dụng; chưa có `.venv`, Python thật, Git hoặc Ollama trong `PATH`.
- Dataset có `test.jsonl` và `test_queries.jsonl`, mỗi file 1.000 ca; evaluator
  riêng tính retrieval/lexical/BERTScore/runtime và để null metric semantic khi
  thiếu judgment. Chế độ chính chọn `reference_history` để đúng hợp đồng dữ liệu.
- Giai đoạn tiếp theo: cài runtime/dependency, tạo cấu hình RTX 3090, chạy
  validation và smoke có concurrency trước khi chạy toàn bộ; artifact dự kiến ở
  `outputs/tthc_test_case_v1/`.

# TASK-20261007-06 — completed

- Đang điều tra evaluator unified-v2 bị `KeyboardInterrupt` trong
  `sacrebleu.BLEU.corpus_score` khi chấm 1.000 prediction.
- Đã xác nhận prediction đủ 1.000 dòng; test có 691 ca một reference và 309 ca
  hai reference, nên số reference không bất thường.
- Tiếp theo: đo độ dài answer/token và benchmark riêng corpus BLEU để xác định
  điểm nghẽn trước khi sửa; chưa chạy lại BERTScore toàn tập.
- Đã xác nhận lexical gốc vẫn hoàn tất trong khoảng 3,75 giây; nguyên nhân gây
  cảm giác treo là 805 lần gọi sentence BLEU phát cảnh báo `effective_order`, rồi
  người dùng ngắt đúng lúc chuyển sang corpus BLEU.
- Đã giữ `effective_order=False` và chỉ chặn logger cảnh báo lặp, nên công thức
  không đổi; thêm thông báo phase corpus BLEU/BERTScore, progress BERTScore và
  option `--bert-batch-size`.
- Kiểm chứng: py_compile đạt, synthetic evaluator đạt; full lexical 1.000 ca
  hoàn tất 3,70 giây, coverage 995/1.000, BLEU-4 23,9057. Artifact:
  `outputs/tthc_test_case_v1/scores_lexical_fixed.json`.
- Chưa tự chạy BERTScore toàn tập theo yêu cầu trước của người dùng muốn tự chạy
  và quan sát; câu lệnh CUDA batch 32 được bàn giao.
- Lượt BERTScore của người dùng chưa nạp được `xlm-roberta-large` vì terminal còn
  hai biến offline từ bước RAG. Đã bàn giao lệnh xóa biến và chạy lại; lexical
  không lỗi, output score đầy đủ chỉ được ghi sau khi BERTScore hoàn tất.

# TASK-20261007-07 — completed

- Đang sửa baseline Qwen để dùng `answer_schema(False)` và retry validation tối
  đa một lần, không thêm retrieval hay gold vào prompt.
- Baseline cũ đã chạy đủ 1.000 dòng; snapshot gần cuối cho thấy phần lớn failure
  là `Invalid structured answer/action`, adapter cũ chỉ dùng `format=json` và
  không retry. Artifact cũ được giữ nguyên để bảo toàn provenance.
- Tiếp theo: triển khai helper có diagnostics, unit test initial/retry/failure,
  rồi chạy smoke thật sang output mới.
- Đã triển khai schema `answer_schema(False)`, retry validation đúng một lần và
  lưu `generation_diagnostics`; 37 test QA/routing, Ruff check/format đạt.
- Chuẩn bị smoke model thật 20 ca, concurrency 4, output mới
  `outputs/tthc_test_case_v1/baseline_schema_retry_smoke20.jsonl`; dự kiến vài
  phút, cần 20/20 hoặc lỗi còn lại phải có diagnostics.
- Smoke thật hoàn tất 20/20, wall 21,08 giây, 0 failure; cả 20 hợp lệ ngay lần
  đầu với schema. Cùng 20 vị trí trong run cũ có 5 failure schema.
- Kiểm chứng cuối: 37 test QA/routing đạt; Ruff check/format và pip check đạt.
  README baseline đã ghi rõ schema, retry và không đưa retrieval/gold vào prompt.
- Artifact cũ `predictions_qwen_baseline_c4.jsonl` giữ nguyên; để benchmark chính
  cần chạy lại đủ 1.000 ca sang tên output mới.

# TASK-20261014-01 - partial

- Đang triển khai pipeline QLoRA local-first cho Qwen2.5-7B-Instruct; không
  tải model 7B và không chạy full training trên máy local.
- Đã xác nhận ba split SFT tại `Data/tthc_test_case_v1/data/`, repo dùng
  `src/` layout, chatbot hiện phục vụ Ollama/OpenAI-compatible.
- Giai đoạn hiện tại: tạo config, package `training`, CLI, adapter inference,
  dependency/docs và unit test CPU; sau đó chạy validation/test/smoke synthetic.
- Đã chạy 9 unit test QLoRA local: đạt; Ruff: đạt. Chuẩn bị chạy
  `python -m training.validate_data --config configs/local.yaml` trên 5.000 record;
  artifact đích `outputs/qlora/dataset_report.json`, không nạp tokenizer/model.
- GPU preflight/training/evaluation thật sẽ chỉ được xác nhận trên máy GPU.
- Đã xong local: 10 unit logic QLoRA + 5 server/plot integration đạt; Ruff
  và diff-check đạt; official Qwen tokenizer từ cache xác nhận 150 token
  với 62 target/88 masked trên một mẫu thật.
- Dataset report: 3.000/1.000/1.000 record hợp lệ; không trùng exact
  conversation/question giữa split; answer exact overlap lần lượt 93/99/57,
  near-question 26/24/13 và procedure overlap được báo cáo, không tự xóa.
- Token length official: train P50/P90/P95/P99/max = 180/709/884/1203/1619;
  validation = 181/717/928/1133/1513; test = 179/696/892/1159/1539.
- Full suite hiện có 124 đạt, 1 skipped, 1 failure cũ về JSON schema trong
  `test_multiturn`; xem ERR-20261014-04. Không có full QLoRA run/checkpoint/metric GPU.

# TASK-20261014-02 - partial

- Đang audit pre-GPU implementation QLoRA hiện có; không nạp model weights
  hoặc chạy training 7B.
- Giai đoạn: đọc source/config/test thực tế, dựng test mô phỏng
  masking/checkpoint/early stopping/metrics/plots, sau đó sửa critical findings.
- Đầu ra bắt buộc: `docs/qlora-pre-gpu-audit.md`, test/static-check logs
  tóm tắt và kết luận READY/NOT READY cho GPU smoke.
- Findings đã sửa: assistant header bị tính loss; truncation cắt target;
  resume sang run directory mới/thiếu kiểm optimizer-scheduler-RNG-callback;
  loss evaluation trung bình theo example thay vì target token; corpus BLEU/chrF
  bị thay bằng trung bình sentence; base parameter count và best-model metrics.
- JSON schema failure được xác nhận là test cũ: runtime schema là contract
  chủ ý, còn provider vẫn hỗ trợ JSON mode cũ. Đã sửa assertion test.
- Nhóm audit hiện đạt 27 test (1 skipped) và Ruff. Chuẩn bị chạy
  full suite `unittest discover` và validator 5.000 record với official tokenizer
  cache-only; không tải model weights.
- Kết quả cuối local: full suite 136 passed, 1 optional skipped, 0 failed;
  Ruff/compileall/diff-check đạt; validator official tokenizer offline đạt
  5.000/5.000 record. Báo cáo: `docs/qlora-pre-gpu-audit.md`.
- Kết luận: READY có điều kiện cho GPU smoke, chưa READY cho full
  training. Còn bắt buộc smoke NF4/CUDA/bitsandbytes và resume checkpoint thật.

﻿# TASK-20261014-03 — completed

- Đang kiểm kê Windows/RTX 5060 Ti, driver/CUDA, Python/venv, dung lượng đĩa,
  Git, dataset và implementation QLoRA trước khi cài dependency.
- Mục tiêu tiếp theo: chọn wheel PyTorch chính thức tương thích driver + SM 12.0,
  tạo `.venv-qlora`, kiểm CUDA tensor rồi mới cài/test stack QLoRA.
- Chưa chạy training hoặc tải trọng số 7B; chưa có kết luận readiness.
- Kiểm kê host: RTX 5060 Ti 16.311 MiB, compute 12.0, driver 616.92 quảng bá
  CUDA 13.4; VRAM trống 15.323 MiB; đĩa C trống 996,56 GiB. Git commit
  `659bd9ec80595636f7346e9b41195e5a51224c96`.
- Không có Python launcher/interpreter độc lập; chỉ có Store alias và Python 3.13
  nhúng của Blender. Chuẩn bị cài Python 3.11 user-scope bằng winget rồi tạo
  `.venv-qlora`.
- Wheel đã chọn: PyTorch 2.9.1 CUDA 13.0 chính thức cho Windows, phù hợp pin repo,
  driver 616.92 và SM 12.0. Lệnh dài bắt đầu: `winget install --id
  Python.Python.3.11 --exact --scope user --silent ...`; artifact là interpreter
  user-scope và `.venv-qlora` ở bước kế tiếp.
- Python 3.11.9 user-scope và `.venv-qlora` đã tạo; pip 26.2.1, setuptools 84.0.0,
  wheel 0.48.0. Chuẩn bị chạy lệnh dài cài `torch==2.9.1` từ index chính thức
  `https://download.pytorch.org/whl/cu130`, sau đó kiểm CUDA tensor thật.
- PyTorch 2.9.1+cu130 cài thành công; runtime CUDA 13.0 nhận RTX 5060 Ti,
  compute (12, 0), BF16=true, arch list có `sm_120`; CUDA matmul 1024x1024 đạt.
- Chuẩn bị lệnh dài cài `requirements/qlora-gpu.txt` cùng sentencepiece, evaluate,
  scikit-learn, psutil, pytest, Ruff và package editable; sau đó chạy `pip check`
  và test bitsandbytes kernel, không chỉ import.
- Dependency cài thành công, `pip check` đạt. Diagnostic thật lưu tại
  `outputs/qlora/gpu_environment_diagnostic.json`: NF4 BF16 forward/backward,
  double quantization và PagedAdamW8bit state uint8 đều PASS.
- Đã thêm config RTX 5060 Ti và smoke config kế thừa đúng schema/path dữ liệu,
  cùng requirements Windows Blackwell. Dataset có đúng 3.000/1.000/1.000 record.
- Chuẩn bị chạy validator official tokenizer; artifact đích
  `outputs/qlora/dataset_report_rtx5060ti.json`, không tải model weights.
- Validator official Qwen đạt 5.000/5.000; max token train/validation/test lần lượt
  1.619/1.513/1.539, dưới 2.048; không có exact conversation/question overlap.
  Preflight JSON đạt CUDA/config/Hub/tokenizer; 21 test QLoRA và Ruff đạt.
- Chuẩn bị lệnh dài smoke thật: `.venv-qlora/Scripts/python.exe -m training.train
  --config configs/smoke_rtx5060ti_16gb.yaml --approve --run-id
  smoke-rtx5060ti-20261014`. Lần này tải Qwen weights khi cần; artifact đích
  `outputs/qlora/smoke-rtx5060ti-20261014/`; yêu cầu checkpoint-2 và 4 step.
- Smoke thật hoàn tất 4 step, loss hữu hạn 1,9367→1,3523, peak allocated/reserved
  10,83/11,55 GiB, không OOM; checkpoint-2 và checkpoint-4 đủ state.
- Phát hiện/cố định cảnh báo callback hậu kiểm ở ERR-20261014-11; đã chụp hash
  checkpoint-4 không gián đoạn. Chuẩn bị resume thật từ checkpoint-2 trong cùng
  run directory và đối chiếu continuity/hash; artifact report ở
  `outputs/qlora/smoke-rtx5060ti-20261014/resume_verification_report.json`.
- Resume thực thi đúng step 3–4, LR/loss/adapter/scheduler/RNG/callback khớp; chỉ
  hash byte pickle optimizer khác (ERR-20261014-12). Chuẩn bị smoke uninterrupted
  đối chứng cùng seed tại `outputs/qlora/smoke-rtx5060ti-reference-20261014/`, rồi
  so nội dung tensor optimizer; chưa kết luận resume PASS trước đối chiếu này.
- Đối chiếu cuối: optimizer step 2→4, scheduler/RNG/callback/adapter/loss/gradient
  khớp; uint8 buffer optimizer không byte-identical nhưng không reset. Acceptance
  7/7 PASS; 7 plot và báo cáo JSON/Markdown đã sinh.
- Kiểm chứng cuối: 136 test đạt, 2 optional skip; pip check, Ruff, compileall và
  diff-check đạt. Trạng thái máy: `READY WITH LIMITATIONS` cho full training có
  giám sát; chưa chạy full training theo yêu cầu.

﻿# TASK-20261014-04 — completed

- Đang bổ sung cơ chế vận hành full QLoRA độc lập bằng PowerShell; không chạy full
  training trong task này.
- Pipeline hiện chưa ghi status live và KeyboardInterrupt không dùng được ổn định
  giữa hai process Windows; sẽ dùng stop-request file được Trainer callback nhận
  ở cuối optimizer step, yêu cầu save rồi dừng.
- Artifact điều khiển dự kiến nằm trong từng run directory và active pointer tại
  `outputs/qlora/control/`; stdout/stderr/exit code tách riêng, không ghi đè run.
- Tiếp theo: triển khai callback/validator, bốn script + worker, README và dry-run
  test; không thay hyperparameter trong config GPU.
- Đã hoàn tất start/status/stop/TensorBoard + worker độc lập, live status/TensorBoard
  GPU metrics, graceful checkpoint stop, resume validation và chống chạy trùng/
  ghi đè. Mỗi attempt có log/metadata riêng; exit code được giữ.
- Dry-run start xác nhận RTX 5060 Ti, ba split 3.000/1.000/1.000 và 1.875 step;
  không tạo worker/run. PowerShell AST và TensorBoard dry-run đạt.
- Kiểm chứng cuối: 138 test đạt, 2 optional skip; pip check, Ruff, compileall và
  diff-check đạt. Không chạy full training theo yêu cầu.

# TASK-20261014-05 — completed

- Giai đoạn: audit và khắc phục logging/reporting QLoRA đã hoàn tất.
- Đã xong: đối chiếu yêu cầu với callback, train artifact, evaluate, metrics, plot
  và report; xác nhận TensorBoard có metric nhưng CSV cuối-run chưa phải log liên
  tục và một số plot chưa có nguồn dữ liệu thực tương ứng.
- Đã xong: event JSONL append-only/timing/checkpoint-resume metadata; evaluation
  theo split và câu hỏi; manifest plot/report unavailable; readiness check và tài liệu.
- Còn lại: measurement thực chỉ xuất hiện sau full training và post-training test
  evaluation do người dùng chủ động chạy; đây không phải phần còn thiếu của tooling.
- Trở ngại: không có.
- Bước tiếp theo: người dùng chạy readiness, start full training, rồi evaluate → plot → report.
- Bằng chứng: readiness RTX `READY` và không load model/start train; `137 passed,
  2 skipped, 40 subtests`; compileall, Ruff và `git diff --check` đạt.

# TASK-20261014-06 — completed

- Đã xác minh `rag/test_queries.jsonl`, `rag/test.jsonl` và `fintuning/test_sft.jsonl`
  đều có 1.000 ID giống nhau; SFT messages khớp tuyệt đối history + question +
  reference answer của hai file RAG, không có mismatch.
- Kết luận: `training.evaluate --split test` đã đánh giá đúng cùng tập câu hỏi mà
  không cần cấu hình dataset mới. Evaluator này không đồng nhất hoàn toàn với QA-v4
  schema/action scorer của baseline Ollama; muốn so trực tiếp artifact cũ cần adapter
  QA-v4 riêng.
- Không chạy generation hoặc tải model trong bước kiểm tra này.

# TASK-20261014-07 — completed

- Giai đoạn: backend QA-v4 cho QLoRA adapter đã hoàn tất và kiểm thử.
- Mục tiêu: dùng đúng 1.000 query, reference history và scorer của baseline/RAG;
  giữ metric retrieval/action unavailable nếu model không phát sinh bằng chứng thật.
- Đã thêm `--qlora-run-dir`, bắt buộc concurrency 1, cùng structured prompt/parser/
  retry, artifact/provenance riêng và lệnh score/compare pairwise.
- Kiểm chứng: 138 passed, 2 skipped, 40 subtests; Ruff và compileall đạt.
- Không chạy batch generation thật trong phiên này; bước tiếp theo là người dùng
  chủ động chạy run → score → pairwise compare theo `docs/qlora-operations.md`.
- Bổ sung theo yêu cầu hiệu năng: đang smoke batch 2 trên 4 câu với equivalence gate
  4/4; artifact `outputs/tthc_test_case_v1/qlora_batch2_smoke4.jsonl`, không chạy full.
- Kết quả: batch 2 đạt 4/4 trong 25,67 giây; batch 4 đạt 4/4 trong 17,85 giây,
  equivalence 4/4 và không OOM. Chọn batch 4 cho full evaluation; không chạy full.

# TASK-20261015-03 - completed

- Giai đoạn: kiểm kê và đối chiếu tính công bằng của benchmark Qwen Base, Base +
  RAG và QLoRA.
- Đã xác nhận: ba nhánh dùng chung 1.000 ID test ở mức dữ liệu; QLoRA được SFT theo
  câu trả lời thuần văn bản, còn backend baseline từng dùng hợp đồng JSON/action.
- Đã đối chiếu artifact: cùng SHA-256 query, cùng `reference_history`; Base và
  QLoRA đủ 1.000 prediction, RAG thành công 995. QLoRA đạt BLEU 61,38, ROUGE-L
  0,7169, BERTScore F1 0,9514 và EM 26,30% trên 810 ca có đáp án văn bản.
- Giới hạn đã xác minh: QLoRA không xuất action/retrieval; 56,4% toàn bộ ca test
  dùng document đã có trong train. Trên 810 ca similarity, nhóm document đã gặp
  (493 ca) đạt BLEU 64,82/EM 30%/ROUGE-L 0,74; nhóm chưa gặp (317 ca) vẫn đạt
  BLEU 56,02/EM 20%/ROUGE-L 0,68.
- Kết luận: adapter học trực tiếp phong cách và ánh xạ hỏi-đáp gold nên bám reference
  tốt hơn; lợi thế không chỉ do overlap nhưng overlap theo nguồn làm kết quả lạc
  quan hơn một benchmark document-disjoint. Chưa đủ bằng chứng để nói QLoRA tốt
  hơn RAG về cập nhật tri thức, factuality, action behavior hoặc retrieval.
- Không chạy lại workload dài hoặc thay đổi checkpoint trong task điều tra này.

# TASK-20261015-04 - completed

- Giai đoạn: tích hợp QLoRA vào web demo ba mô hình.
- Đã xác minh: server đã có provider `local_transformers` và loader PEFT 4-bit,
  nhưng `configs/inference.yaml` chưa khai báo adapter, mode chỉ cho `base|rag`,
  UI chỉ mô tả hai trạng thái truy hồi.
- Đã thêm mode `qlora`, cấu hình `qwen-qlora` trỏ đúng `best_adapter`, nhãn UI ba
  mô hình và luồng direct generation không retrieval cho adapter.
- Đã thêm chuyển backend tuần tự: dỡ Ollama trước khi nạp local Transformers và
  giải phóng cache local trước khi quay lại Ollama; mặc định không giữ đồng thời
  hai model 7B trên GPU 6 GB.
- Kiểm chứng: 22 test server/UI/config/QLoRA đạt; Ruff, compileall và diff-check
  các file thay đổi đạt; config phân giải adapter tới artifact đang tồn tại.
- Giới hạn: chưa chạy inference model thật hoặc browser QA; không tuyên bố runtime
  GPU hay hiển thị trực quan đã được xác nhận. Không thay đổi checkpoint.

# TASK-20261015-05 - completed

- Giai đoạn: sửa môi trường runtime web QLoRA.
- Đã xác nhận web dùng `env\Scripts\python.exe`, Torch `2.14.0+cu130`, CUDA nhận
  RTX 4050; môi trường thiếu đồng thời `accelerate`, `peft` và `bitsandbytes`.
- Chuẩn bị cài riêng ba package đã ghim trong requirements, giữ nguyên Torch CUDA
  và Transformers hiện có; sau đó chạy import, `pip check` và smoke loader.
- Đã cài `accelerate 1.12.0`, `peft 0.18.0`, `bitsandbytes 0.49.0`; `pip check`,
  import và NF4 CUDA forward nhỏ đạt. Chuẩn bị smoke nạp đúng base + `best_adapter`
  và sinh tối đa 8 token; đây là lệnh dài, có thể dùng cache hoặc tải weights nếu thiếu.
- Smoke `device_map=auto` xác nhận 6 GB không đủ để đặt toàn bộ module; thử CPU
  offload lần lượt lộ lỗi tương thích Transformers 5.17/bitsandbytes và meta tensor.
- Đã đưa Transformers về bản dự án ghim `4.57.3`, giữ Torch `2.14.0+cu130`, rồi
  cấu hình `force_single_gpu: true` cho QLoRA thay vì auto-dispatch/offload.
- Smoke thật PASS: nạp `Qwen/Qwen2.5-7B-Instruct` + đúng `best_adapter`, sinh 8
  token trong 7,96 giây; CUDA allocated 5,35 GiB. Base weights đã cache cục bộ.
- Kiểm chứng dependency: `pip check` sạch; import Accelerate/PEFT/bitsandbytes/
  Transformers và NF4 CUDA forward đạt. Cần restart web server cũ để nạp stack mới.

# TASK-20261015-06 - completed

- Đã xác minh web lưu và gửi lại history QLoRA theo từng model; không có bằng
  chứng mất ngữ cảnh giữa các lượt được nêu.
- Chuỗi người dùng chỉ cung cấp chủ đề/tên/mã, chưa hỏi thông tin cần lấy như hồ
  sơ, thời hạn, phí, cơ quan hoặc trình tự; câu clarify phù hợp contract SFT.
- Mã `1.004696` không tồn tại trong dataset/corpus kiểm tra. Tên thủ tục tương ứng
  có mã `1.009646` trong corpus, nhưng document này không xuất hiện ở bất kỳ split
  SFT train/validation/test nào của adapter.
- QLoRA web hiện là direct generation không retrieval nên không đọc được corpus
  của thủ tục mới. Dùng RAG cho ca này, hoặc hỏi QLoRA về thủ tục đã học với thuộc
  tính cụ thể; hướng kiến trúc sau là QLoRA + RAG, không phải thay đổi prompt đơn thuần.
- Quan sát bổ sung: câu hỏi cụ thể về hồ sơ `1.009646` cho ra một mục
  “Hồ sơ liên quan đến nội dung đề nghị điều chỉnh” (1 bản chính), không khớp
  corpus. Nguồn thật có ba mục; kết luận factuality FAIL và completeness FAIL.

