# Hệ thống tài liệu ViGovBot

- [Agent Skills cho RAG/chatbot và tối ưu Codex](agent-skills/README.md)

`docs/README.md` là mục lục duy nhất. Các tài liệu được nhóm theo mục đích để
tránh trộn hướng dẫn vận hành, quyết định kiến trúc và báo cáo thực nghiệm.

## Bắt đầu và môi trường

- [Thiết lập và gate phát triển](setup/development.md)
- [Môi trường thực thi và khả năng tái lập](setup/environments.md)
- [Thiết lập GPU cho QLoRA](setup/gpu-setup.md)
- [Chạy ViGovBot bằng Docker Desktop](setup/docker.md)
- [Quy trình đóng góp](../CONTRIBUTING.md)

## Kiến trúc

- [Kiến trúc hệ thống](architecture/architecture.md)
- [Đặc tả embedding và corpus](architecture/embedding.md)

## Hướng dẫn sử dụng

- [Evaluation mở rộng và judge Ollama](guides/evaluation-extended.md)

- [Tham chiếu CLI `vigov`](guides/cli.md)
- [Vận hành pipeline RAG](guides/trien-khai-rag-co-ban.md)
- [Kiểm tra sẵn sàng trước khi chạy web](guides/web-readiness.md)
- [RAG nhiều lượt](guides/rag-multi-turn.md)
- [Routing PhoBERT bốn head và menu theo trạng thái](guides/four-head-routing.md)
- [Đánh giá QA/RAG](guides/qa-rag-evaluation.md)
- [Vận hành huấn luyện](guides/training.md)
- [Phục hồi QLoRA v2 từ adapter trên máy mới](guides/qlora-model-restore.md)
- [Phục hồi PhoBERT router trên máy mới](guides/phobert-model-recovery.md)
- [Đánh giá, biểu đồ và báo cáo QLoRA](guides/evaluation.md)

## Chuyên đề QLoRA

- [Continued-SFT theo hợp đồng QLoRA + RAG](training/rag-sft.md)
- [Pipeline QLoRA local-first và GPU portable](training/qlora-training.md)
- [Vận hành full QLoRA độc lập](training/qlora-operations.md)

## Báo cáo kết quả

- [Báo cáo kết thúc mốc nghiên cứu/demo](reports/bao-cao-ket-thuc-nghien-cuu-demo.md)
- [Báo cáo hệ thống nhãn phân loại và actions](reports/bao-cao-phan-loai-nhan-va-actions.md)
- [Báo cáo khoa học quá trình huấn luyện QLoRA v2](reports/bao-cao-khoa-hoc-qua-trinh-train-qlora-v2.md)
- [Benchmark độ trễ reranker (10 câu)](reports/reranker-latency-20261029.md)
- [Báo cáo Dataset v3 và đánh giá model](reports/model-evaluation/dataset-v3-and-model-evaluation-report.md)
- [Benchmark và EDA router](reports/model-evaluation/router-benchmark-and-eda-report.md)

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
