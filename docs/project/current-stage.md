# Trạng thái hệ thống hiện tại

## Golden smoke phân biệt thủ tục trùng tên - 2026-10-30

- **Mục tiêu:** Không chấm hành vi hỏi làm rõ an toàn thành routing sai khi Golden ngầm chọn một mã trong nhiều thủ tục trùng tên.
- **Thực hiện:** `GOLDEN_V3_006630` nêu rõ Thanh Hóa, mã `1.115490` và `metadata_filters.source_code`; validator liệt kê candidate có tên bằng nhau nhưng thiếu mã để rà soát.
- **Kết quả:** Smoke mới `dataset-v3-train-rag-10-20261030-run-3` đạt route accuracy 10/10. Case đích có `IN_SCOPE/NEW/PROCEDURE`, chỉ truy xuất `1.115490` và trả `answer`; runtime vẫn hỏi chọn khi tên trùng mà không có mã.

## Extended metrics sau prediction - 2026-10-30

- **Mục tiêu:** Cho phép tái chấm prediction bất biến và xuất một bộ case-score/summary/report thống nhất.
- **Thực hiện:** `score --rescore` dựng artifact dẫn xuất trong thư mục tạm; lexical/embedding/BERTScore được gắn theo từng case và khóa bằng hash đầu vào.
- **Kết quả:** Luồng merge và tái chấm run đã tồn tại đã được xác minh; smoke 10/10 giữ nguyên prediction. Extra `evaluation` và môi trường hiện tại có đủ BERTScore/sentence-transformers với Transformers 4.57.3; trọng số metric thật chưa được tải/chạy.

## Evaluation v3.2 có routing và cohort - 2026-10-30

- **Mục tiêu:** Prediction và score phản ánh được route cuối, đồng thời tách kết quả follow-up/new-question.
- **Thực hiện:** `execution.routing` giữ route thô/canonical và nhãn classifier quan sát được; case-score có `routing.route_accuracy`; summary có `cohort_metric_aggregates` theo turn type.
- **Kết quả:** Hợp đồng schema và hồi quy đã đạt. Lỗi collector bỏ qua `included_text` trong trace đã được sửa; run smoke hiện có 10/10 prediction thành công, gồm 5/5 follow-up và 5/5 new-question, không còn case lỗi do thiếu prompt context.

## Follow-up không có signed state - 2026-10-30

- **Mục tiêu:** Xử lý history tham chiếu của evaluator và client stateless mà không tin nội dung assistant hoặc menu không ký.
- **Thực hiện:** Router khôi phục duy nhất một định danh thủ tục có trong catalog từ các lượt `user` mới nhất; signed state vẫn ưu tiên và lựa chọn số vẫn bắt buộc state hợp lệ.
- **Kết quả:** Follow-up có mã hoặc tên duy nhất tiếp tục retrieval đúng thủ tục; nhiều/mã lạ/assistant-only vẫn `clarify`, câu hỏi thủ tục mới không kế thừa chủ đề cũ. 395 test đạt, 21 skipped.

## Dataset và Evaluation v3.2 - 2026-10-30

- **Mục tiêu:** Dùng một hợp đồng đánh giá thống nhất cho Dataset v3, prediction, case-score và summary.
- **Thực hiện:** Resolver ưu tiên `Data/dataset_v3/{split}/golden_{split}.jsonl` và vẫn đọc layout legacy. Collector/scorer end-to-end và retrieval-only dùng schema v3.2, action/architecture canonical, trace prompt/context thật và provenance fine-tuned bắt buộc.
- **Kết quả:** Dataset 7.100 case hợp lệ; train/test 4.258/2.838 không trùng ID hoặc nhóm `(domain, standalone_query)`. Smoke RAG thật và ba artifact đánh giá pass schema; web Docker healthy. Full suite đạt 389 test, 21 skipped.

