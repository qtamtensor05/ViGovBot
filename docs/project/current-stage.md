# TASK-20261018-13 - completed

- Dependency huggingface-hub khai báo trực tiếp; 5 lock resolve lại; range torch
  và pin 2.9.1 không xung đột. Docs phân biệt core Python với GPU extras.
- __all__ thay suppression F401; clean-env dùng host interpreter/OS, optional lock;
  wheel kiểm tra cả entrypoint mới/cũ; root main không còn tự chạy ingestion.
- Đã dọn 2 pyc mồ côi, 3 cây skill rỗng và thêm ignore patterns yêu cầu.
- PASS: wheel build/install ngoài checkout, defaults, cả hai entrypoint + help
  train/eva/data/doctor, root help, 14 tests, Ruff/compileall/docs/diff-check.
- NOT RUN: clean install matrix từng OS/Python, GPU/model/E2E. Chưa commit.
- [Lịch sử triển khai](implementation-history.md) · [Stage archive](stage-history-20261018.md).
