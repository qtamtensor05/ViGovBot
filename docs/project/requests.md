# Thay đổi hệ thống

## Gom case Golden theo tên thủ tục trùng - 2026-10-30

- **Mục tiêu:** Tập hợp các case Golden đề cập tên thủ tục trùng vào đúng thư mục nhóm để kiểm duyệt các trường hợp cùng tên nhưng khác mã.
- **Thực hiện:** Thêm collector khớp tên chuẩn hóa trên câu hỏi, truy vấn độc lập và lịch sử hội thoại, chọn nhóm có tên dài nhất và ghi case nguyên dòng kèm summary định danh ground truth vào từng folder.
- **Kết quả:** Hoàn tất cho 46 nhóm với 794 case; 539 case khớp mã trong nhóm, 255 case dùng mã ngoài nhóm và 3 case thiếu định danh nguồn. Golden, split và metadata nguồn không bị sửa.

## Sửa Golden smoke trùng tên thủ tục - 2026-10-30

- **Mục tiêu:** Loại bỏ sai lệch routing do Golden yêu cầu một mã thủ tục cụ thể nhưng câu hỏi chỉ nêu tên trùng với nhiều bản ghi trong catalog.
- **Thực hiện:** Bổ sung mã `1.115490` cho `GOLDEN_V3_006630`, đồng bộ Golden/SFT, thêm kiểm tra ứng viên định danh mơ hồ và hồi quy giữ hành vi hỏi làm rõ khi thiếu mã.
- **Kết quả:** Golden/SFT local đã đồng bộ; 52 test tập trung và full suite 402 test đều đạt (15 skipped); validator 7.100 case, Ruff, compile và diff check đều đạt. Smoke lần 3 chạy mới 10/10 case thành công, route accuracy 100%; `GOLDEN_V3_006630` truy xuất đúng mã `1.115490` và trả `answer`. Hai lỗi action độc lập còn lại là `GOLDEN_V3_001984` và `GOLDEN_V3_005750`.

## Hiển thị trạng thái đánh giá cho từng câu trả lời Web - 2026-10-30

- **Mục tiêu:** Cho người dùng biết câu trả lời là đầy đủ, một phần, cần làm rõ hay từ chối; đồng thời thấy mức bằng chứng và cách truy xuất.
- **Thực hiện:** Bổ sung `evidence_status` vào payload công khai và bảng trạng thái tiếng Việt trên cả luồng streaming lẫn non-streaming; hiển thị action, evidence, retrieval, lý do quyết định, phạm vi, loại lượt và section.
- **Kết quả:** 114 test liên quan, Ruff, compile và `git diff --check` đạt. Web Docker healthy; `/api/chat` và `/api/chat/stream` thật cùng trả `action=abstain`, `evidence_status=missing`, `retrieval_strategy=procedure_direct`. Chưa kiểm tra trực quan vì phiên Computer Use không có trình duyệt khả dụng.

## Từ chối theo bằng chứng truy xuất và bảo toàn Unicode - 2026-10-30

- **Mục tiêu:** Chỉ từ chối dữ liệu hồ sơ khi context thực sự không hỗ trợ định danh được hỏi; không gán cứng kết quả theo tiền tố mã và không làm hỏng tiếng Việt.
- **Thực hiện:** Truy xuất tài liệu trước, so khớp định danh riêng trong câu hỏi với context rồi mới quyết định `missing/abstain`; nếu context chứa định danh thì tiếp tục generation. Chuỗi phản hồi được lưu UTF-8 đúng.
- **Kết quả:** 112 test tập trung, Ruff, compile và `git diff --check` đạt. Đối chiếu Golden nhận đúng 150/150 ca không trả lời, 0/6.950 ca còn lại bị đánh dấu nhầm. Web Docker healthy; API thật trả `identifier_not_in_evidence`, có retrieval và tiếng Việt không chứa ký tự thay thế.

## Bổ sung 150 ca không có câu trả lời cho golden v3 - 2026-10-30