## Hiển thị trạng thái đánh giá cho từng câu trả lời Web - 2026-10-30

- **Mục tiêu:** Làm rõ kết quả và mức bằng chứng của từng phản hồi ngay trên Web.
- **Thực hiện:** API công khai thêm `evidence_status`; Web hiển thị action, evidence, retrieval, quyết định routing, phạm vi, loại lượt và section bằng nhãn tiếng Việt kèm mã kỹ thuật.
- **Kết quả:** 114 test liên quan đạt; Web Docker healthy. Hai endpoint chat thật truyền đủ action/evidence/retrieval; JavaScript Web đã kiểm tra cú pháp và formatter trạng thái. Chưa kiểm tra trực quan vì phiên Computer Use không có trình duyệt khả dụng.

## Từ chối theo bằng chứng truy xuất và bảo toàn Unicode - 2026-10-30

- **Mục tiêu:** Giữ câu trả lời trong phạm vi bằng chứng thực tế, không suy từ hình thức mã hồ sơ và không phát sinh mojibake.
- **Thực hiện:** Luồng RAG truy xuất trước rồi kiểm tra định danh riêng có xuất hiện trong context hay không; chỉ `abstain/missing` khi bằng chứng thiếu. Câu chào độc lập vẫn được tách khỏi thủ tục cũ.
- **Kết quả:** 112 test tập trung đạt; 150/150 ca `is_unanswerable` được nhận diện, 0/6.950 ca còn lại bị đánh dấu nhầm. Web Docker healthy; `/api/chat` thật trả tiếng Việt UTF-8 đúng và không có ký tự `�`.

## Bổ sung ca không có câu trả lời cho golden v3 - 2026-10-30

- **Mục tiêu:** Tăng độ bao phủ đánh giá khả năng từ chối suy đoán khi PDF/metadata không chứa dữ liệu vận hành của hồ sơ cá nhân.
- **Thực hiện:** Tạo 150 ca từ 138 thủ tục thuộc 56 lĩnh vực, gồm 30 follow-up và 120 câu hỏi mới; phủ đều trạng thái, cán bộ xử lý, lý do từ chối, lịch hẹn và yêu cầu bổ sung.
- **Kết quả:** Dataset hiện có 7.100 bản ghi; 150 ca mới đều dùng `is_unanswerable=true`, `expected_action=abstain`, context/citation rỗng và `metadata_filters.source_code` trỏ đúng cặp PDF/metadata. Toàn bộ file hợp lệ schema, không trùng ID hoặc bản ghi.

## Golden dataset v3 hợp nhất, schema-clean — 2026-10-30

- **Mục tiêu:** Có một file golden cuối dùng được cho đánh giá, không còn khác biệt schema giữa hai bộ dữ liệu.
- **Thực hiện:** `Data/dataset_v3/golden_all.jsonl` chứa 7.100 bản ghi, 283 domain; 6.950 ca chuẩn hóa dùng ID `GOLDEN_V3_000001` → `GOLDEN_V3_006950`, 150 ca không có câu trả lời dùng ID `GOLDEN_V3_UA_000001` → `GOLDEN_V3_UA_000150`; `validation_audit` nằm trong `golden_all.audit.jsonl`; bản trước chuẩn hóa giữ tại `golden_all.pre-normalize.jsonl`.
- **Kết quả:** 7.100/7.100 bản ghi hợp lệ schema, 0 ID trùng và 0 bản ghi giống hoàn toàn. Các mapping ngữ nghĩa đã chốt: `easy` → `medium`, `test` → `in_domain`, `relevance_completeness` theo báo cáo, bổ sung 19 domain vào enum.

## Đồng bộ hóa tài liệu kiến trúc RAG Contract v2 và kiểm chứng toàn diện — 2026-10-29

