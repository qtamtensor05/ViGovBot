# Lịch sử thay đổi hệ thống

## Preflight web và model tùy chọn - 2026-11-09

- **Mục tiêu:** Chặn web sớm khi thiếu runtime bắt buộc nhưng vẫn cho mở giao diện khi model sinh tùy chọn chưa sẵn sàng.
- **Thực hiện:** Thêm `vigov web-check`, tự chạy preflight trong `vigov web`; tách PASS/WARN/FAIL và bỏ dependency Compose từ web sang model-init, đưa QLoRA import vào profile `qlora`.
- **Kết quả:** Cấu hình CPU đạt preflight với cảnh báo Ollama; cấu hình CUDA native dừng đúng khi CUDA không khả dụng. Bốn unit test, Ruff và kiểm tra tài liệu đạt; chưa khởi động stack Docker thật.

## Bundle recovery tự chứa - 2026-11-09

- **Mục tiêu:** Đóng gói mỗi model thành một bundle có thể chuyển máy và tự sinh runtime.
- **Thực hiện:** Đưa logic, manifest và trọng số nguồn vào `recovery/phobert/` và `recovery/qlora_v2/`; runtime tiếp tục được sinh dưới `model/`.
- **Kết quả:** Phục hồi PhoBERT từ bundle mới đạt với sáu checksum trùng khớp, bản sao tạm đã được dọn. QLoRA v2 chưa chạy merge hoặc tạo GGUF.

## Gom công cụ recovery vào scripts - 2026-11-09

- **Mục tiêu:** Cho phép tìm và chạy toàn bộ logic phục hồi model trực tiếp từ `scripts/recovery/`.
- **Thực hiện:** Chuyển triển khai PhoBERT và QLoRA v2 khỏi package training; CLI tiếp tục giữ hợp đồng cũ nhưng điều phối tới script.
- **Kết quả:** Dry-run trực tiếp của cả hai model và ba unit test recovery PhoBERT đạt; không tải hoặc merge QLoRA.

## Phân cấp và phục hồi PhoBERT v3 - 2026-11-09

- **Mục tiêu:** Đóng gói checkpoint PhoBERT thành nguồn phục hồi độc lập và tách khỏi runtime cùng hồ sơ training.
- **Thực hiện:** Tạo các nhóm `recovery`, `runtime`, `training`; thêm manifest checksum và CLI phục hồi nguyên tử; chuyển toàn bộ cấu hình, Compose, script và tài liệu sang runtime path mới.
- **Kết quả:** Lệnh phục hồi đã sao chép và xác minh lại đủ sáu tệp, tổng 542.106.330 byte; ba kiểm thử recovery đạt. Live inference chưa chạy lại do môi trường host thiếu PyTorch/Transformers và Docker Desktop không hoạt động.

## Phân nhóm runtime, phục hồi và báo cáo QLoRA v2 - 2026-11-09

- **Mục tiêu:** Làm rõ artifact nào dùng để chạy, phục hồi và báo cáo QLoRA v2.
- **Thực hiện:** Đặt GGUF/Modelfile trong `runtime/`, bundle PEFT trong `recovery_adapter/`, đầu ra phục hồi trung gian trong `build/` và ảnh thực nghiệm trong `result/training-qlora_v2/plots/`.
- **Kết quả:** Thư mục model không còn ảnh hoặc GGUF rời ở cấp gốc; Compose và tài liệu đã trỏ sang `runtime/`. QLoRA v1 được giữ nguyên, chưa kiểm thử runtime sau thay đổi.

## Luồng phục hồi QLoRA v2 từ adapter rút gọn - 2026-11-09

- **Mục tiêu:** Tái tạo model QLoRA v2 phục vụ Ollama trên máy mới mà không cần chuyển bản GGUF đầy đủ.
- **Thực hiện:** Bổ sung manifest checksum và CLI tải Qwen nền, merge PEFT ở BF16, chuyển GGUF Q8_0, sinh Modelfile và import Ollama; bundle loại bỏ toàn bộ training state không cần cho inference.
- **Kết quả:** Source và tài liệu đã hoàn thiện, bundle local đạt 177.420.652 byte. Chưa chạy test hoặc job phục hồi thực tế theo yêu cầu; chưa có commit SHA model nền của lần training nên `main` chỉ dùng khi cho phép tường minh.

## Tách model runtime khỏi outputs - 2026-11-09

- **Mục tiêu:** Tách trọng số model dùng khi chạy khỏi cache, run và artifact sinh trong `outputs/`.
- **Thực hiện:** Chuyển QLoRA v2 và PhoBERT sang `model/`, ignore cây model; cập nhật mount Docker, cấu hình RAG, script và tài liệu sang đường dẫn mới.
- **Kết quả:** SHA256 PhoBERT và GGUF 8.098.525.120 byte đạt; `docker compose config --quiet`, sáu test liên quan và smoke PhoBERT live đạt. Chưa import/chạy lại QLoRA qua Ollama sau khi đổi bind mount.

## Chuẩn hóa đường dẫn artifact evaluation theo repository - 2026-11-09

- **Mục tiêu:** Cho phép sao chép kết quả training/evaluation giữa các máy mà không phụ thuộc đường dẫn tuyệt đối của máy tạo artifact.
- **Thực hiện:** Chuyển đường dẫn trong `result/` sang dạng tương đối POSIX; workflow mới serialize theo gốc repository và vẫn đọc manifest tuyệt đối lịch sử.
- **Kết quả:** Toàn bộ `result/` không còn `C:\Users`; 38 JSON, 4 JSONL và 28 test evaluation được kiểm chứng, Ruff, compileall và test tài liệu đạt.

## Khóa mã thủ tục qua menu chọn section - 2026-11-08

- **Mục tiêu:** Ngăn lượt chọn section làm mất mã thủ tục đã chọn và rơi sang semantic retrieval toàn corpus.
- **Thực hiện:** Đưa `code` vào pending request bất biến, phục hồi từ `selected` cho state v3 cũ và thêm chốt lọc context khác mã trước generation; bổ sung hồi quy hai menu liên tiếp.
- **Kết quả:** Chuỗi live chọn `1.000055` rồi mục `SUBMISSION_METHOD` dùng `procedure_direct`, chỉ nguồn `1.000055`; 179 test conversation/routing/server đạt và Web Docker healthy.

## Hợp nhất chuẩn hóa tiếng Việt bỏ dấu - 2026-11-06

- **Mục tiêu:** Ngăn matching lệch nhau do retrieval, routing, prompt, chunking và taxonomy tự triển khai các biến thể Unicode folding.
- **Thực hiện:** Tạo primitive `fold_vietnamese` trong `vigovbot.utils.text`; chuyển các caller sang dùng chung, tách rõ policy sửa “đăng kí”, co khoảng trắng, bỏ Markdown và token hóa ASCII.
- **Kết quả:** Các biến thể giữ nguyên hành vi có chủ đích bằng contract test; 171 test liên quan, Ruff, compileall và diff check đạt. Chưa kiểm chứng trên runtime web/model thật.

## Khóa section intent qua lựa chọn thủ tục - 2026-11-06

- **Mục tiêu:** Ngăn câu hỏi về một mục cụ thể bị biến thành truy vấn tổng quan sau khi người dùng chọn mã thủ tục từ menu.
- **Thực hiện:** Nâng signed state lên v3 với pending request bất biến; thực hiện transition lựa chọn không gọi lại router; thêm invariant fail-closed, trace state/filter, lọc cứng theo mã và section type, đồng thời tách `step_number` khỏi nhãn section.
- **Kết quả:** Luồng chọn thủ tục giữ nguyên câu hỏi “bước 1”, `PROCEDURE`, `procedure_step` và `step_number=1`; retrieval chỉ trả đúng mã/section trong hồi quy. 133 test conversation/routing/server, Ruff, compileall, test tài liệu và diff check đạt; chưa chạy model thật hoặc 97 case đánh giá.

## Tổng hợp đầy đủ fragment cùng mục trong QLoRA + RAG - 2026-11-04

- **Mục tiêu:** Khắc phục trường hợp retrieval đưa đủ nhiều chunk cùng mục vào prompt nhưng QLoRA chỉ trả nội dung chunk đầu và tự đánh giá `sufficient`.
- **Thực hiện:** Đánh dấu group, vị trí và tổng số fragment theo thứ tự corpus; bổ sung hậu kiểm độ bao phủ, một lần sinh sửa có fragment thiếu ở cuối prompt và fallback grounded chỉ nối đoạn nguồn mới chưa xuất hiện.
- **Kết quả:** Live `qwen-rag-qlora` cho thủ tục 6.006714 dùng `p1` và `p2`, trả đủ hạn 28/3, 15/4, nhánh phân cấp và xử lý sai quy định với `answer/sufficient`. 80 test RAG/server liên quan, compileall và diff check đạt; Web Docker healthy.

## Sửa lỗi hồi quy QLoRA + RAG từ prediction - 2026-11-04

