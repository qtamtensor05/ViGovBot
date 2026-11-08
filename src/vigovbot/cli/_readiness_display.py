"""Rich-formatted display for web-readiness preflight reports."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


_STATUS_ICON = {"PASS": "✔", "WARN": "⚠", "FAIL": "✘"}
_STATUS_STYLE = {"PASS": "bold green", "WARN": "bold yellow", "FAIL": "bold red"}
_STATUS_LABEL = {"PASS": "PASS", "WARN": "WARN", "FAIL": "FAIL"}

# Overall banner colours
_BANNER_PASS = "bold white on green"
_BANNER_FAIL = "bold white on red"
_BANNER_WARN = "bold white on dark_orange"

# Separator width
_WIDTH = 70


def _status_text(status: str):
    from rich.text import Text

    icon = _STATUS_ICON.get(status, "?")
    style = _STATUS_STYLE.get(status, "")
    t = Text()
    t.append(f" {icon} {_STATUS_LABEL.get(status, status)} ", style=style)
    return t


def print_readiness_report(report: dict) -> None:
    """Render *report* as a human-readable Rich panel to stdout."""
    from rich.console import Console
    from rich.padding import Padding
    from rich.rule import Rule
    from rich.table import Table
    from rich.text import Text

    console = Console(highlight=False)

    # ── header ────────────────────────────────────────────────────────────
    console.print()
    console.rule("[bold]Kiểm tra sẵn sàng trước khi chạy web[/bold]", style="bright_blue")

    # meta info
    meta = Table.grid(padding=(0, 1))
    meta.add_column(style="dim", min_width=14)
    meta.add_column()
    meta.add_row("Cấu hình", f"[cyan]{report.get('config', '?')}[/cyan]")
    meta.add_row("Địa chỉ web", f"[cyan]{report.get('web', '?')}[/cyan]")
    console.print(Padding(meta, (1, 0, 0, 2)))

    # ── checks table ──────────────────────────────────────────────────────
    console.print()
    table = Table(
        show_header=True,
        header_style="bold dim",
        box=None,
        padding=(0, 1),
        expand=False,
    )
    table.add_column("Trạng thái", width=8, justify="center")
    table.add_column("Loại", style="dim", width=10)
    table.add_column("Kiểm tra", min_width=22)
    table.add_column("Chi tiết")

    checks = report.get("checks", [])
    for item in checks:
        status = item.get("status", "?")
        required = item.get("required", True)
        name = item.get("name", "")
        detail = item.get("detail", "")

        kind_label = Text("bắt buộc" if required else "tùy chọn", style="dim")
        detail_text = Text(detail, style="default")
        if status == "FAIL":
            detail_text.stylize("red")
        elif status == "WARN":
            detail_text.stylize("yellow")
        else:
            detail_text.stylize("dim")

        table.add_row(_status_text(status), kind_label, Text(name), detail_text)

    console.print(Padding(table, (0, 0, 0, 2)))

    # ── summary banner ────────────────────────────────────────────────────
    console.print()
    overall = report.get("status", "FAIL")
    failures = report.get("required_failures", 0)
    warnings = report.get("warnings", 0)

    if overall == "PASS" and warnings == 0:
        banner_style = _BANNER_PASS
        banner_text = "  ✔  Tất cả kiểm tra bắt buộc đạt — sẵn sàng khởi động web  "
    elif overall == "PASS":
        banner_style = _BANNER_WARN
        banner_text = f"  ⚠  Đạt với {warnings} cảnh báo — web sẽ khởi động, một số tính năng có thể chưa đủ  "
    else:
        banner_style = _BANNER_FAIL
        banner_text = f"  ✘  {failures} lỗi bắt buộc — web không thể khởi động  "

    console.print(Padding(Text(banner_text, style=banner_style), (0, 0, 0, 2)))

    # hint for failures
    if overall != "PASS":
        console.print()
        console.print(
            Padding(
                "[dim]Xem hướng dẫn khắc phục: [cyan]docs/guides/web-readiness.md[/cyan][/dim]",
                (0, 0, 1, 2),
            )
        )
    else:
        console.print()