- **Mục tiêu:** Đồng bộ hóa toàn bộ tài liệu kiến trúc hệ thống (rchitecture.md), hướng dẫn routing bốn head (our-head-routing.md), và hướng dẫn vận hành pipeline RAG (	rien-khai-rag-co-ban.md) theo đúng trạng thái mã nguồn và runtime hiện hành.
- **Thực hiện:** Cập nhật sơ đồ luồng Mermaid RAG v2, đặc tả PhoBERT 4-head, ranh giới HMAC signed state (256 phiên), cơ chế direct_choice (không chặn oan câu hỏi chứa số khi không có menu), nhánh phân rã Qwen extractive rewrite cho MIXED_SCOPE (<= 8 vế), cơ chế dự phòng unresolved_semantic_hits (trace semantic), bảng tham số cấu hình RAG v2 loại bỏ hoàn toàn FastText cũ, ghi chú thực nghiệm về độ trễ Reranker CPU (~12,28s).
- **Kết quả:** Bộ kiểm thử tự động 392/392 test pass (21 skipped cho external), toàn bộ tài liệu kiến trúc và hướng dẫn vận hành đồng bộ 100% với mã nguồn src/vigovbot/rag/.

## Semantic retrieval khi thiếu danh tính thủ tục - 2026-10-29

- **Mục tiêu:** Cho phép generation dùng evidence FAISS nếu không tìm được tên/mã thủ tục nhưng semantic search vẫn có kết quả.
- **Thực hiện:** Candidate semantic không gán mã được giữ làm evidence khi chưa nhận diện tên; trace phân biệt chiến lược `semantic` với `procedure_direct`.
- **Kết quả:** AST và `git diff --check` đạt; toàn bộ 392 unit test tự động đạt (21 skipped).

## Fallback rewrite cho MIXED_SCOPE nhiều vế - 2026-10-29

- **Mục tiêu:** Cho phép LLM trích vế hành chính khi phân tách được câu nhưng PhoBERT không xác nhận vế nào.
- **Thực hiện:** Rewrite được phép khi không có vế hành chính độc lập nào được PhoBERT xác nhận, tối đa 8 vế; nhiều vế hành chính được xác nhận vẫn phải làm rõ.
- **Kết quả:** AST và `git diff --check` đạt; toàn bộ 392 unit test tự động đạt (21 skipped).

## Điều hướng số thứ tự khi không có menu - 2026-10-29

- **Mục tiêu:** Không chặn câu hỏi mới chỉ vì câu có cụm “thủ tục 1” hoặc “mục 2”.
- **Thực hiện:** Văn bản số chỉ được xem là lựa chọn khi có menu; trạng thái được truyền nhưng không xác thực vẫn bị từ chối.
- **Kết quả:** AST và `git diff --check` đạt; toàn bộ 392 unit test tự động đạt (21 skipped).

## Retrieval RAG sau khi gỡ reranker - 2026-10-29

- **Mục tiêu:** Trở về luồng truy xuất FAISS trực tiếp sau khi đo chi phí độ trễ của thử nghiệm reranker.
- **Thực hiện:** Khôi phục `top_k: 5`, gỡ cấu hình và module reranker online, dừng web trước khi xóa riêng cache `BAAI/bge-reranker-v2-m3`; giữ nguyên cache embedding, corpus và báo cáo benchmark.
- **Kết quả:** Reranker không còn tham gia runtime; web Docker healthy và `/api/health` trả HTTP 200 sau restart. Kết quả benchmark 10 câu vẫn được lưu tại [báo cáo](../reports/reranker-latency-20261029.md).


## Tích hợp PhoBERT routing — 2026-10-29

