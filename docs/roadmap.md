# Công việc hiện tại và trạng thái dự án

Tài liệu này ghi nhận phạm vi đang được duy trì trong mã nguồn và trạng thái có
thể kiểm chứng của repository tại thời điểm hiện tại.

## Công việc hiện tại

- Duy trì pipeline RAG cho dữ liệu thủ tục hành chính tiếng Việt trên CLI và
  notebook Colab.
- Xử lý PDF/OCR, chia đoạn theo cấu trúc, tạo embedding BGE-M3 và lưu chỉ mục
  FAISS cùng metadata SQLite.
- Truy hồi ngữ cảnh, tạo prompt và sinh câu trả lời một lượt bằng Qwen qua
  Ollama, kèm thông tin nguồn.
- Chạy benchmark từ bộ câu hỏi độc lập, lưu và tiếp tục prediction, tính metric
  và tạo báo cáo đánh giá.
- Duy trì tính toàn vẹn của pack/corpus bằng manifest, checksum, revision và
  khóa ghi.

## Trạng thái thành phần

| Thành phần | Trạng thái hiện tại |
|---|---|
| Mã nguồn | Package chính là `vigovbot`; các package `src/<module>` giữ khả năng tương thích với điểm chạy cũ |
| Giao diện | CLI cục bộ và notebook Colab |
| Ingestion | Đọc PDF, hỗ trợ OCR và xuất dữ liệu đã chia đoạn |
| Embedding và corpus | BGE-M3, FAISS, SQLite, manifest và kiểm tra checksum/revision |
| Hỏi đáp | Truy hồi dense và sinh câu trả lời một lượt qua Ollama |
| Đánh giá | Bộ test độc lập, prediction có thể tiếp tục, metric và biểu đồ |
| Kiểm thử | Bộ kiểm thử tự động không phụ thuộc model thật; lock dependency được xuất cho môi trường Windows x64 |

## Dữ liệu và vận hành hiện tại

- Cấu hình `configs/inference.yaml` yêu cầu corpus có đủ
  `tthc_unified.index`, `tthc_unified_metadata.json` và `corpus_manifest.json`.
- Thư mục `Data/vector/unified/` đang có index và metadata nhưng không có
  `corpus_manifest.json`; cấu hình mặc định không nạp corpus này.
- Chế độ tương thích corpus cũ được điều khiển bằng
  `data.allow_legacy_corpus`; cấu hình mặc định đặt giá trị này là `false`.
- Luồng truy hồi dùng dense top-k, không có BM25, hybrid search, reranker hoặc
  ngưỡng điểm tối thiểu.
- Hệ thống không có API web, quản lý người dùng, lịch sử hội thoại hay pipeline
  fine-tuning QLoRA.

## Giới hạn đã ghi nhận

- Chất lượng câu trả lời phụ thuộc dữ liệu nguồn, kết quả OCR, cách chia đoạn,
  chất lượng truy hồi và model Ollama.
- Prompt điều khiển việc từ chối khi thiếu thông tin; pipeline không có bộ phân
  loại riêng để xác nhận câu hỏi nằm ngoài kho tri thức.
- FAISS được nạp vào RAM; bước tạo corpus giữ metadata và ma trận vector trong
  bộ nhớ.
- Kết quả kiểm thử mô phỏng chỉ xác nhận luồng kỹ thuật, không chứng minh độ
  đúng ngữ nghĩa của câu trả lời hoặc hiệu lực của thông tin thủ tục.