- **Mục tiêu:** Khắc phục ba nhóm lỗi có thể xử lý ở runtime: mất section intent sau lựa chọn, output bị cắt do hết token và action/evidence không nhất quán.
- **Thực hiện:** Bổ sung nhận diện `bước N` tại routing và retrieval, phục hồi truy vấn section sau menu, siết schema citation và parser structured answer, đồng thời fail closed khi các lần sửa output vẫn kết thúc vì giới hạn token hoặc không đủ context.
- **Kết quả:** Thêm hồi quy trực tiếp cho luồng đăng ký kết hôn và hợp đồng missing-evidence; 115 test liên quan, Ruff và compileall đạt. Manifest 107 case đã sẵn sàng nhưng benchmark model thật chưa chạy.

## Giới hạn legacy retrieval cho kết quả và bảo toàn các hàng cách nộp - 2026-11-04

- **Mục tiêu:** Ngăn mục `RESULT` trên corpus legacy mở rộng thành toàn bộ thủ tục và ngăn QLoRA chỉ lặp tiêu đề bảng cách nộp.
- **Thực hiện:** Nhận diện chunk kết quả legacy bằng heading, áp dụng cho cả follow-up và conversation v2; bổ sung chỉ dẫn liệt kê đủ từng hình thức cùng các ô không rỗng.
- **Kết quả:** 89 test liên quan, compileall và diff check đạt. Live `qwen-rag-qlora` trả đủ Trực tuyến/Qua bưu điện/Trực tiếp với thời hạn, phí; mục kết quả chỉ dùng chunk `tthc_1_000894_sec_metadata_identity_11_p1`.

## Thiết lập môi trường Native Windows không dùng Docker và xác minh 4 model đánh giá trên GPU RTX 5060 Ti - 2026-11-03

- **Mục tiêu:** Cài đặt toàn bộ môi trường chạy cục bộ trên máy host Windows 10, tối ưu tối đa tài nguyên phần cứng (NVIDIA GeForce RTX 5060 Ti 16GB, Blackwell SM 12.0) không thông qua Docker; nạp bản merge QLoRA chuẩn (`qwen2.5-7b-qlora-q8_0.gguf`) và mô hình nền vào Ollama native; bảo đảm toàn bộ 4 mô hình (`qwen-base`, `qwen-rag`, `qwen-qlora`, `qwen-rag-qlora`) nạp đầy đủ (PhoBERT router, BGE-M3 CUDA, FAISS index, Ollama LLM) không bị fallback ngầm.
- **Thực hiện:**
  - Cài đặt Python 3.11.9 và Ollama 0.40.13 native trên Windows.
  - Thiết lập virtualenv `.venv-qlora`, cài đặt PyTorch 2.9.1+cu130 (hỗ trợ SM 12.0 cho RTX 5060 Ti), BitsAndBytes 0.49.0, Transformers 4.57.3, Sentence-Transformers 3.4.1, PyVi 0.1.1, FAISS, FastAPI, Uvicorn, BERTScore.
  - Chuẩn hóa cấu trúc thư mục checkpoint PhoBERT (`outputs/phobert_v3_finetuned_20261028/checkpoint`) và tập dữ liệu đối chuẩn (`Data/dataset_v3`).
  - Khởi tạo daemon Ollama native, nạp `qwen-qlora:latest` từ `outputs/qlora/qwen2.5-7b-qlora-q8_0.gguf` (8.1 GB, 100% GPU offload, ~7.9 GB VRAM) và tải bản base `qwen2.5:7b`.
  - Khởi động Web API server native cổng 8001; kiểm tra chẩn đoán GPU (`vigov gpu check`) đạt 100% PASS (NF4 forward/backward, Paged AdamW 8-bit, BF16).
  - Kiểm thử suy luận trực tiếp và qua API đối với toàn bộ 4 profile; xác nhận bộ định tuyến PhoBERT hoạt động chính xác (đích đến `rag_search`, nhãn mục nội dung đúng), `fallback_reason` là `None`.
  - Sửa điểm truyền `model_config_path` trong `vigovbot.evaluation.workflow` khi xuất điểm partial run; kiểm thử quy trình `vigov eva validate -> run -> score` trơn tru trên Golden benchmark v3.2.
- **Kết quả:** Hệ thống chạy hoàn toàn native trên máy host, không dùng Docker. 100% các thành phần mô hình (PhoBERT router, BGE-M3 trên CUDA, Ollama Q8_0 trên GPU) được nạp đầy đủ, tốc độ sinh đạt 50 tokens/s, độ trễ truy hồi ~115ms, không có hiện tượng fallback. Quy trình đánh giá sẵn sàng thực thi độc lập.

## Loại bỏ giới hạn cắt cứng câu trả lời RAG - 2026-11-03

- **Mục tiêu:** Không ép câu trả lời dừng tại 600/800 ký tự và không lược bỏ facts quan trọng trực tiếp trả lời câu hỏi.
- **Thực hiện:** Bỏ `maxLength` khỏi schema sửa lỗi; viết lại từ cùng evidence với chỉ dẫn giữ đủ bước, chủ thể, điều kiện, ngoại lệ, hồ sơ, số lượng, thời hạn, phí và kết quả liên quan; tăng ngân sách sửa tối đa 1.024 token và chặn output nếu vẫn hết token hoặc không đủ context để sửa.
- **Kết quả:** 70 kiểm thử đạt; Web/Ollama healthy và live QLoRA + RAG trả câu trả lời 1.032 ký tự hoàn chỉnh, `finish_reason: stop`, không phải JSON thô.

## Tóm tắt lại câu trả lời RAG khi vượt giới hạn sinh - 2026-11-02

- **Mục tiêu:** Ngăn câu trả lời hoặc JSON dang dở xuất hiện khi model RAG dùng hết ngân sách token.
- **Thực hiện:** Phát hiện `done_reason: length`, sinh lại từ cùng context bằng hợp đồng tóm tắt tối đa 800 ký tự, ngừng stream lần sửa và chặn kết quả nếu lần hai vẫn hết token.
- **Kết quả:** 69 kiểm thử routing/server/UI/config đạt; hai ca hồi quy mới phủ cả thành công và thất bại có kiểm soát. Web live healthy và câu hỏi quy trình đăng ký kết hôn trả văn bản hoàn chỉnh 992 ký tự, `finish_reason: stop`, không lộ JSON.

## Tích hợp QLoRA merge và QLoRA + RAG vào Web - 2026-11-02

- **Mục tiêu:** Cho phép hỏi đồng thời bốn cấu hình Base, Base + RAG, QLoRA merge và QLoRA merge + RAG trên Web mặc định.
- **Thực hiện:** Chuyển QLoRA sang backend Ollama dùng `qwen-qlora:latest`; bổ sung hai model vào cấu hình host/Docker, init idempotent từ GGUF trong Compose, hợp đồng cấu hình và kiểm thử API cho `mode: qlora` không retrieval.
- **Kết quả:** Web cổng 8001 healthy và `/api/models` trả đủ bốn model. Live API xác nhận `qwen-qlora` trả lời trực tiếp với `sources: []`, còn `qwen-rag-qlora` chạy nhánh RAG; model merge 8,09 GB được giữ trong volume Ollama cho các lần khởi động sau.

## Lọc PA1-clean và chấm lại bốn mô hình từ prediction hiện có - 2026-11-02

- **Mục tiêu:** Kiểm tra độ bền kết luận đánh giá sau khi loại bốn case có nguy cơ chồng lấn nội dung SFT khỏi PA1.
- **Thực hiện:** Xuất `Data/dataset_v3/test_rag/test_rag_pa1_clean.jsonl` gồm 634 case; lọc theo ID và tổng hợp lại metric `computed` từ `case-scores.jsonl` của Base, RAG, QLoRA và QLoRA+RAG, không train và không inference lại. Lưu manifest, case-score đã lọc, summary từng run và bảng so sánh tại `outputs/evaluation/pa1-clean-634`.
- **Kết quả:** Cả bốn run đủ 634 ID. QLoRA tiếp tục dẫn đầu các metric tương đồng sinh câu; QLoRA+RAG tiếp tục dẫn đầu key-fact coverage; RAG thuần nhỉnh hơn retrieval. Biến động metric sau lọc nhỏ và không làm đổi kết luận tổng thể.

## Khởi tạo bộ dữ liệu SFT ChatML từ dataset_v3/fintuning phục vụ huấn luyện QLoRA - 2026-11-02

- **Mục tiêu:** Chuyển đổi không mất mát (lossless) bộ dữ liệu đã được làm sạch và chia split chuẩn `dataset_v3/fintuning` sang cấu trúc SFT `messages` chuẩn để sẵn sàng nạp cho pipeline huấn luyện QLoRA Qwen2.5-7B-Instruct.
- **Thực hiện:**
  - Chạy `vigov data golden-to-sft --source-dir Data/dataset_v3 --output-dir Data/golden_dataset_sft`.
  - Kiểm tra và xác thực dữ liệu qua `vigov data check --config configs/training/experiments/golden_sft.yaml`.