- **Mục tiêu:** Thay phân loại LLM và ghi đè nhãn section bằng checkpoint PhoBERT.
- **Thực hiện:** Nạp local bốn head/PyVi/ngưỡng gốc, adapter corpus/state, cấu hình mặc định và mount read-only; lớp dependency Docker riêng.
- **Kết quả:** Web local đang chạy PhoBERT; identity công bố hash checkpoint. Adapter khớp token/xác suất script gốc trên 7 ca. API thật xác nhận phí, căn cứ pháp lý hỏi tiếp, ngoài phạm vi và menu tên thủ tục → nhập số. Bộ runtime/routing trong image đạt 146 test, 2 skipped; 7 test cấu hình đạt. Full host đạt 383 test, 22 skipped. Chưa kiểm tra trực quan trình duyệt; head trộn thủ tục còn một ca đối chứng dự đoán sai.

## Xác định mã thủ tục trước truy xuất — 2026-10-29

- **Mục tiêu:** Giữ bằng chứng đúng khi router trả tên thiếu tiền tố Thủ tục.
- **Thực hiện:** Xác định mã độc lập với menu, ưu tiên tên/mã trong câu hỏi đơn thủ tục; bổ sung biến thể pháp lí.
- **Kết quả:** 125 kiểm thử liên quan, Ruff và compileall đạt. Web local đã nạp bản sửa; hai câu nguyên văn qua API streaming lấy đúng mã 1.000894: phí 1 đoạn, pháp lý 4 đoạn trong lượt hỏi tiếp. Chưa kiểm tra trực quan trình duyệt hoặc độ đầy đủ của câu trả lời sinh; chưa tái hiện trạng thái gây chọn nhầm 1.010998 ban đầu.

## Hợp đồng đánh giá bốn cấu hình v3.2 — 2026-10-28

- **Mục tiêu:** Thống nhất hợp đồng mới, bỏ tương thích schema đầu ra cũ.
- **Thực hiện:** Ba schema độc lập golden/prediction/evaluation, chỉ có $ref nội bộ;
  architecture base/finetuned/rag/finetuned_rag quyết định dữ liệu và metric áp dụng;
  Base/fine-tuning không cần retrieval, điểm không áp dụng không ghi thành 0.
  Không chấm router; fine-tuning bắt buộc định danh adapter/checkpoint. Golden có
  evaluation_plan, relevance nhị phân và liên kết bằng chứng/cặp thử nhiễu.
  Theo phạm vi người dùng chốt: chỉ schema, kiểm thử và tài liệu; runtime giữ nguyên.
- **Kết quả:** 44 kiểm thử schema/tài liệu đạt; hai ví dụ multi-intent hợp lệ.
  JSONL cũ giữ nguyên, cần bổ sung evaluation_plan trước khi dùng schema mới.
  Ví dụ JSON là fixture tổng hợp. Collector/scorer chưa hỗ trợ v3.2; kiểm tra
  liên kết ID/hash/rank xuyên trường cần validator ngữ nghĩa khi triển khai runtime.

## Mục tiêu

Vận hành ViGovBot bằng cấu trúc canonical, hỗ trợ Base, RAG và QLoRA; đánh giá
có nguồn gốc rõ ràng và truy hồi đúng thủ tục hành chính.

## Thực hiện

- Routing mặc định v2: bốn nhóm nhãn, model base Qwen độc lập, trạng thái có chữ ký, menu dạng văn bản trên web và truy hồi theo từng thủ tục/section. Hợp đồng v1 chỉ còn tương thích LLM; v2 không dùng early exit prefix. Xem [hướng dẫn](../guides/four-head-routing.md).

- RAG đã có bước hỏi lại theo metadata: chọn thủ tục khi nhiều mã phù hợp,
  chọn section khi thiếu mục tiêu; context riêng từng model trên API thường/streaming
  và web, có hỗ trợ client cũ qua lịch sử. Không cần tạo lại embedding hoặc huấn luyện router.

- RAG follow-up đã có nhánh SQLite theo mã/phần, ngữ cảnh theo model/hội thoại,
  fallback giới hạn đúng nguồn và nút xóa hội thoại. Đã kiểm tra Python/JavaScript
  và model cục bộ; web đã restart để nạp backend mới ngày 2026-10-27.
