# Công việc hiện tại và trạng thái dự án

Tài liệu này ghi nhận phạm vi đang được duy trì trong mã nguồn và trạng thái có
thể kiểm chứng của repository tại thời điểm hiện tại.

## Công việc hiện tại

- Duy trì pipeline RAG cho dữ liệu thủ tục hành chính tiếng Việt trên CLI,
  notebook Colab và web UI/API cục bộ.
- Xử lý PDF/OCR, chia đoạn theo cấu trúc, tạo embedding BGE-M3 và lưu chỉ mục
  FAISS cùng metadata SQLite.
- Phân loại phạm vi/quan hệ hội thoại bằng PhoBERT 4-head mặc định, xác thực
  state/catalog, truy hồi ngữ cảnh và sinh câu trả lời có xét bằng chứng bằng
  Qwen qua Ollama hoặc QLoRA local theo profile.
- Chạy benchmark từ bộ câu hỏi độc lập, lưu và tiếp tục prediction, tính metric
  và tạo báo cáo đánh giá.
- Duy trì tính toàn vẹn của pack/corpus bằng manifest, checksum, revision và
  khóa ghi.

## Trạng thái thành phần

| Thành phần | Trạng thái hiện tại |
|---|---|
| Mã nguồn | Package duy nhất là `vigovbot`; notebook và điểm chạy dùng namespace `vigovbot.*` |
| Giao diện | CLI, notebook Colab và web UI/API cục bộ; so sánh Base, RAG và QLoRA |
| Training | `src/vigovbot/training/`: QLoRA 4-bit, masking multi-turn, checkpoint/resume, CLI `vigov train`; chưa xác nhận production |
| Ingestion | Đọc PDF, hỗ trợ OCR và xuất dữ liệu đã chia đoạn |
| Embedding và corpus | BGE-M3, FAISS, SQLite, manifest và kiểm tra checksum/revision |
| Hỏi đáp | RAG v2 nhiều lượt; PhoBERT 4-head là router mặc định, LLM v2 là backend cấu hình tường minh; state/menu có chữ ký và chẩn đoán web |
| Đánh giá | Golden v3, prediction có thể tiếp tục, metric retrieval/generation/routing và báo cáo |
| Kiểm thử | Bộ kiểm thử tự động không phụ thuộc model thật; lock dependency được xuất cho môi trường Windows x64 |

## Dữ liệu và vận hành hiện tại

- Cấu hình `configs/rag/inference.yaml` yêu cầu corpus có đủ
  `tthc_unified.index`, `tthc_unified_metadata.json` và `corpus_manifest.json`.
- Thư mục `Data/vector/unified/` hiện có đủ index, metadata và
  `corpus_manifest.json`; cấu hình inference mặc định yêu cầu và xác minh manifest.
- Chế độ tương thích corpus cũ được điều khiển bằng
  `data.allow_legacy_corpus`; cấu hình mặc định đặt giá trị này là `false`.
- Luồng trả lời online dùng direct FAISS top-k, không có reranker. Host và Docker
  mặc định hiện dùng `top_k: 15`; profile Docker GPU dùng `top_k: 5`. BM25 +
  cosine chỉ phục vụ khám phá/xác nhận tên thủ tục trong catalog, không rerank
  các chunk trả lời.
- Web giữ history riêng theo model/chế độ ở trình duyệt và mất khi reload; chưa
  có persistence phía server, quản lý người dùng, xác thực/TLS. Fine-tuning QLoRA đã có trong module `training`.

## Giới hạn đã ghi nhận

- Chất lượng câu trả lời phụ thuộc dữ liệu nguồn, kết quả OCR, cách chia đoạn,
  chất lượng truy hồi và model Ollama.
- PhoBERT 4-head thực hiện routing mặc định; Qwen sinh câu trả lời và chỉ tham gia
  routing khi chọn backend `llm` hoặc fallback extractive `MIXED_SCOPE` có bước
  PhoBERT kiểm chứng lại. Chất lượng nhãn, retrieval và kết luận vẫn cần benchmark
  độc lập; JSON hợp lệ không tự chứng minh nội dung đúng.
- FAISS được nạp vào RAM; bước tạo corpus giữ metadata và ma trận vector trong
  bộ nhớ.
- Kết quả kiểm thử mô phỏng chỉ xác nhận luồng kỹ thuật, không chứng minh độ
  đúng ngữ nghĩa của câu trả lời hoặc hiệu lực của thông tin thủ tục.
