# Công việc hiện tại và trạng thái dự án

Tài liệu này ghi nhận phạm vi đang được duy trì trong mã nguồn và trạng thái có
thể kiểm chứng của repository tại thời điểm hiện tại.

## Công việc hiện tại

- Duy trì pipeline RAG cho dữ liệu thủ tục hành chính tiếng Việt trên CLI,
  notebook Colab và web UI/API cục bộ.
- Xử lý PDF/OCR, chia đoạn theo cấu trúc, tạo embedding BGE-M3 và lưu chỉ mục
  FAISS cùng metadata SQLite.
- Phân loại phạm vi/quan hệ hội thoại, viết lại câu hỏi nối tiếp, truy hồi ngữ
  cảnh và sinh câu trả lời có xét bằng chứng bằng Qwen qua Ollama.
- Chạy benchmark từ bộ câu hỏi độc lập, lưu và tiếp tục prediction, tính metric
  và tạo báo cáo đánh giá.
- Duy trì tính toàn vẹn của pack/corpus bằng manifest, checksum, revision và
  khóa ghi.

## Trạng thái thành phần

| Thành phần | Trạng thái hiện tại |
|---|---|
| Mã nguồn | Package duy nhất là `vigovbot`; notebook và điểm chạy dùng namespace `vigovbot.*` |
| Giao diện | CLI, notebook Colab và web UI/API cục bộ; so sánh Qwen trực tiếp với Qwen + RAG |
| Ingestion | Đọc PDF, hỗ trợ OCR và xuất dữ liệu đã chia đoạn |
| Embedding và corpus | BGE-M3, FAISS, SQLite, manifest và kiểm tra checksum/revision |
| Hỏi đáp | Dense RAG nhiều lượt; router dùng schema theo nhánh, có retry/fallback và chẩn đoán web |
| Đánh giá | Bộ test độc lập, prediction có thể tiếp tục, metric và biểu đồ |
| Kiểm thử | Bộ kiểm thử tự động không phụ thuộc model thật; lock dependency được xuất cho môi trường Windows x64 |

## Dữ liệu và vận hành hiện tại

- Cấu hình `configs/inference.yaml` yêu cầu corpus có đủ
  `tthc_unified.index`, `tthc_unified_metadata.json` và `corpus_manifest.json`.
- Thư mục `Data/vector/unified/` hiện có đủ index, metadata và
  `corpus_manifest.json`; cấu hình inference mặc định yêu cầu và xác minh manifest.
- Chế độ tương thích corpus cũ được điều khiển bằng
  `data.allow_legacy_corpus`; cấu hình mặc định đặt giá trị này là `false`.
- Luồng truy hồi dùng dense top-k, không có BM25, hybrid search, reranker hoặc
  ngưỡng điểm tối thiểu.
- Web giữ history riêng theo model/chế độ ở trình duyệt và mất khi reload; chưa
  có persistence phía server, quản lý người dùng, xác thực/TLS hay fine-tuning QLoRA.

## Giới hạn đã ghi nhận

- Chất lượng câu trả lời phụ thuộc dữ liệu nguồn, kết quả OCR, cách chia đoạn,
  chất lượng truy hồi và model Ollama.
- Qwen thực hiện routing và tự xét bằng chứng; JSON được ràng buộc/kiểm tra nhưng
  chất lượng nhãn và kết luận vẫn phụ thuộc model, không có judge độc lập.
- FAISS được nạp vào RAM; bước tạo corpus giữ metadata và ma trận vector trong
  bộ nhớ.
- Kết quả kiểm thử mô phỏng chỉ xác nhận luồng kỹ thuật, không chứng minh độ
  đúng ngữ nghĩa của câu trả lời hoặc hiệu lực của thông tin thủ tục.