- **Mục tiêu:** Bổ sung 150 câu hỏi thực tế không thể trả lời từ tài liệu thủ tục, có danh tính thủ tục được lấy từ PDF và metadata nguồn.
- **Thực hiện:** Đối chiếu 138 cặp PDF/metadata trong `Data/dataset_v3/linh_vuc_thieu`; thêm 150 ca `is_unanswerable=true`, `expected_action=abstain` thuộc năm tình huống vận hành hồ sơ và 30 mẫu diễn đạt.
- **Kết quả:** Hoàn tất; `golden_all.jsonl` có 7.100 bản ghi, 150 ca mới đều hợp lệ schema, có cặp nguồn, không trùng ID/bản ghi và không có ứng viên gần-trùng ở ngưỡng SequenceMatcher 0,90.

## Chuẩn hóa golden_all v3 theo schema — 2026-10-30

- **Mục tiêu:** Gộp hai bộ golden lĩnh vực thành một file cuối và chuẩn hóa toàn bộ bản ghi theo `schema/golden_dataset.schema.json`.
- **Thực hiện:** Thống nhất ID `GOLDEN_V3_*`; tách `validation_audit` sang sidecar; map các giá trị cũ; bổ sung 19 domain vào enum; giữ nguyên hai thư mục nguồn.
- **Kết quả:** 6.950/6.950 bản ghi hợp lệ `golden_dataset.schema.json`, 0 ID trùng; audit tách riêng 3.797 bản ghi; giữ backup trước chuẩn hóa và báo cáo mapping. 14 unit test schema/SFT đạt.

## Giữ lại semantic hits khi chưa nhận diện mã thủ tục - 2026-10-29

- **Mục tiêu:** Không bỏ các chunk semantic đã tìm được chỉ vì catalog không nhận diện được tên thủ tục.
- **Thực hiện:** Giữ hits theo từng yêu cầu chưa có mã; dùng lại chúng làm evidence và ghi strategy `semantic`. Mã tường minh ngoài catalog không vào fallback.
- **Kết quả:** AST và `git diff --check` đạt; chưa chạy unit test hoặc API.

## Rewrite MIXED_SCOPE khi không có vế được xác nhận - 2026-10-29

- **Mục tiêu:** Cho phép rewrite chọn lọc khi câu MIXED_SCOPE tách thành nhiều vế nhưng PhoBERT chưa xác nhận được vế nào.
- **Thực hiện:** Cho phép rewrite nếu PhoBERT không xác nhận vế hành chính độc lập nào và tổng số vế không quá 8; vẫn chặn khi có nhiều vế hành chính được xác nhận.
- **Kết quả:** AST và `git diff --check` đạt; chưa chạy unit test hoặc API.

## Câu hỏi có số thứ tự khi không có menu - 2026-10-29

- **Mục tiêu:** Để câu hỏi mới như “thủ tục 1” đi qua router khi không có menu lựa chọn hợp lệ.
- **Thực hiện:** `direct_choice` chỉ coi selection có cấu trúc là lựa chọn khi menu vắng mặt; văn bản có số được chuyển tới router. Trạng thái được truyền nhưng không xác thực vẫn giữ lỗi lựa chọn hết hạn.
- **Kết quả:** AST và `git diff --check` đạt; chưa chạy unit test hoặc API.

## Tích hợp BAAI/bge-reranker-v2-m3 - 2026-10-29

- **Mục tiêu:** Lấy top 10 ứng viên retrieval, rerank và đưa top 3 vào model trả lời.
- **Thực hiện:** Tích hợp cross-encoder vào cả pipeline RAG cũ và luồng PhoBERT; truy hồi 10 ứng viên, rerank rồi gửi tối đa 3 đoạn; thêm trace, fallback và cache model Docker.
- **Kết quả:** Model revision đã ghim được tải vào volume Hugging Face; smoke model 10→3, API RAG, web health, 40 test tập trung và tài liệu đạt. Sau benchmark độ trễ, runtime tích hợp và cache model đã được gỡ theo yêu cầu tiếp theo; báo cáo benchmark được giữ tại `docs/reports/reranker-latency-20261029.md`. Một bộ test rộng hơn có 1 lỗi mismatch adapter tồn tại ngoài phạm vi; chưa benchmark chất lượng retrieval.


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