- Source chính đặt tại `src/vigovbot/`; CLI công khai là `vigov`.
- Docker mặc định chạy web Base/RAG bằng Torch CPU và Ollama; QLoRA cục bộ
  nằm trong service/profile `web-gpu` tùy chọn. Cả hai dùng cache model/RAG bền vững.
- RAG hỗ trợ exact-match mã/tên thủ tục, ưu tiên loại mục và gửi trực tiếp FAISS
  top 5 vào LLM; reranker BGE đã được gỡ khỏi runtime.
- Evidence quá ngân sách được rút gọn theo hàng/field/phần tử hoàn chỉnh; không
  còn bỏ toàn bộ bảng hoặc JSON có thể chiếu an toàn vào prompt.
- Routing dùng context `4096` và giới hạn sinh `768` token riêng; generation vẫn
  dùng ngân sách `8192`/`512`.
- QLoRA dùng adapter đã huấn luyện; RAG vẫn là nguồn căn cứ cho nội dung hiện hành.
- Evaluation v2 tách prediction, scoring, judge và export; Golden SFT tách train/validation.
- Dataset v3 có artifact fine-tuning cục bộ tại `Data/dataset_v3/finetuning/`: train 3.385 case và validation 873 case, chia xác định theo nhóm domain/truy vấn để tránh leakage.
- Web dùng `/api/chat/stream` để hiển thị token dần theo quá trình sinh; endpoint
  `/api/chat` cũ vẫn giữ nguyên cho evaluation và client hiện có.

## Kết quả

- `Data/dataset_v3/duplicate_procedure_names/` chứa 46 folder tên trùng, 168 mã, 5.768 chunk metadata và 168 PDF nguồn từ corpus hiện hành. Mỗi folder có manifest nhóm, JSON metadata và PDF kèm checksum cho từng mã; Golden, split train/test và vector index không thay đổi.

- Schema độc lập cho Golden Dataset và Evaluation v2 nằm tại `schema/`; toàn bộ
  3.850 dòng Golden và evaluation record sinh từ `build_record` đã validate theo
  JSON Schema Draft 2020-12.

- Yêu cầu “Các thủ tục cấp lại chứng chỉ kiểm định viên” đã trả danh sách lựa
  chọn qua API thật sau restart, không tự chốt tên khớp 2.000066. Chọn mục 2
  chuyển sang các section của 1.000187; danh sách giới hạn năm mục có báo còn thêm.

- Sao chép nguyên dòng thủ tục gồm tên, mã, cấp thực hiện đã được xác minh qua API
  sau restart: mục 5 → 1.000180 và mục 1 → 2.000037, chuyển sang chọn section,
  không lặp lại danh sách thủ tục hoặc gọi lại router.

- Hỏi lại metadata và nối tiếp: bản sửa chọn dòng và hỏi danh sách đạt 106 test Python
  liên quan và 2 test JavaScript; Ruff/compileall đạt. Backend đã restart. Qwen thật
  qua API thường → streaming giữ mã kết hôn 1.000894 khi chọn mục phí rồi hỏi hồ sơ;
  lượt hồ sơ dùng procedure_direct và required_documents. Chưa thao tác trình duyệt thật.
  SQLite thực tế xác nhận 6.192 thủ tục và sáu section cho mã tạm trú 1.004194.

- Stack Docker CUDA, `/api/health`, `/api/chat` và `vigov doctor` đã được kiểm
  chứng ngày 2026-10-25.
- Retrieval theo mã/tên thủ tục đã được kiểm chứng bằng unit test và API
  container. Độ trễ thử nghiệm reranker được ghi riêng trong báo cáo ngày 2026-10-29;
  không dùng kết quả đó để kết luận chất lượng retrieval.