- **Kết quả:**
  - Tạo thành công hai tệp `train_sft.jsonl` (1.931 bản ghi, 1.28 MB, SHA256: `7c2d3c72...`) và `validation_sft.jsonl` (827 bản ghi, 556 KB, SHA256: `526f58f1...`) tại `Data/golden_dataset_sft/`.
  - Phân phối tin nhắn: Train gồm 1.176 mẫu 2-turn và 755 mẫu 4-turn; Validation gồm 503 mẫu 2-turn và 324 mẫu 4-turn.
  - Kiểm tra rò rỉ (leakage check): 0 nhóm trùng lặp hội thoại, 0 câu hỏi trùng lặp giữa Train và Validation, bảo toàn 100% ID và Unicode tiếng Việt NFC. Lệnh `vigov data check` xác nhận `status: valid`.

## Xây dựng 2 bộ benchmark đánh giá RAG theo tỉ lệ - 2026-11-01

- **Mục tiêu:** Tạo hai bộ dữ liệu kiểm thử RAG chuẩn hóa từ ba file nguồn trong `Data/dataset_v3/test_rag`, ưu tiên hệ thống tỉ lệ tự nhiên và bảo đảm chất lượng hơn số lượng.
- **Thực hiện:** Khử trùng lặp ID `GOLDEN_V3_005568` trong `follow_v2` (giữ 158 mẫu mỏ neo); thêm `scripts/build_test_rag_benchmark.py` xuất 2 tập benchmark độc lập: Phương án 1 (638 mẫu cân bằng 6 tỉ lệ vàng, Đất đai ~23%, Section đều 16-24%, Single/Multi 50/50, 406 thủ tục) và Phương án 2 (917 mẫu bao phủ 100% toàn bộ 808 thủ tục với 1 câu hỏi tốt nhất/thủ tục, 66 ca bẫy unanswerable, Đất đai ~24,3%).
- **Kết quả:** Hoàn tất xuất `test_rag_pa1_ratio_balanced.jsonl` (638 dòng, 4,1 MB) và `test_rag_pa2_max_procedure_coverage.jsonl` (917 dòng, 5,4 MB). Toàn bộ 1.555 bản ghi đạt 100% `golden_dataset.schema.json`, 0 ID trùng lặp, 0 leakage với tập train/val fine-tuning và test router. Script kiểm tra Ruff sạch.

## Gom case Golden theo tên thủ tục trùng - 2026-10-30

- **Mục tiêu:** Đưa các case Golden đề cập tên thủ tục trùng vào đúng thư mục nhóm để rà soát định danh theo mã, cấp và địa phương.
- **Thực hiện:** Thêm `scripts/collect_duplicate_procedure_golden_cases.py` khớp tên chuẩn hóa trên câu hỏi, truy vấn độc lập và lịch sử hội thoại; chọn nhóm có tên dài nhất; ghi `golden_cases.jsonl` (nguyên dòng Golden), `golden_cases_summary.json` và `golden_cases_manifest.json`.
- **Kết quả:** Phân 794 case vào 46 nhóm, không trùng assignment; 539 case có mã ground truth thuộc nhóm, 255 case dùng mã ngoài nhóm cần rà soát và 3 case thiếu định danh nguồn. Test mới, test generator, Ruff, compileall và script kiểm chứng độc lập đều đạt; checksum, nội dung dòng Golden và summary khớp nguồn.

## Sửa Golden smoke trùng tên thủ tục - 2026-10-30

- **Mục tiêu:** Tách lỗi dữ liệu đánh giá khỏi lỗi PhoBERT routing và giữ nguyên nguyên tắc không tự chọn thủ tục trùng tên.
- **Thực hiện:** Bổ sung mã `1.115490` và tỉnh Thanh Hóa cho `GOLDEN_V3_006630`, đồng bộ Golden/SFT local, thêm candidate audit và hồi quy cho cả có/thiếu mã.
- **Kết quả:** Validator 7.100 case đạt và nêu 269 candidate cần rà soát; 52 test tập trung và full suite 402 test đều đạt (15 skipped). Smoke lần 3 chạy mới 10/10 prediction thành công, route accuracy tăng từ 90% lên 100%, action accuracy từ 70% lên 80%; hai lỗi action còn lại không phải lỗi routing.

## Hiển thị trạng thái đánh giá cho từng câu trả lời Web - 2026-10-30

- **Mục tiêu:** Không buộc người dùng suy đoán trạng thái runtime từ nội dung câu trả lời.
- **Thực hiện:** Truyền `evidence_status` qua `/api/chat` và `/api/chat/stream`; dùng một formatter trạng thái chung cho hai đường render Web.
- **Kết quả:** 114 test liên quan, Ruff, compile và `git diff --check` đạt; Web Docker healthy. `/api/chat` và `/api/chat/stream` thật cùng trả `abstain/missing/procedure_direct` cho ca tỷ lệ đúng hẹn thực tế. Chưa kiểm tra trực quan vì phiên Computer Use không có trình duyệt khả dụng.

## Từ chối theo bằng chứng truy xuất và bảo toàn Unicode - 2026-10-30

- **Mục tiêu:** Ngăn RAG dùng nội dung thủ tục chung để trả lời dữ liệu riêng nhưng vẫn cho phép trả lời khi nguồn thật sự chứa định danh đó.
- **Thực hiện:** Thay luật gán cứng `HS-*` bằng kiểm tra định danh riêng giữa câu hỏi và các chunk đã truy xuất; thiếu định danh trong evidence thì trả `identifier_not_in_evidence`, có định danh thì tiếp tục đánh giá/generation. Sửa chuỗi phản hồi sang UTF-8 đúng.
- **Kết quả:** 112 test liên quan, Ruff, compile và `git diff --check` đạt; đối chiếu 7.100 ca Golden cho kết quả 150/150 ca không trả lời và 0 dương tính giả. API local thật có retrieval `procedure_direct`, trả `abstain`, tiếng Việt đúng và không chứa ký tự thay thế.

## Bổ sung ca không có câu trả lời cho golden v3 - 2026-10-30

- **Mục tiêu:** Đánh giá khả năng không suy đoán dữ liệu vận hành của hồ sơ cá nhân khi PDF và metadata chỉ mô tả thủ tục chung.
- **Thực hiện:** Đọc 686 trang của 138 PDF, đối chiếu 138 metadata và thêm 150 ca thuộc 56 lĩnh vực; dùng năm nhóm tình huống, 30 mẫu diễn đạt, 30 follow-up và 120 câu hỏi mới.
- **Kết quả:** `Data/dataset_v3/golden_all.jsonl` tăng từ 6.950 lên 7.100 bản ghi. 150/150 ca mới là `is_unanswerable=true` và `expected_action=abstain`; toàn bộ dataset hợp lệ Draft 2020-12, 0 ID trùng, 0 bản ghi giống hoàn toàn, 0 lỗi liên kết nguồn và 0 ứng viên gần-trùng ở ngưỡng SequenceMatcher 0,90; 6 regression test schema đạt.

## Chuẩn hóa golden dataset v3 theo schema — 2026-10-30

- **Mục tiêu:** Gộp hai bộ golden lĩnh vực thành một file cuối và đưa toàn bộ bản ghi về đúng `schema/golden_dataset.schema.json`.
- **Thực hiện:** Gộp `linh_vuc` và `linh_vuc_thieu` thành 6.950 bản ghi, thống nhất ID `GOLDEN_V3_*`; tách `validation_audit` sang `golden_all.audit.jsonl`; map `easy` → `medium`, `test` → `in_domain`, chuẩn hóa `relevance_completeness`, `cutoffs`, `negative_rules`, `distractor_injection`, citation, `fact_evidence` và bổ sung 19 domain vào enum schema.
- **Kết quả:** `Data/dataset_v3/golden_all.jsonl` có 6.950 bản ghi, 283 domain, 0 lỗi schema, 0 ID trùng; backup `golden_all.pre-normalize.jsonl`, sidecar audit 3.797 bản ghi và báo cáo `golden_all.normalization-report.json` được giữ lại. 14 unit test schema/SFT đạt; hai thư mục nguồn không bị sửa.

## Đồng bộ hóa tài liệu kiến trúc RAG Contract v2 và kiểm chứng toàn diện — 2026-10-29

- **Mục tiêu:** Đồng bộ hóa toàn bộ tài liệu kiến trúc hệ thống (`architecture.md`), hướng dẫn routing bốn head (`four-head-routing.md`), và hướng dẫn vận hành pipeline RAG (`trien-khai-rag-co-ban.md`) theo đúng trạng thái mã nguồn và runtime hiện hành.
- **Thực hiện:** Cập nhật sơ đồ luồng Mermaid RAG v2, đặc tả PhoBERT 4-head, ranh giới HMAC signed state (256 phiên), cơ chế `direct_choice` (không chặn oan câu hỏi chứa số khi không có menu), nhánh phân rã Qwen extractive rewrite cho `MIXED_SCOPE` (<= 8 vế), cơ chế dự phòng `unresolved_semantic_hits` (trace `semantic`), bảng tham số cấu hình RAG v2 loại bỏ hoàn toàn FastText cũ, ghi chú thực nghiệm về độ trễ Reranker CPU (~12,28s).
- **Kết quả:** Bộ kiểm thử tự động 392/392 test pass (21 skipped cho external), toàn bộ tài liệu kiến trúc và hướng dẫn vận hành đồng bộ 100% với mã nguồn `src/vigovbot/rag/`.

## Semantic retrieval khi thiếu danh tính thủ tục — 2026-10-29

