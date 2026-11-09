# Trạng thái hiện tại của ViGovBot

> Cập nhật: 2026-11-09. Mốc nghiên cứu/demo hiện tại đã được đóng.
> Báo cáo tổng kết và ranh giới bằng chứng nằm tại
> [báo cáo kết thúc nghiên cứu/demo](../reports/bao-cao-ket-thuc-nghien-cuu-demo.md).

## Trạng thái mốc

ViGovBot đã hoàn thành mục tiêu xây dựng prototype nghiên cứu cho hỏi đáp
thủ tục hành chính tiếng Việt. Repository giữ mã nguồn, cấu hình, kiểm
thử, Dataset v3, artifact đánh giá và tài liệu cần thiết để kiểm tra lại
kết quả. Mốc này không đại diện cho một hệ thống production.

Trên máy đóng mốc, các container, image, volume và network Docker của
ViGovBot đã được gỡ. `compose.yaml` và các hướng dẫn vẫn được giữ là
công thức tái lập; chúng không chứng minh runtime hiện đang hoạt động.

## Kết quả đã chốt

- Pipeline canonical bao phủ ingestion PDF/OCR, chunking theo cấu trúc, embedding
  BGE-M3, chỉ mục FAISS/SQLite, routing, hội thoại nhiều lượt, generation có
  ràng buộc bằng chứng, QLoRA và evaluation.
- PhoBERT bốn head cùng lớp adapter/catalog/state triển khai phân loại phạm vi,
  flow, mã thủ tục và section intent. Benchmark router v2 trên 1.246 mẫu ghi
  nhận Scope Accuracy 96,95%, Action Accuracy 91,33% và Strict E2E Accuracy 74,08%.
- Benchmark PA1 lưu kết quả cho sáu cấu hình Base, RAG, QLoRA v1, QLoRA v1 +
  RAG, QLoRA v2 và QLoRA v2 + RAG. QLoRA v2 + RAG dẫn đầu EM, key facts và
  citation recall trong snapshot, nhưng không dẫn đầu mọi metric Judge.
- Signed state v3 giữ câu hỏi, menu, mã thủ tục và section intent qua nhiều
  lượt; retrieval loại context khác mã trước generation.
- CLI `vigov`, web UI/API cục bộ, Docker profiles, cấu hình training/evaluation
  và các hướng dẫn phục hồi được giữ trong repository.

## Phần chưa hoàn thành

- Chưa chạy lại toàn bộ benchmark model sau các thay đổi state và section intent.
- QLoRA v2 + RAG còn invalid citation 30,35% trong snapshot PA1; abstention và
  unsupported answer chưa đạt mức phù hợp cho triển khai thực tế.
- Lần prediction QLoRA v2 + RAG hoàn thành 637/638 case do một lỗi HTTP 502.
- Chưa có bằng chứng về tải lớn, high availability, xác thực người dùng,
  TLS, session store phân tán hoặc giám sát production.

## Ngoài phạm vi mốc

- Chứng nhận hệ thống production hoặc cam kết SLA.
- Khẳng định thông tin thủ tục luôn còn hiệu lực mà không cập nhật nguồn.
- Tối ưu cho máy cấu hình yếu hoặc vận hành không có GPU.
- Reranker cross-encoder online; runtime hiện dùng direct FAISS top-k.

## Điểm bắt đầu nếu phát triển lại

1. Checkout tag `vigovbot-research-v1` để phục hồi mốc này.
2. Tạo branch mới từ tag hoặc `main`; không viết lại lịch sử mốc.
3. Phục hồi dependency, corpus và model theo
   [tài liệu setup](../setup/development.md),
   [hướng dẫn Docker](../setup/docker.md),
   [phục hồi PhoBERT](../guides/phobert-model-recovery.md) và
   [phục hồi QLoRA](../guides/qlora-model-restore.md).
4. Chạy preflight và test phù hợp trước khi chạy model hoặc benchmark thật.
5. Dùng các mục chưa hoàn thành trong [roadmap](roadmap.md) làm backlog.
