# Bố cục mã nguồn

Mã nguồn được triển khai trong package duy nhất [vigovbot](vigovbot/).
Cài package bằng `python -m pip install -e ".[rag,evaluation]"`, sau đó dùng
namespace `vigovbot.*` và CLI `python -m vigovbot`.

Evaluation và benchmark QA v4 thống nhất tại
[vigovbot.evaluation](vigovbot/evaluation/README.md), chạy bằng
`python -m vigovbot eva`.

[Kiến trúc hệ thống](../docs/architecture/architecture.md) · [Giao diện CLI](../README.md) · [Migration](../docs/architecture/migration.md)