- **Mục tiêu:** Cho phép generation dùng evidence FAISS nếu không tìm được tên/mã thủ tục nhưng semantic search vẫn có kết quả.
- **Thực hiện:** Candidate semantic không gán mã được giữ làm evidence khi chưa nhận diện tên; trace phân biệt chiến lược `semantic` với `procedure_direct`.
- **Kết quả:** Toàn bộ 392 unit test tự động đạt (21 skipped).

## Fallback rewrite cho MIXED_SCOPE nhiều vế — 2026-10-29

- **Mục tiêu:** Cho phép LLM trích vế hành chính khi phân tách được câu nhưng PhoBERT không xác nhận vế nào.
- **Thực hiện:** Rewrite được phép khi không có vế hành chính độc lập nào được PhoBERT xác nhận, tối đa 8 vế; nhiều vế hành chính được xác nhận vẫn phải làm rõ.
- **Kết quả:** Toàn bộ 392 unit test tự động đạt (21 skipped).

## Điều hướng số thứ tự khi không có menu — 2026-10-29

- **Mục tiêu:** Không chặn câu hỏi mới chỉ vì câu có cụm “thủ tục 1” hoặc “mục 2”.
- **Thực hiện:** Văn bản số chỉ được xem là lựa chọn khi có menu; trạng thái được truyền nhưng không xác thực vẫn bị từ chối.
- **Kết quả:** Toàn bộ 392 unit test tự động đạt (21 skipped).

## Retrieval RAG sau khi gỡ reranker — 2026-10-29

- **Mục tiêu:** Trở về luồng truy xuất FAISS trực tiếp sau khi đo chi phí độ trễ của thử nghiệm reranker.
- **Thực hiện:** Khôi phục `top_k: 5`, gỡ cấu hình và module reranker online, dừng web trước khi xóa riêng cache `BAAI/bge-reranker-v2-m3`; giữ nguyên cache embedding, corpus và báo cáo benchmark.
- **Kết quả:** Reranker không còn tham gia runtime; web Docker healthy và `/api/health` trả HTTP 200 sau restart. Kết quả benchmark 10 câu vẫn được lưu tại `docs/reports/reranker-latency-20261029.md`.

## Tích hợp PhoBERT routing 4-head — 2026-10-29

- **Mục tiêu:** Thay phân loại LLM và ghi đè nhãn section bằng checkpoint PhoBERT fine-tuned.
- **Thực hiện:** Nạp local bốn head/PyVi/ngưỡng gốc, adapter corpus/state, cấu hình mặc định và mount read-only; lớp dependency Docker riêng.
- **Kết quả:** Web local đang chạy PhoBERT; identity công bố hash checkpoint. Full test suite đạt 392 tests pass, 21 skipped.

## Định danh bốn cấu hình và phạm vi metric v3.2 — 2026-10-28

- **Mục tiêu:** Chấm chung Base, fine-tuning, RAG và fine-tuning + RAG đúng khả năng.
- **Thực hiện:** architecture bắt buộc; Base/fine-tuning không có retrieval/context;
  điểm không áp dụng phải bỏ qua hoặc not_applicable. Fine-tuning có revision
  adapter/checkpoint. Bỏ actual_route và điểm phân loại ngoài phạm vi.
- **Kết quả:** 44 kiểm thử schema/tài liệu đạt. Ví dụ chuyển sang v3.2.
  Chỉ sửa schema, ví dụ, test và tài liệu; không sửa runtime hoặc JSONL cũ.

## Bổ sung dữ liệu chấm RAG/retrieval v3.1 — 2026-10-28

- **Mục tiêu:** Thiết kế prediction và golden theo đầu vào cần cho từng nhóm metric.
- **Thực hiện:** Bắt buộc trace query/sub-query, nội dung context/prompt, action,
  citation và latency khi success; measurement provider có trạng thái/lý do.
  Golden thêm evaluation_plan và liên kết bằng chứng/cặp thử nhiễu.
- **Kết quả:** 36 kiểm thử schema/tài liệu đạt. Hai ví dụ multi-intent hợp lệ.
  Giữ nguyên source runtime và JSONL cũ; JSONL cũ cần bổ sung evaluation_plan
  trước khi dùng với hợp đồng mới. Chưa chạy inference hoặc judge.

## Gom schema độc lập — 2026-10-28

- **Mục tiêu:** Mở một file là đọc được toàn bộ hợp đồng dữ liệu.
- **Thực hiện:** Gom về golden, prediction, evaluation; bỏ ba schema tham chiếu
  ngoài, giữ hai ví dụ JSON; thêm kiểm thử đồng bộ định nghĩa được nhúng.
- **Kết quả:** 28 kiểm thử schema/tài liệu đạt. Không sửa runtime hoặc dữ liệu cũ.

## Chuẩn hóa schema RAG/retrieval v3 — 2026-10-28

- **Mục tiêu:** Thống nhất hợp đồng mới, bỏ tương thích schema đầu ra cũ.
- **Thực hiện:** Dùng chung envelope prediction/case-score và golden qua $ref;
  relevance nhị phân, metric có trạng thái, hỗ trợ retrieval-only và no-answer.
  Theo phạm vi người dùng chốt: chỉ schema, kiểm thử và tài liệu; runtime giữ nguyên.
- **Kết quả:** 25 kiểm thử schema/tài liệu đạt, 3.850 mẫu golden hợp lệ.
  Ví dụ JSON là fixture tổng hợp. Collector/scorer chưa hỗ trợ v3; kiểm tra
  liên kết ID/hash/rank xuyên trường cần validator ngữ nghĩa khi triển khai runtime.

## Siết schema evaluation — 2026-10-28

- **Mục tiêu:** Sửa ràng buộc evaluation, giữ nguyên dữ liệu và artifact JSON/JSONL.
- **Thực hiện:** Đồng bộ golden nhúng, cho phép metric tùy chọn và mở rộng,
  ràng buộc trạng thái thực thi với actual_output/partial_output. Giữ bộ xuất hiện tại.
- **Kết quả:** 15 kiểm thử schema đạt; đầu ra evaluator thông thường vẫn hợp lệ.
  Artifact cũ vi phạm ràng buộc mới bị từ chối, không được tự sửa.

## Tách image web CPU và QLoRA GPU - 2026-10-27

### Mục tiêu

Giảm dung lượng web thường ngày và chỉ mang CUDA khi chạy QLoRA cục bộ.

### Thực hiện

- Tách Docker target `web-ollama` dùng Torch CPU và `web-gpu` dùng CUDA.
- Tách config Base/RAG mặc định và service QLoRA thuộc profile `gpu`.
- Sinh lock CPU bằng resolver; giữ nguyên volume Ollama, Hugging Face và RAG.

### Kết quả

Image mặc định giảm 12,8 GB xuống 2,03 GB; Base/RAG streaming trả
`success`. Image GPU 12,8 GB xác nhận RTX 4050, CUDA 12.8, PEFT và
bitsandbytes. Đã thu hồi 32,01 GB BuildKit cache. 249 test, Ruff, compileall,
Compose default/GPU và `git diff --check` đạt; 22 test tùy chọn bị skip.

## Streaming phản hồi LLM trên web - 2026-10-27

### Mục tiêu

Giảm cảm giác chờ bằng cách hiển thị phản hồi ngay trong quá trình model sinh.

### Thực hiện

- Bổ sung callback token cho Ollama, OpenAI-compatible và Transformers cục bộ.
- Thêm `/api/chat/stream` dạng NDJSON và cập nhật từng thẻ model trên web.
- Giữ `/api/chat` và payload kết quả cuối cùng tương thích ngược.

### Kết quả

249 test, Ruff, compileall và `git diff --check` đạt; 22 test dependency tùy chọn
bị skip. Image web đã build, container healthy; API `qwen-base` thật phát 4 sự
kiện token, TTFT warm 0,300 giây và hoàn tất sau 0,486 giây. Chưa thao tác
xác minh trên trình duyệt thật.

## Intent classifier FastText/hybrid - 2026-10-27

### Mục tiêu

Giảm chi phí prompt routing bằng classifier CPU nhưng bảo toàn hợp đồng routing
nhiều lượt và khả năng rollback về Qwen.

### Thực hiện

- Thêm backend `llm|fasttext|hybrid`, confidence threshold, diagnostics và
  fallback an toàn khi artifact thiếu/sai hash hoặc cần rewrite/clarification.
- Thêm CLI train/evaluate, schema dataset chống group leakage, cấu hình FastText
  gọn có kiểm tra kích thước trên fixture, Docker builder stage và hướng dẫn.

### Kết quả

Docker build thành công; 62 test router/server/CLI, 5 test tài liệu/cấu hình,
Ruff, compileall và diff check đều đạt. Full suite chạy 269 test còn 7 lỗi nền
không thuộc thay đổi này và 7 skip. Chưa huấn luyện artifact thật trên dữ liệu
độc lập, chưa đạt quality gate và chưa đo API latency, nên giữ mặc định `llm`.

## Đưa trực tiếp top 5 retrieval vào LLM - 2026-10-26

### Mục tiêu

Loại chi phí và tác động xếp hạng của reranker khỏi luồng RAG online để thử
nghiệm trực tiếp năm kết quả FAISS đầu tiên trong prompt LLM.

