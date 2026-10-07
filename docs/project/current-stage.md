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
