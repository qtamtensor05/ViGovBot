# Trạng thái hệ thống hiện tại

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
- Web dùng `/api/chat/stream` để hiển thị token dần theo quá trình sinh; endpoint
  `/api/chat` cũ vẫn giữ nguyên cho evaluation và client hiện có.

## Kết quả

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