### Thực hiện

- Đổi hai profile host/Docker sang `retrieval.top_k: 5` và bỏ cấu hình reranker.
- Bỏ module reranker online; pipeline truy hồi trực tiếp top 5 cho cả truy vấn
  đơn và hợp nhất sub-query.
- Đồng bộ trace cấu hình, panel nguồn, hướng dẫn vận hành và kiểm thử regression.
- Giữ công cụ rerank artifact ngoại tuyến trong evaluation, không tham gia luồng
  trả lời chatbot.

### Kết quả

36 test routing, 9 test server, 1 test UI, toàn bộ 235 test, schema hai profile,
Ruff, compileall và `git diff --check` đạt; 21 test dependency tùy chọn bị skip.
Chưa xác minh API/container hoặc chất lượng câu trả lời thực vì Docker daemon
không hoạt động và host thiếu FAISS/model runtime.

## Rút gọn evidence có cấu trúc vượt ngân sách - 2026-10-25

### Mục tiêu

Tránh `abstain` giả khi các hit đầu là bảng hoặc JSON có bằng chứng nhưng vượt
`max_chunk_tokens`.

### Thực hiện

- Chiếu bảng Markdown/HTML theo hàng hoàn chỉnh và JSON theo field/phần tử.
- Giữ nguyên scalar và giá trị ô; chỉ dùng projection có dữ liệu và còn vừa cả
  giới hạn chunk lẫn tổng prompt.
- Cập nhật test hồi quy và hợp đồng module prompt.

### Kết quả

11 test evidence chuyên biệt, full suite 238 test, Ruff, compileall và
`git diff --check` đạt; 21 test dependency tùy chọn bị skip. Chưa xác minh bằng
tokenizer Qwen thật hoặc API generation do thiếu Transformers/FAISS.

## Tách ngân sách context cho routing - 2026-10-25

### Mục tiêu

Giảm context và giới hạn đầu ra của routing mà không thu hẹp ngân sách sinh câu
trả lời.

### Thực hiện

- Thêm `routing_num_ctx=4096` và `routing_num_predict=128` vào schema và hai
  profile RAG.
- Áp dụng ngân sách riêng cho request, kiểm tra prompt và routing retry.
- Giữ `num_ctx=8192` và `num_predict=512` cho generation.

### Kết quả

36 test routing, full suite 234 test và Ruff đạt. Chưa đo latency A/B vì không có
Ollama hoặc Docker runtime hoạt động.

## Chuẩn hóa cấu trúc repository và CLI - 2026-10-15 đến 2026-10-18

### Mục tiêu

Loại bỏ package song song và thống nhất đường dẫn sử dụng công khai.

### Thực hiện

- Chuyển source về `src/vigovbot/`.
- Hợp nhất training tại `src/vigovbot/training/` và evaluation tại
  `src/vigovbot/evaluation/`.
- Thống nhất CLI `vigov`, cấu hình theo miền và tài liệu theo nhóm trong `docs/`.

### Kết quả

Cấu trúc canonical, package discovery, CLI và kiểm tra tài liệu đã hoạt động trên
checkout sạch; wrapper và cây package cũ không còn là điểm triển khai chính.

## QLoRA local-first và tích hợp Web - 2026-10-14 đến 2026-10-16

### Mục tiêu

Huấn luyện, đánh giá và chạy QLoRA trên GPU mà không thay thế Base/RAG.

### Thực hiện

- Hoàn thiện masking assistant-only, resume gate, profile GPU và cấu hình adapter.
- Tích hợp lựa chọn `base`, `rag`, `qlora` vào Web với lịch sử tách biệt.
- Dùng checkpoint validation tốt nhất `checkpoint-1100` cho adapter hiện tại.

### Kết quả

QLoRA chạy cục bộ trên RTX 4050 với Transformers 4.57.3; Base/RAG vẫn được giữ
và QLoRA-only không được xem là nguồn căn cứ cho thủ tục chưa có trong SFT.

## Docker runtime và cache bền vững - 2026-10-16 đến 2026-10-25

### Mục tiêu

Vận hành Web/Ollama trên Docker GPU mà không tải lại dependency và model sau mỗi
chỉnh sửa source.

### Thực hiện

- Tách lớp dependency CUDA khỏi source thay đổi thường xuyên.
- Dùng volume cho Hugging Face, Ollama và RAG; bind mount source/config cần thiết.
- Bổ sung healthcheck, preflight và lệnh `vigov doctor`.

### Kết quả

Stack Docker CUDA đã healthy; Qwen2.5:7B và RAG cache được tái sử dụng;
`/api/chat` và CLI trả kết quả có nguồn từ corpus. Thay đổi source/config thông
thường chỉ cần khởi động lại Web.

## Evaluation v2 và Golden datasets - 2026-10-17 đến 2026-10-24

### Mục tiêu

Tách inference khỏi scoring và giữ provenance cho mọi kết quả đánh giá.

### Thực hiện

- Tách prediction, offline scoring, judge và export thành các bước có thể resume.
- Bổ sung fingerprint, schema kết quả, trace retrieval/generation và trạng thái
  metric chưa có.
- Chuyển Golden sang SFT train/validation, giữ Unicode, ID và chống leakage.

### Kết quả

Evaluation v2 hỗ trợ resume từ prediction cache và không giả lập metric thiếu;
Golden SFT có 2.200 mẫu train, 550 mẫu validation, không trùng ID/conversation.

## Cứng hóa RAG và retrieval - 2026-10-23 đến 2026-10-25

### Mục tiêu

Trả đúng thủ tục, đúng loại thông tin và giữ câu trả lời có căn cứ.

### Thực hiện

- Thêm exact lookup theo mã và tên thủ tục.
- Ưu tiên section theo ý định, rerank Top-20 xuống Top-3 bằng MiniLM.
- Thêm format policy theo loại câu hỏi và fallback an toàn cho output phụ lỗi.

### Kết quả

Truy vấn mã `1.116222` trả đúng số quyết định; bộ 18 câu theo tên thủ tục đạt
top-1 và top-3 đúng 18/18; API container đã xác nhận luồng retrieval-rerank.

## Chuẩn hóa hồ sơ vận hành - 2026-10-25

### Mục tiêu

Chỉ lưu thay đổi quan trọng liên quan hệ thống hoặc vận hành.

### Thực hiện

- Đổi quy định kích hoạt skill nhật ký.
- Hợp nhất yêu cầu, lịch sử, trạng thái và sự cố cũ theo mốc hệ thống.
- Loại nội dung báo cáo, dọn dẹp, kiểm tra và chỉnh sửa nhỏ.

### Kết quả

Hồ sơ dùng thống nhất ba phần `Mục tiêu - Thực hiện - Kết quả` và không còn cập
nhật theo mọi task nhiều bước.


## 2026-10-27 — Follow-up truy xuất trực tiếp theo mã thủ tục

### Mục tiêu

Giảm thời gian truy xuất cho câu nối tiếp đã xác định thủ tục, giữ đúng nguồn.

### Thực hiện

Thêm lookup SQLite theo mã/phần, kiểm tra fingerprint corpus/chunk/lịch sử,
fallback trong đúng thủ tục khi thiếu phần hoặc vượt top_k. API/UI giữ ngữ cảnh
riêng theo model và xóa cùng hội thoại; trace phân biệt chiến lược truy xuất.

### Kết quả

Bộ Python mở rộng 128 test PASS; nhóm kiểm tra cuối bao gồm hai ca bảo vệ bổ sung.
Hai test JavaScript, Ruff, compileall và diff check PASS. Đo hai câu follow-up
trên corpus/model cục bộ: đúng mã và phần dữ liệu; retrieval warm giảm
1,182 → 0,067 s, cold tăng 1,170 → 1,456 s do nạp danh mục. Routing dao động,
chưa chứng minh giảm đều tổng latency. Chi tiết ở
`outputs/verification/follow-up/report.md`. Chưa restart web hoặc kiểm tra browser thật.


## 2026-10-27 — Hỏi lại thủ tục và section từ metadata

- **Mục tiêu:** Không tự trả lời một phần hoặc tự chọn thủ tục khi câu hỏi chưa rõ mục tiêu/đối tượng.
- **Thực hiện:** Thêm danh mục SQLite và bước hỏi lại trong RAG; ưu tiên mã/tên, hiển thị tối đa năm thủ tục và các section có thật. Giữ mục tiêu qua lựa chọn nhiều lượt, hỗ trợ context có chữ ký theo lịch sử/model và client cũ qua lịch sử; tích hợp API thường/streaming và reset UI. Giữ nguyên các chỉnh sửa follow-up đã có, không sửa corpus/model.
- **Kết quả:** 123 test Python routing/retrieval/API/prompt và 2 test JavaScript đạt; Ruff và compileall đạt. HTTP thường → streaming kiểm tra bằng model giả lập. SQLite thực tế có 6.192 thủ tục; mã tạm trú 1.004194 có sáu section. Chưa restart backend, chưa xác minh bằng model hoặc trình duyệt thật.


## 2026-10-27 — Sửa mất thủ tục khi chọn dòng và hỏi nối tiếp