- Không có pipeline huấn luyện hoặc benchmark dài đang chạy.
- Hồ sơ vận hành đã được tinh gọn theo quy định mới.
- Cấu hình và regression routing đã được kiểm chứng; đã có baseline Qwen nhưng
  latency A/B classifier chưa được đo trên dataset routing độc lập.
- Streaming đã qua kiểm thử provider/API/UI giả lập và container thật. API
  `qwen-base` đã phát 4 sự kiện token, TTFT warm 0,300 giây và hoàn tất
  sau 0,486 giây; chưa thao tác xác minh trên trình duyệt thật.
- Image web mặc định là 2,03 GB và không chứa CUDA; Base/RAG streaming đã
  trả `success`. Image GPU 12,8 GB giữ riêng QLoRA, đã nhận RTX 4050/CUDA 12.8.
  BuildKit cache hiện 0 B sau khi thu hồi 32,01 GB; các volume model/RAG được giữ nguyên.

- Phép đo follow-up ngày 2026-10-27: retrieval warm 1,182 → 0,067 s; lượt cold
  1,170 → 1,456 s do nạp danh mục. Tổng latency vẫn phụ thuộc routing/generation.

- Kiểm chứng routing v2: 303 ca đạt, 22 ca bỏ qua trong 325 test; Ruff, compileall và diff check đạt. Catalog sửa nhãn ngoài phạm vi sai khi câu hỏi khớp hành động/đối tượng thủ tục, đồng thời xếp hạng ứng viên theo khoảng cách từ khóa để tránh trôi miền semantic. API Qwen thật xác nhận “thuê đất” trong phạm vi và “thành lập trường” chỉ trả ứng viên giáo dục. Chưa thao tác trình duyệt thật do không có browser kết nối.

- PhoBERT không vượt ngưỡng section nhưng đã xác định chính xác một thủ tục và
  câu hỏi còn mục tiêu cụ thể thì retrieval tìm toàn bộ section của đúng mã;
  câu chỉ nêu tên/mã vẫn mở menu. API thật xác nhận câu hỏi đối tượng thực hiện
  của mã 3.000622 trả đúng `metadata_identity_1_p1`.

- Chunking mới đồng bộ bốn section chi tiết với PhoBERT: `submission_method`,
  `processing_time`, `fee`, `result`. Runtime hiện vẫn dùng corpus legacy và cầu
  đọc tương thích; chưa rebuild/công bố FAISS nên chưa đo mức giảm token.

- Arbitration phạm vi chỉ cho catalog đổi `OUT_OF_SCOPE` khi
  `0,50 ≤ P(OUT) < 0,85`; trace ghi xác suất, band và outcome. Câu trần “Đăng ký
  kết hôn” có thể bị giữ ngoài phạm vi vì checkpoint từng cho `P(OUT)≈0,925`.

- Curated alias có thể xác nhận trực tiếp mã; hybrid BM25/cosine với qualifier
  penalty chỉ được mở confirmation menu cho cụm ngắn đủ score và margin. Menu
  không retrieval/generation; chọn mới nâng scope, phủ nhận giữ ngoài phạm vi.

- Khi PhoBERT dự đoán `MIXED_SCOPE` mà split câu bằng dấu câu/“và” thất bại,
  Qwen được gọi một lần để trích câu hỏi nguyên văn; PhoBERT phải xác nhận lại
  `IN_SCOPE` trước retrieval. API thật đã trả đúng phí mã 1.000894 và ghi chú phần
  ngoài phạm vi. Chưa đo tỷ lệ ca mixed trong traffic hoặc hiệu năng đại diện.

- Section được nêu rõ trong câu hỏi như hồ sơ, trình tự hoặc căn cứ pháp lý có
  thể hiệu chỉnh nhãn section PhoBERT cho một request `IN_SCOPE`; scope và danh
  tính thủ tục vẫn giữ nguyên. API local đã xác nhận chuỗi follow-up mã 1.000894
  truy xuất đúng `required_documents`, `procedure_step` và `legal_basis`.
