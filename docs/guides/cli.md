# Tham chiếu CLI `vigov`

Cài editable một lần bằng `python -m pip install -e .`, sau đó có thể gọi
`vigov` từ bất kỳ thư mục làm việc nào. Dùng `vigov <nhóm> --help` để xem option.

## Web và hỏi đáp

```powershell
vigov web
vigov web --host 127.0.0.1 --port 8000
vigov ask "Hồ sơ gồm những gì?"
vigov ask "Còn lệ phí?" --history history.json
```

## Dữ liệu và corpus

```powershell
vigov data ingest
vigov data ingest one.pdf --workers 1
vigov data embed
vigov data embed outputs/metadata --output-dir Data/vector/unified-new
vigov data check
vigov data stats
```

`data embed` mặc định đọc `outputs/metadata` và ghi `Data/vector/unified`. Lệnh
từ chối ghi đè corpus hiện có theo logic embedding hiện hành.

## RAG

```powershell
vigov rag prepare
vigov rag smoke
vigov rag evaluate
vigov rag report
vigov rag run
```

`prepare` dùng cấu hình inference; bốn lệnh đánh giá dùng
`configs/rag/evaluation.yaml` mặc định. Truyền `--config` để chọn profile khác.

## GPU và QLoRA

```powershell
vigov gpu check
vigov train smoke --approve
vigov train start --config configs/training/environments/rtx5060ti_16gb.yaml --dry-run
vigov train status
vigov train logs --lines 100
vigov train logs --follow
vigov train stop
vigov train resume <checkpoint> --config <same-config>
vigov dashboard --run-id <run-id>
```

`--dry-run` không tạo training process. GPU smoke chỉ chạy thật khi có
`--approve`.

## Đánh giá và báo cáo QLoRA

```powershell
vigov eval test --run-id <run-id>
vigov report plots --run-id <run-id>
vigov report build --run-id <run-id>
```

Các entry point `python -m vigovbot ingest|embed|rag|qa-v4` vẫn tồn tại để chạy
script cũ, nhưng luồng vận hành thông thường nên dùng `vigov`.