- **Mục tiêu:** Giữ thủ tục đã xác định khi người dùng sao chép “4. Cách thức nộp, thời hạn và phí”, rồi hỏi “Hồ sơ, giấy tờ của thủ tục”.
- **Thực hiện:** Parser đối chiếu số kèm nhãn (kể cả dấu chấm escape Markdown), không nhầm mã thủ tục với số mục; phục hồi danh sách qua tối đa ba lượt lỗi không tìm thấy của parser cũ và không vượt qua câu đổi chủ đề. Pipeline xác minh fingerprint câu trả lời, corpus và chunk trước khi dùng lại mã cho câu hỏi phần nội dung, kể cả router chọn new_question. Giữ các ràng buộc context và phân loại ngoài phạm vi.
- **Kết quả:** 103 test Python liên quan, 2 test JavaScript, Ruff và compileall đạt. Restart web và /api/health trả ok. Qwen thật qua /api/chat → /api/chat/stream: danh sách kết hôn 1.000894 (1,37 giây), chọn dòng phí trả answer với cùng mã (15,77 giây), hỏi hồ sơ trả answer/required_documents bằng procedure_direct cùng mã (29,93 giây). Đây là kiểm chứng liên tục ngữ cảnh/truy hồi, không phải đánh giá đầy đủ tính đúng của nội dung pháp lý; chưa thao tác trình duyệt thật.


## 2026-10-27 — Sửa chọn nguyên dòng thủ tục có metadata

- **Mục tiêu:** Chọn được nguyên dòng thủ tục gồm tên, mã và cấp thực hiện thay vì lặp danh sách.
- **Thực hiện:** Dùng chung nhãn corpus cho render và parser; nhận tên, tên kèm mã, nguyên dòng có metadata với số thứ tự thường/escape Markdown. Kiểm tra số, mã, nhãn khớp; metadata mô tả không bị biến thành mục tiêu hỏi, giữ mục tiêu đã có.
- **Kết quả:** 105 test Python liên quan, 2 test JavaScript, Ruff/compileall đạt. Backend đã restart và health ok. API thật với câu “Thủ tục cấp lại chứng chỉ kiểm địng viên” trả đúng năm ứng viên; sao chép mục 5 chọn 1.000180 (0,56 giây), mục 1 chọn 2.000037 (0,41 giây), đều chuyển section_required với 0 lần gọi router. Chưa thao tác trình duyệt thật.


## 2026-10-27 — Hỏi danh sách không tự chọn tên khớp chính xác

- **Mục tiêu:** Nhận biết “Các thủ tục cấp lại chứng chỉ kiểm định viên” là yêu cầu chọn trong nhóm thủ tục, không tự chốt mã 2.000066.
- **Thực hiện:** Nhận diện yêu cầu danh sách/số nhiều; mở rộng tên khớp sang các biến thể dài hơn có cùng cụm tên trong catalog. Ưu tiên mã cụ thể khi được nêu, giữ tên đơn/ý hỏi rõ; không biến từ “tất cả các thủ tục” thành mục tiêu tổng quan sau khi chọn.
- **Kết quả:** 106 test Python liên quan và 2 test JavaScript đạt; Ruff/compileall đạt. Backend đã restart, health ok. API thật trả procedure_required với năm mã 2.000066, 1.000187, 1.000180, 1.000183, 2.000037 và more=true (3,23 giây); sao chép mục 2 chuyển section_required đúng mã 1.000187 (0,51 giây). Chưa thao tác trình duyệt thật.


## 2026-10-27 — Streaming early exit cho LLM router

- **Mục tiêu:** Trả sớm nhánh ngoài phạm vi/làm rõ trên API streaming.
- **Thực hiện:** Đọc prefix scope/relation qua nhiều chunk, dừng sinh router khi nhãn kết thúc được xác định; đóng HTTP stream hoặc dừng/join worker Transformers. Giữ đối chiếu metadata trước câu làm rõ, dùng câu hỏi mặc định khi bỏ phần clarification của JSON. Gửi token kết quả trước model_result; API thường vẫn chờ JSON đầy đủ.
- **Kết quả:** 90 test routing/provider/server/clarification/documentation đạt; Ruff và compileall đạt. Test provider giả lập xác nhận không đọc phần đuôi JSON và đóng kết nối. Chưa kiểm chứng model thật hoặc hủy sinh trên GPU; Docker daemon chưa chạy.


## 2026-10-27 — Routing v2 bốn nhóm nhãn

- **Mục tiêu:** Áp dụng luồng chọn menu trực tiếp và router base thay thế được, hỗ trợ nhiều thủ tục/section.
- **Thực hiện:** Tách classifier và điều phối, schema/retry v2, trạng thái có chữ ký, menu có nút, truy hồi giới hạn mã/section; giữ v1 cho FastText. Sau smoke model thật, khóa section được nêu rõ, thay query khi chọn menu, ưu tiên catalog cho yêu cầu danh sách và xử lý từ chối/xác nhận/biến thể bằng trạng thái.
- **Kết quả:** 303 ca đạt, 22 ca bỏ qua trong 325 test; Ruff, compileall và diff check đạt. API Qwen thật xác nhận Thông tin chung, phí và trình tự của mã 1.000894 dùng đúng nguồn; trạng thái chứng chỉ không tự chọn; “thuê đất” là IN_SCOPE và “thành lập trường” chỉ trả thủ tục giáo dục. Artifact tại `outputs/verification/reported-*-regression.json` và `catalog-discovery-live.json`. Chưa thao tác trình duyệt thật do không có browser kết nối; không thay đổi golden, checkpoint hoặc chỉ mục.
## 2026-10-28 - Schema Golden Dataset và Evaluation v2 độc lập

- **Mục tiêu:** Chuẩn hóa hợp đồng máy đọc được cho dữ liệu Golden và kết quả evaluation hiện hành.
- **Thực hiện:** Tạo schema Draft 2020-12 trong `schema/`; mô tả đầy đủ trường lồng nhau của Golden và toàn bộ cấu trúc Evaluation v2, không dùng tham chiếu tới file ngoài.
- **Kết quả:** Validate thành công 3.850 case train/val/test và evaluation record do `src/vigovbot/evaluation/records.py` tạo; `git diff --check` đạt.


## 2026-10-29 — Giữ mã thủ tục khi không cần menu

- **Mục tiêu:** Không loại bỏ bằng chứng đúng khi tên router thiếu tiền tố Thủ tục.
- **Thực hiện:** Xác định mã từ câu hỏi/tên độc lập với inspect menu; ưu tiên câu hỏi đơn thủ tục có tên xác nhận trong corpus, hỗ trợ tiền tố và pháp lí; giữ menu cho tên trùng. Bổ sung hồi quy và restart web dùng bind mount.
- **Kết quả:** 125 kiểm thử liên quan, Ruff và compileall đạt. Web local đã nạp bản sửa; hai câu nguyên văn qua API streaming lấy đúng mã 1.000894: phí 1 đoạn, pháp lý 4 đoạn trong lượt hỏi tiếp. Chưa kiểm tra trực quan trình duyệt hoặc độ đầy đủ của câu trả lời sinh; chưa tái hiện trạng thái gây chọn nhầm 1.010998 ban đầu.

## 2026-10-29 — PhoBERT bốn head thay router mặc định

- **Mục tiêu:** Dùng checkpoint routing đã huấn luyện cho phạm vi, mạch hội thoại, trộn thủ tục và mục nội dung.
- **Thực hiện:** Thêm inference local giữ nguyên PyVi, ba segment, 128 token, CLS pooling và ngưỡng metadata; adapter corpus/state không gọi Qwen hoặc từ khóa section; cấu hình mặc định, dependency Docker và mount checkpoint read-only; trace/identity có xác suất, ngưỡng và hash.
- **Kết quả:** 35 checksum đạt; parity token/xác suất đạt 7/7. Image web build/recreate thành công; API thật dùng backend PhoBERT và trả đúng nguồn 1.000894 cho phí/pháp lý, ngoài phạm vi không retrieval. Catalog sửa false OUT_OF_SCOPE cho tên thủ tục mà không thêm section; menu văn bản và lựa chọn số hoạt động, lựa chọn không chạy classifier. Runtime/routing trong image đạt 146 test (2 skipped), 7 test cấu hình đạt; full host đạt 383 test (22 skipped). Một câu nhiều thủ tục bị head mix dự đoán sai, nên adapter hỏi/chọn thủ tục bảo thủ và chưa có khẳng định chất lượng tổng thể.

## 2026-10-29 — Retrieval khi PhoBERT không vượt ngưỡng section

- **Mục tiêu:** Trả lời câu hỏi có mục tiêu cụ thể thay vì mở menu khi đã xác định chính xác thủ tục nhưng mọi xác suất section dưới ngưỡng.
- **Thực hiện:** Giữ `sections=[]`, tìm toàn bộ section của đúng mã cho câu hỏi có nội dung; chỉ giữ menu khi đầu vào là tên hoặc mã thủ tục trần. Không thêm từ khóa section hoặc sửa checkpoint.
- **Kết quả:** 52 test routing đạt; Ruff, compileall và diff check đạt. Container web healthy. API thật trả đúng đối tượng “Tổ chức (không bao gồm doanh nghiệp, HTX)” từ mã 3.000622 và có chunk `tthc_3_000622_sec_metadata_identity_1_p1`.

