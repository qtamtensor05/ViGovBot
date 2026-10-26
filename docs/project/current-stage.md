# Trạng thái hệ thống hiện tại

## Mục tiêu

Vận hành ViGovBot bằng cấu trúc canonical, hỗ trợ Base, RAG và QLoRA; đánh giá
có nguồn gốc rõ ràng và truy hồi đúng thủ tục hành chính.

## Thực hiện

- Source chính đặt tại `src/vigovbot/`; CLI công khai là `vigov`.
- Docker vận hành Web và Ollama, dùng cache model/RAG bền vững.
- RAG hỗ trợ exact-match mã/tên thủ tục, ưu tiên loại mục và rerank MiniLM.
- Evidence quá ngân sách được rút gọn theo hàng/field/phần tử hoàn chỉnh; không
  còn bỏ toàn bộ bảng hoặc JSON có thể chiếu an toàn vào prompt.
- Routing dùng context `4096` và giới hạn sinh `128` token riêng; generation vẫn
  dùng ngân sách `8192`/`512`.
- QLoRA dùng adapter đã huấn luyện; RAG vẫn là nguồn căn cứ cho nội dung hiện hành.
- Evaluation v2 tách prediction, scoring, judge và export; Golden SFT tách train/validation.

## Kết quả

- Stack Docker CUDA, `/api/health`, `/api/chat` và `vigov doctor` đã được kiểm
  chứng ngày 2026-10-25.
- Retrieval theo mã/tên thủ tục và rerank đã được kiểm chứng bằng unit test và
  API container.
- Không có pipeline huấn luyện hoặc benchmark dài đang chạy.
- Hồ sơ vận hành đã được tinh gọn theo quy định mới.
- Cấu hình và regression routing đã được kiểm chứng; latency A/B chưa được đo do
  runtime Ollama/Docker không hoạt động.