Giảm dung lượng runtime Docker mặc định và tránh mang dependency CUDA,
training khi chỉ chạy Base/RAG qua Ollama.

### Thực hiện

- Tách target web CPU và target QLoRA GPU, config và profile Compose tương ứng.
- Sinh lock CPU bằng resolver và giữ volume model/cache hiện có.

### Kết quả

Đã hoàn tất. Image mặc định giảm từ 12,8 GB xuống 2,03 GB, không
chứa CUDA/PEFT/bitsandbytes; Base và RAG streaming đều trả `success` trên
container healthy. Image GPU 12,8 GB giữ riêng QLoRA và đã xác nhận RTX 4050,
CUDA 12.8, PEFT/bitsandbytes. Đã thu hồi 32,01 GB BuildKit cache, không xóa
image runtime hay volume model/cache. Toàn bộ 249 test, Ruff, compileall,
Compose default/GPU và `git diff --check` đều đạt; 22 test tùy chọn bị skip.

## Streaming phản hồi LLM trên web - 2026-10-27

### Mục tiêu

Hiển thị phản hồi dần theo quá trình sinh token thay vì chờ toàn bộ văn bản.

### Thực hiện

- Bổ sung luồng streaming từ provider qua API đến giao diện web.
- Giữ nguyên hợp đồng `/api/chat` cho evaluation và client hiện có.

### Kết quả

Đã triển khai streaming qua Ollama, OpenAI-compatible và Transformers cục bộ;
web hiển thị token ngay khi nhận. Đã kiểm chứng 249 test, Ruff, compileall,
`git diff --check`, build/recreate container và API `qwen-base` thật. Lần gọi đã warm
phát token đầu sau 0,300 giây, hoàn tất sau 0,486 giây với 4 sự kiện token;
22 test dependency tùy chọn bị skip. Chưa thao tác xác minh trên trình duyệt thật.

## Intent classifier cho routing - 2026-10-27

### Mục tiêu

Giảm lượt gọi Qwen chỉ để phân loại intent nhưng vẫn giữ khả năng xử lý
follow-up, mixed, ambiguous và rollback an toàn.

### Thực hiện

- Thêm backend `llm`, `fasttext`, `hybrid` và artifact FastText có metadata/hash.
- Thêm dữ liệu contract, lệnh train/evaluate, diagnostics và fallback về Qwen.

### Kết quả

Đã triển khai backend, CLI, artifact validation, Docker packaging và diagnostics;
backend mặc định vẫn là `llm`. Đã kiểm chứng model FastText thật và regression
offline; quality gate và API latency chưa được xác nhận vì chưa có dataset routing
độc lập đã gán nhãn.

## Đưa trực tiếp top 5 retrieval vào LLM - 2026-10-26

### Mục tiêu

Gỡ bước rerank khỏi luồng RAG online và đưa trực tiếp năm kết quả FAISS đứng đầu
vào prompt của LLM.

### Thực hiện

- Loại cấu hình và lời gọi reranker khỏi runtime RAG.
- Đồng bộ profile host/Docker, giao diện quan sát context và kiểm thử liên quan.

### Kết quả

Đã chuyển runtime sang FAISS top 5 trực tiếp và loại cấu hình/module reranker
online. Đã kiểm chứng 36 test routing, 9 test server, 1 test UI, toàn bộ 235 test,
schema hai profile, Ruff, compileall và `git diff --check`; 21 test dependency tùy
chọn bị skip. Chưa xác minh API/container hoặc chất lượng câu trả lời thực vì
Docker daemon không hoạt động và host thiếu FAISS/model runtime.

