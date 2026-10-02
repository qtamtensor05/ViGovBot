# Trạng thái triển khai và lộ trình phát triển

Tài liệu phân biệt năng lực đã có trong mã nguồn với các hạng mục dự kiến. Một
hạng mục chỉ được xem là hoàn thành khi đáp ứng tiêu chí nghiệm thu tương ứng.

## Năng lực hiện tại

- PDF/OCR, chunking theo cấu trúc, tạo corpus BGE-M3/FAISS, cache SQLite và RAG Ollama.
- Benchmark có lưu/resume prediction, chống rò rỉ đáp án chuẩn, metric và biểu đồ.
- Package `vigovbot`, CLI thống nhất, lớp tương thích, cấu hình theo nhóm.
- Manifest/checksum/revision cho pack/corpus; khóa ghi và kiểm thử dữ liệu lỗi.
- Hỏi đáp một câu độc lập với bộ test; CI và lock theo môi trường Windows hiện tại.

## Mốc phát triển và tiêu chí nghiệm thu

| Mốc | Tiêu chí hoàn thành |
|---|---|
| Xác nhận môi trường CI | Các job Windows/Linux và wheel smoke đều xanh trên GitHub |
| Baseline chất lượng | Lưu cùng bộ test/corpus, model revision, config và báo cáo baseline/RAG; công bố coverage và ca lỗi |
| Rà soát dữ liệu | Kiểm tra mẫu OCR/metadata/chunking; tập lỗi có nhãn và test hồi quy |
| Đánh giá câu trả lời | Đo truy hồi, nguồn thực sự dùng, khả năng từ chối khi thiếu thông tin và kiểm tra thủ công |
| QLoRA | Có pipeline train/eval riêng, tách train/test và so sánh cùng điều kiện với baseline |
| Dịch vụ hỏi đáp nếu cần | API có vòng đời model, giới hạn tài nguyên, health check và kiểm thử tải phù hợp |

QLoRA, API web và hội thoại nhiều lượt là công việc dự kiến, chưa được trình bày
như tính năng hiện có. Không dùng kết quả test mô phỏng để khẳng định chất lượng
ngữ nghĩa hay độ đúng của thông tin thủ tục.