## 2026-10-29 — Đồng bộ taxonomy chunk với PhoBERT

- **Mục tiêu:** Loại bỏ lệch pha giữa các nhãn phí, thời hạn, cách nộp, kết quả và section tổng hợp của corpus.
- **Thực hiện:** Chiếu bảng cách thức thực hiện thành ba section giữ hình thức nộp làm khóa; nhận diện kết quả xử lý thành `result`; ánh xạ routing 1-1 và thêm cầu đọc corpus legacy chỉ khi section mới không có hit.
- **Kết quả:** 388 test đạt, 22 skipped. Dữ liệu thật 3.000622 tạo đủ bốn nhóm mới, từ 12 thành 14 chunk và giữ đúng phí/thời hạn/cách nộp/kết quả. Chưa rebuild hoặc công bố corpus FAISS mới.

## 2026-10-29 — Arbitration phạm vi theo confidence

- **Mục tiêu:** Không ghi đè mù `OUT_OF_SCOPE` chỉ vì câu chứa mã hoặc tên thủ tục trong catalog.
- **Thực hiện:** Chỉ override trong band `0,50 ≤ P(OUT) < 0,85`; giữ ngoài phạm vi ở ngưỡng cao hoặc ngoài band. Trace ghi object gồm xác suất, band và outcome.
- **Kết quả:** 80 test routing tập trung đạt; Ruff, compileall và diff check đạt. Đã có hồi quy tại biên `0,85`; chưa benchmark confusion matrix để hiệu chỉnh ngưỡng.

## 2026-10-29 — Hybrid confirmation cho thực thể thủ tục

- **Mục tiêu:** Hỗ trợ cụm tìm kiếm phổ thông mà không cho semantic candidate tự retrieval.
- **Thực hiện:** Thêm curated alias; catalog BM25 + exact cosine dùng encoder/index hiện có; phạt qualifier thiếu; gate độ dài, score và margin; menu xác nhận có state riêng, chọn mới vào scope và phủ nhận giữ ngoài phạm vi.
- **Kết quả:** 394 test đạt, 22 skipped. API thật: “đổi bằng lái xe máy” dùng alias tới 1.115978, mở menu section, 0 nguồn và generation 0; “làm hộ chiếu” không mở confirmation vì margin 0,009926 < 0,08. Ngưỡng chưa được calibration trên benchmark nhãn thật.

## 2026-10-29 — Fallback LLM chọn lọc cho MIXED_SCOPE

- **Mục tiêu:** Tách một yêu cầu hành chính khỏi phần ngoài lề dùng liên từ tự nhiên khi split xác định không thành công.
- **Thực hiện:** Chỉ gọi Qwen khi PhoBERT `MIXED_SCOPE` và regex không tách được phần hỗ trợ; nhiều phần hỗ trợ hoặc một phần dự đoán nhiều thủ tục vẫn hỏi lại. Yêu cầu đoạn trích liên tiếp có giới hạn 128 token, giữ mã/qualifier, rồi xác nhận lại bằng PhoBERT. Lỗi/đầu ra rỗng/ngoài phạm vi đều hỏi lại; scope `MIXED_SCOPE` vẫn được giữ để ghi chú phần bỏ qua.
- **Kết quả:** 401 test đạt, 22 skipped; 73 test routing liên quan, Ruff, compileall và diff check đạt. API thật trích “Phí đăng ký kết hôn” từ câu mixed, PhoBERT xác nhận `IN_SCOPE`, RAG lấy một nguồn mã 1.000894 và phản hồi `partial`. Chưa đo tỷ lệ mixed traffic 3–7% hoặc hiệu năng tổng thể.

## Tích hợp BGE cross-encoder reranker - 2026-10-29

### Mục tiêu

Lấy tối đa 10 ứng viên retrieval, chấm lại bằng `BAAI/bge-reranker-v2-m3` và đưa ba đoạn đầu vào model trả lời.

### Thực hiện

- Thêm module reranker Transformers dùng CPU mặc định, batch inference, cache singleton và fallback theo thứ tự FAISS khi model lỗi. Ghim revision `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`.
- Tích hợp vào pipeline RAG cũ và PhoBERT v2; giữ FAISS score/rank, ghi `reranker_score`, `rerank_rank`, trạng thái, model và thời gian vào kết quả/trace. Đặt `candidate_top_k: 10`, `top_k: 3` trong ba profile.
- Thêm hướng dẫn vận hành và cập nhật test cấu hình. Dùng volume Hugging Face hiện có; không thêm dependency hoặc rebuild image.

### Kết quả

Snapshot tải đủ vào volume. Smoke model thật chấm 10 cặp và trả ba kết quả hạng 1-3; API RAG trả `success`, reranker `ok` và web Docker healthy/HTTP 200. 40 test tập trung gồm routing, cấu hình và link tài liệu đạt; cú pháp nguồn và `git diff --check` đạt. Lượt kiểm tra rộng hơn có một test cũ đòi hai QLoRA adapter trong khi profile hiện có một; không liên quan thay đổi reranker. Chưa chạy benchmark chất lượng trên Golden/relevance nên chưa kết luận reranker cải thiện retrieval.

## Gỡ BGE reranker khỏi runtime - 2026-10-29

- **Mục tiêu:** Bỏ chi phí inference BGE reranker khỏi luồng RAG trực tuyến sau benchmark CPU.
- **Thực hiện:** Khôi phục ba profile RAG và hai pipeline về FAISS top 5; bỏ cấu hình/module online và telemetry API; xóa riêng model BGE reranker khỏi volume Hugging Face, giữ cache embedding và cache RAG.
- **Kết quả:** Web Docker healthy, `/api/health` trả HTTP 200; model reranker vắng khỏi cache, BGE-M3 embedding còn nguyên. Báo cáo và JSON benchmark vẫn được giữ.

## Không chặn câu hỏi có số khi không có menu - 2026-10-29

- **Mục tiêu:** Đưa câu mới như “thủ tục 1” và “mục 2” qua router nếu không có menu đang chờ lựa chọn.
- **Thực hiện:** Bỏ suy diễn lựa chọn hết hạn chỉ từ số trong văn bản; tiếp tục từ chối selection có cấu trúc khi không có menu và số đi cùng conversation state không xác thực.
- **Kết quả:** AST và `git diff --check` đạt. Chưa chạy unit test hoặc API.

## Đồng bộ Dataset và Evaluation v3.2 - 2026-10-30

- **Mục tiêu:** Dùng trực tiếp split Dataset v3 và thống nhất toàn bộ artifact đánh giá với schema v3.2.
- **Thực hiện:** Thêm resolver split mới/legacy, validator leakage, schema summary và cơ chế đồng bộ schema nhúng; chuyển collector/scorer end-to-end và retrieval-only, chuẩn hóa action/architecture, provenance QLoRA và trace prompt/context thật.
- **Kết quả:** Dataset 7.100 case pass schema; train/test 4.258/2.838 không trùng ID hoặc nhóm truy vấn chuẩn hóa. Smoke RAG thật tạo prediction, case-score và summary hợp lệ; web healthy sau restart. 389 test đạt, 21 skipped; Ruff, compileall và `git diff --check` đạt.

## Follow-up stateless phục hồi thủ tục từ user history - 2026-10-30

- **Mục tiêu:** Cho case follow-up có history chuẩn vào retrieval khi không có signed state, đồng thời giữ biên an toàn của menu.
- **Thực hiện:** Chỉ khôi phục một định danh corpus-backed từ lượt `user`; đưa định danh vào classifier context và request retrieval. Không dùng assistant text, không suy menu, không kế thừa qua mã lạ hoặc nhiều thủ tục.
- **Kết quả:** Hồi quy đúng case căn cước `1.116405/AUTHORITY`; signed state sai có thể fallback an toàn, câu NEW không dính chủ đề cũ. 395 test đạt, 21 skipped; Ruff, compileall và diff check đạt.

## Mở rewrite MIXED_SCOPE khi chưa xác nhận được vế hỗ trợ - 2026-10-29

- **Mục tiêu:** Cho LLM đề xuất vế hành chính trích nguyên văn khi PhoBERT không xác nhận được vế nào trong câu đã tách.
- **Thực hiện:** Cho phép fallback tối đa 8 vế khi không có vế `IN_SCOPE` độc lập; giữ giới hạn phân loại và không cho LLM chọn giữa nhiều vế hành chính đã xác nhận.
- **Kết quả:** AST và `git diff --check` đạt. Chưa chạy unit test hoặc API.

## Giữ semantic evidence khi không nhận diện được thủ tục - 2026-10-29

- **Mục tiêu:** Không loại bỏ kết quả semantic chỉ vì không có mã thủ tục khớp catalog.
- **Thực hiện:** Giữ hits dò danh mục theo từng request chưa định danh, đưa lại vào danh sách evidence và ghi `retrieval_strategy=semantic`; mã nguồn tường minh không tồn tại vẫn không được tìm kiếm chéo.
- **Kết quả:** AST và `git diff --check` đạt. Chưa chạy unit test hoặc API.

## Chấm routing và cohort cho Evaluation v3.2 - 2026-10-30