## Rút gọn evidence có cấu trúc vượt ngân sách - 2026-10-25

### Mục tiêu

Không loại toàn bộ bảng hoặc giá trị JSON chỉ vì vượt `max_chunk_tokens`; giữ
phần bằng chứng hợp lệ trong prompt mà không cắt hỏng cấu trúc.

### Thực hiện

- Rút gọn bảng Markdown/HTML theo hàng hoàn chỉnh và JSON theo field/phần tử.
- Không thay đổi scalar hoặc giá trị trong ô; giữ giới hạn từng chunk, tổng
  context và trace phần nội dung thực tế đã dùng.

### Kết quả

Đã kiểm chứng bằng 11 test evidence chuyên biệt, full suite 238 test, Ruff,
compileall và `git diff --check`; 21 test dependency tùy chọn bị skip. Chưa chạy
tokenizer Qwen thật hoặc API generation vì môi trường Python hiện thiếu
Transformers/FAISS.

## Tách ngân sách context cho routing - 2026-10-25

### Mục tiêu

Giảm chi phí context và giới hạn đầu ra của lần gọi routing mà không thay đổi
ngân sách sinh câu trả lời.

### Thực hiện

- Thêm `llm.routing_num_ctx` và `llm.routing_num_predict`.
- Dùng ngân sách riêng cho payload và kiểm tra context của routing.
- Kiểm chứng cấu hình, hành vi routing và regression.

### Kết quả

Đã triển khai và kiểm chứng bằng 36 test routing, full suite 234 test và Ruff.
Chưa đo latency thực tế vì máy hiện không có Ollama hoặc Docker runtime hoạt động.

## Chuẩn hóa hồ sơ vận hành - 2026-10-25

### Mục tiêu

Giữ tài liệu triển khai ngắn gọn và chỉ cập nhật khi chỉnh sửa quan trọng ảnh
hưởng hệ thống hoặc vận hành.

### Thực hiện

- Đổi điều kiện kích hoạt `vigovbot-task-journal`.
- Chuẩn hóa hồ sơ theo `Mục tiêu - Thực hiện - Kết quả`.
- Hợp nhất lịch sử cũ, loại yêu cầu báo cáo, dọn dẹp và chỉnh sửa nhỏ.

### Kết quả

Hoàn tất ngày 2026-10-25.


## 2026-10-27 — Truy xuất follow-up theo mã thủ tục

### Mục tiêu

Bỏ embedding khi follow-up có thủ tục và phần dữ liệu xác định.

### Thực hiện

Triển khai truy xuất SQLite, ngữ cảnh riêng theo model/hội thoại và fallback có giới hạn nguồn.

### Kết quả

Hoàn tất mã nguồn, kiểm tra hồi quy và phép đo cục bộ; chưa restart web đang chạy. Chi tiết tại `outputs/verification/follow-up/report.md`.


## 2026-10-27 — Hỏi lại theo metadata thủ tục

- **Mục tiêu:** Xác định đúng thủ tục và nội dung cần tra cứu trước khi trả lời.
- **Thực hiện:** Tích hợp danh sách thủ tục/section từ SQLite, lựa chọn nhiều lượt và context riêng theo model vào RAG/API/web.
- **Kết quả:** Hoàn tất mã nguồn; 123 test Python và 2 test JavaScript đạt, có HTTP thường → streaming giả lập và kiểm tra SQLite thực tế. Chưa restart backend hoặc xác minh model/trình duyệt thật.


## 2026-10-27 — Giữ thủ tục khi chọn dòng nội dung và hỏi nối tiếp

- **Mục tiêu:** Sửa lỗi sao chép “4. Cách thức nộp, thời hạn và phí” làm mất thủ tục đã xác định, và giữ mã cho câu hỏi hồ sơ tiếp theo.
- **Thực hiện:** Đối chiếu số kèm nhãn với danh sách hiện tại; xác nhận mã từ context truy hồi trước khi giải quyết câu nối tiếp; phục hồi danh sách qua lỗi không tìm thấy do parser cũ.
- **Kết quả:** 103 test Python liên quan và 2 test JavaScript đạt. Backend đã restart; Qwen thật qua API thường/streaming giữ mã 1.000894 khi chọn dòng phí rồi hỏi hồ sơ, lượt hồ sơ dùng procedure_direct/required_documents.


