# TASK-20261025-05 — Hợp nhất evaluation Golden

- Yêu cầu: triển khai một workflow Golden, gỡ QA/v1 cũ theo phương án đã duyệt.
- Trạng thái: in_progress.
- Dataset canonical: Data/golden_dataset; SFT là dữ liệu dẫn xuất riêng.
- Phạm vi: CLI, loader, capture, scoring, retrieval, caller RAG, tests và tài liệu.
- Tiêu chí: một CLI không hậu tố phiên bản; không còn runtime QA cũ; kiểm tra resume, coverage, không truyền gold vào inference; bảo toàn dữ liệu và artifact.
- Kiểm chứng: đang thực hiện.
