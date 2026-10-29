# Hệ thống tài liệu ViGovBot

- [Agent Skills cho RAG/chatbot và tối ưu Codex](agent-skills/README.md)

`docs/README.md` là mục lục duy nhất. Các tài liệu được nhóm theo mục đích để
tránh trộn hướng dẫn vận hành, quyết định kiến trúc và báo cáo thực nghiệm.

## Bắt đầu và môi trường

- [Thiết lập và gate phát triển](setup/development.md)
- [Môi trường thực thi và khả năng tái lập](setup/environments.md)
- [Thiết lập GPU cho QLoRA](setup/gpu-setup.md)
- [Chạy ViGovBot bằng Docker Desktop](setup/docker.md)
- [Triển khai container Tesla V100 32 GB](setup/remote-v100.md)
- [Quy trình đóng góp](../CONTRIBUTING.md)

## Kiến trúc và migration

- [Kiến trúc hệ thống](architecture/architecture.md)
- [Hướng dẫn migration và tương thích ngược](architecture/migration.md)
- [Tóm tắt refactor](architecture/refactor-summary.md)
- [Đặc tả embedding và corpus](architecture/embedding.md)

## Hướng dẫn sử dụng

- [Evaluation mở rộng và judge Ollama](guides/evaluation-extended.md)

- [Tham chiếu CLI `vigov`](guides/cli.md)
- [Vận hành pipeline RAG](guides/trien-khai-rag-co-ban.md)
- [RAG nhiều lượt](guides/rag-multi-turn.md)
- [Routing PhoBERT bốn head và menu theo trạng thái](guides/four-head-routing.md)
- [Đánh giá QA/RAG](guides/qa-rag-evaluation.md)
- [Vận hành huấn luyện](guides/training.md)
- [Đánh giá, biểu đồ và báo cáo QLoRA](guides/evaluation.md)

## Chuyên đề QLoRA

- [Pipeline QLoRA local-first và GPU portable](training/qlora-training.md)
- [Vận hành full QLoRA độc lập](training/qlora-operations.md)
- [Audit pre-GPU](training/qlora-pre-gpu-audit.md)
- [Experiment readiness](training/qlora-experiment-readiness.md)

## Báo cáo kết quả

- [Kiểm chứng đóng gói bằng chứng và prompt RAG](reports/rag-evidence-hardening-20261024.md)

- [Đánh giá RAG vs Base trên TTHC v1](reports/bao-cao-danh-gia-rag-vs-base-tthc-v1.md)
- [Phân tích QLoRA Qwen2.5-7B](reports/bao-cao-phan-tich-qlora-qwen2-5-7b.md)
- [Đề xuất triển khai Evaluation Run v2 cho các model](reports/evaluation-v2-model-implementation-proposal.md)
- [Đánh giá chi tiết mô hình Standalone Base (Evaluation v2)](reports/bao-cao-danh-gia-chi-tiet-model-base.md)
- [Đánh giá chi tiết mô hình Base + RAG (Evaluation v2)](reports/bao-cao-danh-gia-chi-tiet-model-base-rag.md)
- [Huấn luyện & Đánh giá mô hình Tinh chỉnh QLoRA (Evaluation v2)](reports/bao-cao-danh-gia-chi-tiet-model-qlora-finetuning.md)
- [So sánh & Đối sánh tổng hợp 3 mô hình Base vs Base+RAG vs QLoRA (Evaluation v2)](reports/bao-cao-so-sanh-tong-hop-3-model-base-rag-qlora.md)

## Quản trị dự án

- [Roadmap và trạng thái thành phần](project/roadmap.md)
- [Yêu cầu](project/requests.md)
- [Trạng thái hiện tại](project/current-stage.md)
- [Lịch sử triển khai](project/implementation-history.md)
- [Nhật ký vấp ngã](project/failure-journal.md)
- [Nguồn skill](project/skill-sources.md)
- [Hướng dẫn agent](../AGENTS.md)

## Quy ước duy trì

- README gốc là điểm vào cho cài đặt và lệnh cơ bản; tài liệu chuyên sâu nằm tại đây.
- Hướng dẫn cung cấp lệnh thực thi; kiến trúc mô tả ranh giới và hợp đồng.
- Báo cáo ghi nhận kết quả tại một thời điểm, không đại diện trạng thái hiện thời.
- Hồ sơ `project/` chỉ ghi thay đổi quan trọng ảnh hưởng hệ thống hoặc vận hành;
  mỗi mốc dùng `Mục tiêu - Thực hiện - Kết quả`.