## 2026-10-27 — Chọn nguyên dòng thủ tục có mã và cấp thực hiện

- **Mục tiêu:** Không lặp danh sách thủ tục khi người dùng sao chép nguyên lựa chọn, gồm mã và cấp thực hiện.
- **Thực hiện:** Dùng chung nhãn hiển thị/đối chiếu lựa chọn; phân biệt metadata mô tả lựa chọn với mục tiêu hỏi, giữ mục tiêu đã có.
- **Kết quả:** 105 test Python liên quan và 2 test JavaScript đạt. Backend đã restart; API thật xác nhận dòng 5 chọn mã 1.000180 và dòng 1 chọn mã 2.000037, chuyển sang section_required, không gọi lại router.


## 2026-10-27 — Phân biệt hỏi danh sách thủ tục với chọn tên chính xác

- **Mục tiêu:** Câu “Các thủ tục cấp lại chứng chỉ kiểm định viên” phải đưa các biến thể để chọn thay vì tự chốt mã 2.000066.
- **Thực hiện:** Phát hiện yêu cầu danh sách/số nhiều, mở rộng tên khớp sang biến thể dài hơn trong catalog trước bước chọn section; giữ ưu tiên mã cụ thể và mục tiêu đã rõ.
- **Kết quả:** 106 test Python liên quan và 2 test JavaScript đạt. Backend đã restart; API thật trả procedure_required với năm ứng viên và more=true; chọn mục 2 chuyển section_required cho mã 1.000187.


## 2026-10-27 — Streaming early exit cho LLM router

- **Mục tiêu:** Trả sớm nhánh ngoài phạm vi/làm rõ trên API streaming.
- **Thực hiện:** Đọc prefix scope/relation qua nhiều chunk, dừng sinh router khi nhãn kết thúc được xác định; đóng HTTP stream hoặc dừng/join worker Transformers. Giữ đối chiếu metadata trước câu làm rõ, dùng câu hỏi mặc định khi bỏ phần clarification của JSON. Gửi token kết quả trước model_result; API thường vẫn chờ JSON đầy đủ.
- **Kết quả:** 90 test routing/provider/server/clarification/documentation đạt; Ruff và compileall đạt. Test provider giả lập xác nhận không đọc phần đuôi JSON và đóng kết nối. Chưa kiểm chứng model thật hoặc hủy sinh trên GPU; Docker daemon chưa chạy.


## 2026-10-27 — Routing bốn nhóm nhãn và menu theo trạng thái

- **Mục tiêu:** Triển khai router base độc lập, chọn menu trực tiếp, section đa nhãn và nhiều thủ tục.
- **Thực hiện:** Thêm hợp đồng routing v2, router base độc lập, menu có trạng thái ký, section đa nhãn, truy hồi riêng từng thủ tục, nút chọn và kiểm thử hồi quy.
- **Kết quả:** 303 ca đạt, 22 ca bỏ qua trong 325 test; Ruff, compileall và diff check đạt. API Qwen thật xác nhận section của mã 1.000894, trạng thái chọn chứng chỉ và tìm kiếm catalog đều đúng; “thuê đất” được giữ trong phạm vi, “thành lập trường” chỉ trả ứng viên giáo dục. Chưa thao tác trình duyệt thật do không có browser kết nối. Không thay đổi golden, checkpoint hoặc chỉ mục.
## 2026-10-28 - Công khai schema Golden Dataset và Evaluation v2

