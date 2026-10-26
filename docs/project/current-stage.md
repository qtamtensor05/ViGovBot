# Trạng thái hệ thống hiện tại

## Mục tiêu

Vận hành ViGovBot bằng cấu trúc canonical, hỗ trợ Base, RAG và QLoRA; đánh giá
có nguồn gốc rõ ràng và truy hồi đúng thủ tục hành chính.

## Thực hiện

- Source chính đặt tại `src/vigovbot/`; CLI công khai là `vigov`.
- Docker vận hành Web và Ollama, dùng cache model/RAG bền vững.
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

## Kết quả

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
