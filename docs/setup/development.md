# Phát triển ViGovBot

> Đây là môi trường tùy chọn dành cho sửa code và chạy test, không phải runtime
> web hiện hành. Dùng [Docker Compose](docker.md) cho web, Base/RAG/QLoRA và
> Ollama; chỉ tạo lại `.venv` khi cần phát triển hoặc chạy test trên host.

## Thiết lập

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[test,dev]"
.venv\Scripts\vigov doctor
```

Linux dùng `.venv/bin/python` và `.venv/bin/vigov`. CLI tự tìm project root từ
package đã cài, nên có thể gọi ngoài thư mục repository. Có thể đặt rõ
`VIGOVBOT_PROJECT_ROOT` khi dùng bản cài không editable.

## Gate trước khi gửi thay đổi

```powershell
.venv\Scripts\python -m unittest discover -s tests -v
.venv\Scripts\python -m ruff check .
.venv\Scripts\python -m compileall -q src tests
.venv\Scripts\python -m pip check
git diff --check
```

Repository không còn workflow CI tự động. Trước khi bàn giao thay đổi, chạy thủ
công các gate ở trên; test GPU phải được ghi riêng như artifact thực nghiệm.

Implementation canonical nằm trong `src/vigovbot`; QLoRA chỉ dùng namespace
`vigovbot.training`. PowerShell lifecycle cũ chỉ là compatibility entry point và
không chứa business logic training.