- **Mục tiêu:** Cung cấp schema độc lập, đầy đủ trường cho dataset Golden và kết quả evaluation theo từng case.
- **Thực hiện:** Thêm `schema/golden_dataset.schema.json` và `schema/evaluation_case.schema.json`; khai báo trực tiếp cấu trúc Golden, execution output, các nhóm metric, provenance và trạng thái chấm điểm, không phụ thuộc schema ngoài thư mục.
- **Kết quả:** Hoàn tất; hai schema hợp lệ theo JSON Schema Draft 2020-12, 3.850 dòng Golden và một evaluation record sinh bởi code hiện tại đều validate thành công.


## 2026-10-29 — Sửa xác định thủ tục trước truy xuất

- **Mục tiêu:** Không bỏ tài liệu đúng khi tên router thiếu tiền tố Thủ tục.
- **Thực hiện:** Tách xác định mã từ câu hỏi/tên khỏi quyết định mở menu; bổ sung kiểm thử kết hôn và đối chứng API local.
- **Kết quả:** 125 kiểm thử liên quan, Ruff và compileall đạt. Web local đã nạp bản sửa; hai câu nguyên văn qua API streaming lấy đúng mã 1.000894: phí 1 đoạn, pháp lý 4 đoạn trong lượt hỏi tiếp. Chưa kiểm tra trực quan trình duyệt hoặc độ đầy đủ của câu trả lời sinh; chưa tái hiện trạng thái gây chọn nhầm 1.010998 ban đầu.


## 2026-10-29 — Tích hợp PhoBERT routing

- **Mục tiêu:** Dùng checkpoint PhoBERT bốn head thay router LLM và ghi đè section bằng từ khóa trong cấu hình vận hành.
- **Thực hiện:** Kiểm tra bundle, giữ PyVi/128 token/ngưỡng metadata; tích hợp định danh thủ tục bằng corpus và state, kiểm thử offline rồi API local. Không sửa checkpoint hoặc tạo lại index.
- **Kết quả:** Hoàn tất trên web local. 35 checksum đạt; adapter khớp token và xác suất script gốc trên 7 ca. Image web đã build/recreate, identity công bố backend/hash PhoBERT; API thật trả đúng phí 1 đoạn và căn cứ pháp lý 4 đoạn của mã 1.000894, ngoài phạm vi dừng trước retrieval. Tên thủ tục bị head phạm vi gán sai được catalog xác nhận, mở menu văn bản; nhập số phí trả đúng nguồn mà không chạy lại classifier. Bộ runtime/routing trong image đạt 146 test, 2 skipped; 7 test cấu hình đạt. Full host đạt 383 test, 22 skipped. Full suite trong image inference không áp dụng vì thiếu dependency evaluation và chỉ có một adapter QLoRA trong workspace. Chưa kiểm tra trực quan trình duyệt; checkpoint gán sai head trộn thủ tục cho một câu đối chứng nên không tuyên bố độ chính xác tổng thể.

## 2026-10-29 — Không mở menu khi câu hỏi cụ thể thiếu nhãn section

- **Mục tiêu:** Trả lời câu hỏi “đối tượng thực hiện” của thủ tục 3.000622 dù PhoBERT không có nhãn riêng và không vượt ngưỡng section.
- **Thực hiện:** Cho phép tìm toàn bộ section khi mã thủ tục là duy nhất và câu hỏi không phải tên/mã trần; giữ nguyên output checkpoint và menu cho truy vấn chỉ có danh tính.
- **Kết quả:** Hoàn tất trên web local; API thật trả đúng đáp án và nguồn `metadata_identity` của 3.000622. 52 test liên quan và kiểm tra tĩnh đạt.

## 2026-10-29 — Chuẩn hóa taxonomy chunking theo 11 nhãn PhoBERT

- **Mục tiêu:** Tách phí, thời hạn, cách nộp và kết quả thành metadata section độc lập để lọc retrieval chính xác.
- **Thực hiện:** Sửa chunker/config/schema routing, thêm projection bảng có fail-safe và fallback chỉ đọc cho corpus legacy.
- **Kết quả:** Hoàn tất source và hồi quy; 388 test đạt, 22 skipped. Mẫu thật 3.000622 sinh đúng `submission_method`, `processing_time`, `fee`, `result`. Chưa thay artifact runtime hoặc đo tuyên bố giảm 60–70% token.

