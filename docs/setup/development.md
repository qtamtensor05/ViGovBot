# Phát triển ViGovBot

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
.venv\Scripts\python -m compileall -q src training tests
.venv\Scripts\python -m pip check
git diff --check
```

CI chạy cùng unit/integration/static gate trên Windows và Ubuntu, không tải Qwen
và không chạy GPU training. Test GPU phải được ghi riêng như artifact thực nghiệm.

Implementation canonical nằm trong `src/vigovbot`. Namespace `training.*`, YAML
cấp gốc và PowerShell lifecycle cũ chỉ là compatibility layer; không thêm business
logic mới vào các shim này.