- **Mục tiêu:** Cho prediction và score phản ánh route cuối, đồng thời so sánh riêng chất lượng follow-up và new-question.
- **Thực hiện:** Bổ sung `execution.routing`, chuẩn hóa route runtime sang nhãn Golden, chấm `route_accuracy` và tổng hợp `cohort_metric_aggregates` theo `turn_type`; đồng bộ schema, ví dụ và tài liệu vận hành.
- **Kết quả:** Hợp đồng prediction/case-score/summary và hồi quy đạt. Collector giữ đúng `included_text` từ prompt trace; smoke 10 câu được resume và chấm lại với 10/10 prediction thành công, gồm 5/5 follow-up và 5/5 new-question.

## Hiệu chỉnh section rõ ràng trên PhoBERT - 2026-10-30

- **Mục tiêu:** Không để nhãn section sai của PhoBERT giữ retrieval ở hồ sơ khi người dùng hỏi rõ trình tự hoặc căn cứ pháp lý.
- **Thực hiện:** Ưu tiên section từ cụm từ rõ ràng cho một request `IN_SCOPE`, giữ nguyên scope và thủ tục; ghi quyết định vào trace và thêm hồi quy hội thoại.
- **Kết quả:** 139 test routing liên quan, Ruff và compileall đạt. API thật sau restart giữ mã 1.000894 và trả đúng 4 chunk hồ sơ, 5 chunk trình tự, 4 chunk căn cứ pháp lý. Full suite chạy 399 test, còn một lỗi dependency Transformers/`tensorflow_text` không liên quan thay đổi.

## Hợp nhất extended metrics sau prediction - 2026-10-30

- **Mục tiêu:** Tái chấm prediction đã lưu bằng lexical, embedding và BERTScore mà không inference lại, đồng thời xuất một bộ artifact điểm thống nhất.
- **Thực hiện:** Thêm `--rescore`, metric từng case, kiểm tra hash Golden/prediction, merge supplemental vào case-score/summary/report và thay artifact qua thư mục tạm; bổ sung dependency evaluation.
- **Kết quả:** Hồi quy merge/rescore đạt; smoke thực tế tái chấm 10/10 và SHA-256 prediction không đổi. Dependency BERTScore/sentence-transformers import được, Transformers đúng pin 4.57.3 và `pip check` đạt; trọng số metric thật chưa tải/chạy.

## Tạo split SFT từ Dataset v3 - 2026-10-30

- **Mục tiêu:** Chuẩn bị hai tập train/validation SFT từ `Data/dataset_v3/train/golden_train.jsonl` mà không thay đổi nguồn Golden hoặc dùng tập test.
- **Thực hiện:** Chuyển lossless lịch sử hội thoại, câu hỏi và `expected_answer` sang schema `id/messages`; chia xác định bằng SHA-256 với seed 42 theo nhóm `(domain, standalone_query)` để cùng nhóm không rơi vào hai split.
- **Kết quả:** Tạo cục bộ `Data/dataset_v3/finetuning/train_sft.jsonl` gồm 3.385 case và `validation_sft.jsonl` gồm 873 case. Toàn bộ 4.258 ID được bảo toàn; không trùng ID hoặc nhóm truy vấn giữa hai split; schema hội thoại và phép kiểm tra Dataset v3 đạt.
## 2026-10-30 - Gom metadata thủ tục trùng tên trong Dataset v3

- **Mục tiêu:** Đặt các phiên bản thủ tục cùng tên và metadata tương ứng cạnh nhau để kiểm duyệt định danh theo mã, cấp và địa phương.
- **Thực hiện:** Thêm generator xác định tên trùng từ `golden_all.jsonl`, đọc payload theo mã từ SQLite corpus và sinh cây `Data/dataset_v3/duplicate_procedure_names/` với manifest tổng, manifest nhóm và file metadata từng mã.
- **Kết quả:** Sinh 46 folder cho 168 mã, gồm 5.768 chunk metadata và 168 PDF nguồn. Toàn bộ PDF khớp SHA-256 nguồn, mở được 1.914 trang và không thiếu mã/context/nhóm. Manifest lưu checksum Golden, metadata cache và từng PDF; test liên quan, Ruff, compileall, validator Dataset v3 và diff check đều đạt. Dữ liệu Golden và index nguồn được giữ nguyên.
# Lọc case cần predict lại theo model - 2026-11-03

- **Mục tiêu:** Chuẩn bị danh sách prediction retry có model rõ ràng sau khi sửa lỗi cắt output.
- **Thực hiện:** Đối chiếu 638 prediction mỗi model, lọc lỗi HTTP 502, hết token và cắt cứng 600 ký tự; trích nguyên vẹn case tương ứng từ `test_rag_pa1.jsonl` thành bốn JSON theo model, không đưa dữ liệu judge vào artifact.
- **Kết quả:** Sinh bốn file tại `Data/dataset_v3/prediction_retry/`: `qwen-rag-qlora` 36 case, `qwen-rag` 50, `qwen-base` 74 và `qwen-qlora` 0. Loại `GOLDEN_V3_006656` khỏi danh sách bắt buộc vì kết thúc hoàn chỉnh.

## Pipeline continued-SFT cho QLoRA + RAG - 2026-11-03

- **Mục tiêu:** Loại bỏ độ lệch giữa plain-answer SFT và hợp đồng JSON/evidence của runtime RAG.
- **Thực hiện:** Validator chấp nhận system message nhưng giữ luân phiên user/assistant; converter tạo target `answer/action/evidence_status/citations`; thêm profile train và serving/evaluation tách biệt.
- **Kết quả:** Đã sinh 1.931 train và 827 validation, không có duplicate conversation/question/answer chính xác giữa split; schema check đạt. Tokenizer Qwen chưa có trong cache host nên token percentile 16k chưa xác minh; GPU train, merge và chấm test chưa chạy.

## Bộ train/validation procedure-disjoint với PA1+PA2 - 2026-11-03

- **Mục tiêu:** Loại rủi ro ghi nhớ trực tiếp nội dung test khỏi pipeline RAG-SFT.
- **Thực hiện:** Lọc theo test ID, standalone query, context ID/text, đáp án dài và mã thủ tục; template ngắn/near-query khác thủ tục chỉ báo cáo.
- **Kết quả:** Loại 109 case, giữ 2.649 case; hậu kiểm mạnh đều bằng 0 và 2.649 target JSON qua parser runtime. Dữ liệu nguồn và hai file test giữ nguyên hash.

## 2026-11-06 - Khắc phục lỗi runtime từ báo cáo đánh giá toàn diện

- **Mục tiêu:** Loại bỏ chi phí đọc lại source không cần thiết, tránh kích hoạt sai chỉ dẫn trình bày và bảo toàn Unicode khi stream structured answer.
- **Thực hiện:** Cache nội dung fingerprint theo chữ ký đường dẫn/mtime/kích thước; cache source identity thread-safe theo vòng đời `ChatApplication`; matching từ khóa theo biên từ; ghép đúng cặp surrogate JSON; thống nhất fold discovery/routing; bỏ max-abs dư thừa trước L2 và thêm hồi quy.
- **Kết quả:** Các nhóm 37, 121, 31 và 130 test tập trung đều đạt; Ruff và compileall đạt. Full suite chạy 458 test; 1 failure và 5 error còn lại thuộc các vấn đề độc lập đã nêu trong hồ sơ yêu cầu, không phát sinh từ thay đổi này.

## 2026-11-08 - Khôi phục trình tự thực hiện từ corpus cũ

- **Mục tiêu:** Trả đúng trình tự của thủ tục đã nêu rõ khi chunk bước thực hiện trong corpus cũ bị gắn `section_type=other`.
- **Thực hiện:** Thêm fallback theo nội dung cho `procedure_step`, chỉ nhận chunk `other` có tiêu đề “Trình tự thực hiện” hoặc “Bước N”; giữ bộ lọc mã thủ tục và không thay đổi taxonomy ingestion mới.
- **Kết quả:** 104 test routing/retrieval đạt. Cả `/api/chat` và `/api/chat/stream` thật với thủ tục `1.000047` route `NEW/PROCEDURE`, truy xuất đúng ba bước và trả `answer/sufficient` thay vì menu không liên quan.

## 2026-11-08 - Phân biệt cách thực hiện với trình tự thực hiện

- **Mục tiêu:** Truy xuất đúng hình thức nộp khi người dùng hỏi “Cách thực hiện”, không trả lại danh sách các bước.
- **Thực hiện:** Bổ sung từ khóa xác định “cách thực hiện”/“cách thức thực hiện” cho `SUBMISSION_METHOD`; giữ “trình tự”/“các bước” ở `PROCEDURE`; thêm guard hậu sinh đối chiếu các hàng hình thức và fallback bằng nguyên bảng evidence; thêm alias kiểm duyệt “thủ tục kết hôn”/“kết hôn” cho mã `1.000894`.
- **Kết quả:** 154 test alias/routing/prompt/generation đạt. Câu tên rút gọn qua `/api/chat/stream` dùng `procedure_direct`, chỉ truy xuất `1.000894`/`submission_deadline_fee` và trả nguyên bảng Markdown ba hình thức cùng thời hạn 1 ngày, miễn phí.