## 2026-10-29 — Gating catalog override theo xác suất

- **Mục tiêu:** Giảm false positive khi câu ngoài lề chỉ nhắc tên/mã thủ tục.
- **Thực hiện:** Dùng band `[0,50; 0,85)` cho catalog override và ghi toàn bộ arbitration vào trace.
- **Kết quả:** Hoàn tất source; 80 test routing đạt. Ngưỡng là policy cấu hình cứng theo yêu cầu, chưa được calibration bằng benchmark.

## 2026-10-29 — Curated alias và confirmation menu phòng thủ

- **Mục tiêu:** Nhận cụm tên thủ tục rút gọn nhưng không tự chọn semantic candidate hoặc truy xuất khi scope chưa được xác nhận.
- **Thực hiện:** Alias kiểm duyệt được xác nhận trực tiếp; các ca khác dùng BM25/cosine, qualifier penalty, giới hạn sáu từ, score 0,70 và margin 0,08 để quyết định có mở menu hay không.
- **Kết quả:** Hoàn tất trên web local; 394 test đạt, 22 skipped. Alias “đổi bằng lái xe máy” trỏ đúng 1.115978 và không retrieval. “Làm hộ chiếu” bị giữ ngoài phạm vi do margin không đạt, chứng minh gate không mở menu mơ hồ.

## 2026-10-29 — Fallback chọn lọc cho MIXED_SCOPE

- **Mục tiêu:** Xử lý câu mixed có liên từ tự nhiên mà bộ tách dấu câu hiện tại không phân đoạn được.
- **Thực hiện:** Chỉ gọi LLM khi PhoBERT đã phân loại `MIXED_SCOPE`, regex chỉ còn một mảnh và không tìm được phần hỗ trợ; đoạn trích phải giữ mã/qualifier rồi được PhoBERT phân loại lại trước retrieval. Nhiều mảnh hỗ trợ vẫn hỏi lại để không làm rơi ý.
- **Kết quả:** Hoàn tất và restart web local. 401 test đạt, 22 skipped; 73 test routing liên quan đạt, Ruff/compileall/diff check đạt. API thật cho “Phí đăng ký kết hôn, tiện thể cho hỏi cách nấu phở” lấy đúng mã 1.000894, trả `partial`, 1 nguồn, rewriter 11,10 giây; câu ngoài phạm vi không vào nhánh này. Tỷ lệ MIXED_SCOPE 3–7% chưa được đo trên dữ liệu thật.

## 2026-10-30 - Đồng bộ Dataset và Evaluation v3.2

- **Mục tiêu:** Dùng trực tiếp split train/test của Dataset v3 và thống nhất Golden, prediction, case-score, summary với collector/scorer canonical.
- **Thực hiện:** Chuyển resolver, action/architecture, trace prompt, collector/scorer end-to-end và retrieval-only sang hợp đồng v3.2; thêm schema summary, validator split và giữ đọc layout Golden legacy.
- **Kết quả:** Dataset 7.100 case hợp lệ, train/test 4.258/2.838, 4 case loại có lý do, không trùng ID hoặc nhóm `(domain, standalone_query)`. Prediction, case-score và summary của smoke RAG thật đều pass schema; web healthy sau restart. Full suite đạt 389 test, bỏ qua 21 test phụ thuộc tùy chọn; Ruff, compileall và diff check đạt.

## 2026-10-30 - Khôi phục định danh cho follow-up không có signed state

