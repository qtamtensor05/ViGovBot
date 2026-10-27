# Trạng thái hệ thống hiện tại

## Mục tiêu

Vận hành ViGovBot bằng cấu trúc canonical, hỗ trợ Base, RAG và QLoRA; đánh giá
có nguồn gốc rõ ràng và truy hồi đúng thủ tục hành chính.

## Thực hiện

- RAG đã có bước hỏi lại theo metadata: chọn thủ tục khi nhiều mã phù hợp,
  chọn section khi thiếu mục tiêu; context riêng từng model trên API thường/streaming
  và web, có hỗ trợ client cũ qua lịch sử. Không cần tạo lại embedding hoặc huấn luyện router.

- RAG follow-up đã có nhánh SQLite theo mã/phần, ngữ cảnh theo model/hội thoại,
  fallback giới hạn đúng nguồn và nút xóa hội thoại. Đã kiểm tra Python/JavaScript
  và model cục bộ; web đã restart để nạp backend mới ngày 2026-10-27.
- Source chính đặt tại `src/vigovbot/`; CLI công khai là `vigov`.
- Docker mặc định chạy web Base/RAG bằng Torch CPU và Ollama; QLoRA cục bộ
  nằm trong service/profile `web-gpu` tùy chọn. Cả hai dùng cache model/RAG bền vững.
- RAG hỗ trợ exact-match mã/tên thủ tục, ưu tiên loại mục và đưa trực tiếp top 5
  kết quả retrieval vào LLM, không rerank trong runtime online.
- Evidence quá ngân sách được rút gọn theo hàng/field/phần tử hoàn chỉnh; không
  còn bỏ toàn bộ bảng hoặc JSON có thể chiếu an toàn vào prompt.
- Routing dùng context `4096` và giới hạn sinh `128` token riêng; generation vẫn
  dùng ngân sách `8192`/`512`.
- Routing hỗ trợ `llm`, `fasttext` và `hybrid`; mặc định vẫn là `llm`. FastText
  chỉ quyết định trực tiếp câu hỏi mới trong/ngoài phạm vi khi vượt threshold;
  hybrid chuyển các trường hợp còn lại về Qwen.
- QLoRA dùng adapter đã huấn luyện; RAG vẫn là nguồn căn cứ cho nội dung hiện hành.
- Evaluation v2 tách prediction, scoring, judge và export; Golden SFT tách train/validation.
- Web dùng `/api/chat/stream` để hiển thị token dần theo quá trình sinh; endpoint
  `/api/chat` cũ vẫn giữ nguyên cho evaluation và client hiện có.

## Kết quả

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
  container; thay đổi top 5 trực tiếp chưa được kiểm chứng lại bằng API container.
- Không có pipeline huấn luyện hoặc benchmark dài đang chạy.
- Hồ sơ vận hành đã được tinh gọn theo quy định mới.
- Cấu hình và regression routing đã được kiểm chứng; đã có baseline Qwen nhưng
  latency A/B classifier chưa được đo trên dataset routing độc lập.
- Image Docker có FastText CPU đã build thành công. Chưa có artifact đạt quality
  gate hoặc benchmark API `llm`/`fasttext`/`hybrid`, nên chưa bật hybrid mặc định.
- Streaming đã qua kiểm thử provider/API/UI giả lập và container thật. API
  `qwen-base` đã phát 4 sự kiện token, TTFT warm 0,300 giây và hoàn tất
  sau 0,486 giây; chưa thao tác xác minh trên trình duyệt thật.
- Image web mặc định là 2,03 GB và không chứa CUDA; Base/RAG streaming đã
  trả `success`. Image GPU 12,8 GB giữ riêng QLoRA, đã nhận RTX 4050/CUDA 12.8.
  BuildKit cache hiện 0 B sau khi thu hồi 32,01 GB; các volume model/RAG được giữ nguyên.

- Phép đo follow-up ngày 2026-10-27: retrieval warm 1,182 → 0,067 s; lượt cold
  1,170 → 1,456 s do nạp danh mục. Tổng latency vẫn phụ thuộc routing/generation.
