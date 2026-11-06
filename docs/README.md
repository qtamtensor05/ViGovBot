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
- [Rerank tài liệu RAG](guides/rag-reranking.md)
- [Đánh giá QA/RAG](guides/qa-rag-evaluation.md)
- [Vận hành huấn luyện](guides/training.md)
- [Đánh giá, biểu đồ và báo cáo QLoRA](guides/evaluation.md)

## Chuyên đề QLoRA

- [Continued-SFT theo hợp đồng QLoRA + RAG](training/rag-sft.md)
- [Pipeline QLoRA local-first và GPU portable](training/qlora-training.md)
- [Vận hành full QLoRA độc lập](training/qlora-operations.md)
- [Audit pre-GPU](training/qlora-pre-gpu-audit.md)
- [Experiment readiness](training/qlora-experiment-readiness.md)

## Báo cáo kết quả

- [Báo cáo toàn diện quy trình QLoRA (Mục 3.5)](reports/bao-cao-toan-dien-quy-trinh-qlora.md)
- [Báo cáo thiết kế dữ liệu thực nghiệm và phương pháp đánh giá (Mục 3.6 & 3.7)](reports/bao-cao-thiet-ke-du-lieu-va-phuong-phap-danh-gia.md)
- [Báo cáo chi tiết các module xử lý chính ViGovBot](reports/bao-cao-cac-module-xu-ly-chinh-vigovbot.md)
- [Báo cáo chi tiết toàn bộ luồng hoạt động RAG ViGovBot](reports/bao-cao-chi-tiet-luong-rag-vigovbot.md)
- [Phân tích chuyên sâu cơ chế Prompting, Routing và Quyết định](reports/chuyen-sau-prompting-routing-quyet-dinh-rag.md)
- [Báo cáo hệ thống nhãn phân loại và actions](reports/bao-cao-phan-loai-nhan-va-actions.md)
- [Benchmark độ trễ reranker (10 câu)](reports/reranker-latency-20261029.md)

### Đánh giá model trên dataset PA1

- [Tổng hợp tất cả model](reports/model-evaluation/all-models.md)
- [Base](reports/model-evaluation/base.md)
- [RAG](reports/model-evaluation/rag.md)
- [QLoRA v1](reports/model-evaluation/qlora-v1.md)
- [QLoRA v1 + RAG](reports/model-evaluation/qlora-v1-rag.md)
- [QLoRA v2](reports/model-evaluation/qlora-v2.md)
- [QLoRA v2 + RAG](reports/model-evaluation/qlora-v2-rag.md)

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