- **Mục tiêu:** Cho phép history tham chiếu chứa đúng một thủ tục đã xác minh tiếp tục vào retrieval mà không làm yếu cơ chế bảo vệ menu và lựa chọn số.
- **Thực hiện:** Khôi phục tối đa một mã/tên/alias có trong catalog từ lượt `user` gần nhất; truyền định danh đó cho router và retrieval nhưng không phục hồi menu từ văn bản. Signed state hợp lệ vẫn ưu tiên; mã lạ, nhiều thủ tục, assistant-only và lựa chọn số đều dừng an toàn.
- **Kết quả:** Case tương đương `GOLDEN_V3_000984` đi `rag_search`, chọn đúng `1.116405` và `metadata_identity`. Full suite đạt 395 test, 21 skipped; 95 test conversation/server liên quan, Ruff, compileall và diff check đạt.

## 2026-10-30 - Hoàn thiện chấm routing và cohort cho Evaluation v3.2

- **Mục tiêu:** Đảm bảo smoke RAG theo schema mới lưu được quyết định route và báo cáo riêng follow-up/new-question.
- **Thực hiện:** Thêm `execution.routing` vào prediction/case-score, chuẩn hóa route runtime sang nhãn Golden, đưa `route_accuracy` vào nhóm routing và tổng hợp metric theo `turn_type` trong summary.
- **Kết quả:** Schema prediction/case-score/summary, collector và scorer đã đồng bộ; routing được chấm bằng `route_accuracy`, summary tách cohort `turn_type:follow_up` và `turn_type:new_question`. Collector đã đọc đúng `included_text` là context thực tế sau cắt ngân sách token. Run smoke được resume và chấm lại với 10/10 prediction thành công, gồm 5/5 follow-up và 5/5 new-question.

## 2026-10-30 - Hợp nhất extended metrics vào Evaluation v3.2

- **Mục tiêu:** Chấm lại prediction đã lưu bằng lexical, embedding và BERTScore mà không inference lại, đồng thời đưa điểm vào case-score, summary và report chính.
- **Thực hiện:** Bổ sung `--rescore`, tính metric từng case, hợp nhất supplemental theo hash Golden/prediction và thay thế đồng bộ các artifact điểm qua thư mục tạm.
- **Kết quả:** Luồng merge/rescore và schema đạt hồi quy; smoke thực tế tái chấm 10/10 case, giữ nguyên SHA-256 của `predictions.jsonl`. Dependency BERTScore/sentence-transformers đã cài và `pip check` đạt; trọng số metric thật chưa tải/chạy.

## 2026-10-30 - Hiệu chỉnh section rõ ràng khi PhoBERT dự đoán sai

- **Mục tiêu:** Giữ đúng thủ tục trong hội thoại nhưng chuyển retrieval sang mục người dùng nêu rõ như trình tự hoặc căn cứ pháp lý.
- **Thực hiện:** Cho từ khóa section rõ ràng hiệu chỉnh nhãn section của PhoBERT với một request trong phạm vi; không thay đổi scope, thủ tục hoặc mixed-procedure. Bổ sung trace và hồi quy cho chuỗi hỏi đăng ký kết hôn.
- **Kết quả:** Hoàn tất source và runtime local. API thật giữ mã `1.000894`, lần lượt truy xuất `required_documents`, `procedure_step` và `legal_basis` theo ba câu hỏi nối tiếp.
## 2026-10-30 - Gom metadata các thủ tục trùng tên trong Dataset v3

- **Mục tiêu:** Tạo từng thư mục cho mỗi nhóm tên thủ tục trùng trong Dataset v3 và đặt metadata đầy đủ của các mã cùng tên cạnh nhau để kiểm duyệt định danh.
- **Thực hiện:** Sinh dữ liệu dẫn xuất từ `golden_all.jsonl` và SQLite metadata runtime; giữ nguyên Golden, split train/test và corpus nguồn.
- **Kết quả:** Hoàn tất 46 nhóm, 168 mã, 5.768 chunk metadata và 168 PDF; manifest tổng và từng nhóm đã được đối chiếu không thiếu file, nhóm hoặc sai mã; checksum nguồn và hướng dẫn sử dụng đã được bổ sung.
