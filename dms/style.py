"""Shared visual language for DMS command-line output."""

from rich import box
from rich.console import Console
from rich.table import Table

console = Console()


def make_table(title: str | None = None) -> Table:
    """Return a quiet table that reads more like a document than a dashboard."""
    return Table(
        title=title,
        box=box.SIMPLE,
        show_header=True,
        header_style="bold",
        pad_edge=False,
        border_style="dim",
        title_style="bold",
        expand=False,
    )


def heading(title: str, detail: str = "") -> None:
    console.print()
    if detail:
        console.print(f"  [bold]{title}[/bold]  [dim]{detail}[/dim]")
    else:
        console.print(f"  [bold]{title}[/bold]")
    console.print()
