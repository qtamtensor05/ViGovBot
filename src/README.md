# Bố cục mã nguồn

Mã nguồn được triển khai trong package duy nhất [vigovbot](vigovbot/).
Cài package bằng `python -m pip install -e ".[rag,evaluation]"`, sau đó dùng
namespace `vigovbot.*` và CLI `python -m vigovbot`.

Module riêng cho bộ QA v4: [vigovbot.qa_v4](vigovbot/qa_v4/README.md),
chạy chat và đánh giá bằng `python -m vigovbot qa-v4`.

[Kiến trúc hệ thống](../docs/architecture.md) · [Giao diện CLI](../README.md) · [Migration](../docs/migration.md)
