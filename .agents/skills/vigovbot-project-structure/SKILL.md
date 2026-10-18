---
name: vigovbot-project-structure
description: Preserve ViGovBot's canonical source, configuration, documentation and CLI layout when adding, moving, renaming or consolidating files. Use for repository refactors and changes to configs, docs, entry points or package boundaries; skip implementation edits that do not affect structure.
---

# Cấu trúc dự án ViGovBot

Áp dụng cấu trúc hiện có, không tạo thêm cây song song cho cùng trách nhiệm.
Trước khi di chuyển file, kiểm tra Git status, người dùng của đường dẫn hiện tại
và các artifact cần giữ tương thích.

## Vị trí canonical

- Mã Python thuộc `src/vigovbot/`. QLoRA chỉ có một package tại
  `src/vigovbot/training/`; không tạo lại `training/` hoặc `src/training/`.
- Evaluation và QA benchmark dùng chung `src/vigovbot/evaluation/`; không
  tạo lại package `src/vigovbot/qa_v4/`. CLI công khai là `vigov eva`.
- CLI công khai thuộc `src/vigovbot/cli/` và dùng console command `vigov`.
  Handler CLI chỉ điều phối service hiện có, không sao chép business logic.
- Cấu hình nguồn thuộc đúng miền:
  - `configs/ingestion/`: pipeline, parser/OCR và chunking;
  - `configs/rag/`: inference và evaluation RAG;
  - `configs/training/`: base, `environments/` và `experiments/` QLoRA.
- Tài liệu thuộc đúng nhóm:
  - `docs/setup/`, `docs/architecture/`, `docs/guides/`, `docs/training/`,
    `docs/reports/`, `docs/project/`;
  - gốc `docs/` chỉ giữ `README.md` làm mục lục.
- Dataset và artifact runtime giữ tại `Data/` và `outputs/`; không sao chép vào
  `docs/` và không di chuyển checkpoint/run lịch sử khi chưa có yêu cầu rõ ràng.

## README và tài liệu

Giữ README gốc ngắn: mô tả dự án, khả năng chính, quick start tối thiểu, cấu
trúc cấp cao và liên kết tới `docs/README.md`. Không lặp hướng dẫn môi trường,
danh sách option, quy trình GPU/training/evaluation hoặc troubleshooting trong
README gốc; đặt chi tiết tại nhóm docs phù hợp.

Khi thêm hoặc di chuyển tài liệu, cập nhật `docs/README.md`, mọi liên kết đến/đi
và chạy `tests.test_documentation`. Không sửa nội dung lịch sử trong
`docs/project/` chỉ để làm cho đường dẫn cũ trông hiện hành; bổ sung mốc mới.

## Migration và kiểm chứng

Khi đổi path, tìm cả literal, `Path(...)`, script, notebook, test và Markdown.
Sửa đường dẫn tương đối theo vị trí file mới. Giữ snapshot `config.yaml` trong
run lịch sử; đó không phải config nguồn cần gom lại.

Kiểm chứng theo phạm vi thay đổi, tối thiểu gồm test liên quan, Ruff,
`compileall`, `git diff --check` và link test nếu chạm tài liệu. Không tuyên bố
runtime GPU/web/model đã được xác nhận nếu chỉ chạy help, mock hoặc source test.
