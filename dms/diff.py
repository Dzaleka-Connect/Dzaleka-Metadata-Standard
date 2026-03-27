"""
DMS Diff

Compare two DMS records and show field-level differences.
Useful for tracking changes across schema versions or
auditing record edits.
"""

import json
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()


def diff_records(record_a: dict, record_b: dict) -> list[dict]:
    """Compare two DMS records field by field.

    Args:
        record_a: First record dict (the "before" state).
        record_b: Second record dict (the "after" state).

    Returns:
        List of diffs, each with keys: field, status, old, new.
        Status is one of: 'added', 'removed', 'changed', 'unchanged'.
    """
    all_keys = sorted(set(list(record_a.keys()) + list(record_b.keys())))
    diffs = []

    for key in all_keys:
        in_a = key in record_a
        in_b = key in record_b

        if in_a and not in_b:
            diffs.append({
                "field": key,
                "status": "removed",
                "old": record_a[key],
                "new": None,
            })
        elif not in_a and in_b:
            diffs.append({
                "field": key,
                "status": "added",
                "old": None,
                "new": record_b[key],
            })
        elif record_a[key] != record_b[key]:
            diffs.append({
                "field": key,
                "status": "changed",
                "old": record_a[key],
                "new": record_b[key],
            })
        else:
            diffs.append({
                "field": key,
                "status": "unchanged",
                "old": record_a[key],
                "new": record_b[key],
            })

    return diffs


def diff_files(path_a: str | Path, path_b: str | Path) -> list[dict]:
    """Load two JSON files and diff their records.

    Args:
        path_a: Path to first DMS JSON file.
        path_b: Path to second DMS JSON file.

    Returns:
        List of diffs (see diff_records).
    """
    with open(path_a, "r", encoding="utf-8") as f:
        record_a = json.load(f)
    with open(path_b, "r", encoding="utf-8") as f:
        record_b = json.load(f)

    if not isinstance(record_a, dict) or not isinstance(record_b, dict):
        raise ValueError("Both files must contain a single JSON object (not an array).")

    return diff_records(record_a, record_b)


def _fmt_value(val, max_len: int = 50) -> str:
    """Format a value for display, truncating long strings."""
    if val is None:
        return "—"
    if isinstance(val, str):
        return val[:max_len] + "…" if len(val) > max_len else val
    s = json.dumps(val, ensure_ascii=False)
    return s[:max_len] + "…" if len(s) > max_len else s


def print_diff(diffs: list[dict], path_a: str = "A", path_b: str = "B", show_unchanged: bool = False) -> None:
    """Print a formatted diff table to the console."""
    changes = [d for d in diffs if d["status"] != "unchanged"]
    unchanged = [d for d in diffs if d["status"] == "unchanged"]

    if not changes:
        console.print(Panel(
            "[green]Records are identical — no differences found.[/green]",
            box=box.ROUNDED,
            border_style="green",
        ))
        return

    # Status badges
    status_style = {
        "added": "[bold green]+added[/bold green]",
        "removed": "[bold red]−removed[/bold red]",
        "changed": "[bold yellow]~changed[/bold yellow]",
        "unchanged": "[dim]=[/dim]",
    }

    table = Table(
        title=f"Diff: {Path(path_a).name} ↔ {Path(path_b).name}",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Field", style="white", min_width=14)
    table.add_column("Status", justify="center", min_width=10)
    table.add_column(Path(path_a).name, style="red", min_width=20, max_width=45)
    table.add_column(Path(path_b).name, style="green", min_width=20, max_width=45)

    for d in changes:
        table.add_row(
            d["field"],
            status_style[d["status"]],
            _fmt_value(d["old"]),
            _fmt_value(d["new"]),
        )

    if show_unchanged and unchanged:
        for d in unchanged:
            table.add_row(
                d["field"],
                status_style["unchanged"],
                _fmt_value(d["old"]),
                _fmt_value(d["new"]),
            )

    console.print(table)

    # Summary
    added = sum(1 for d in diffs if d["status"] == "added")
    removed = sum(1 for d in diffs if d["status"] == "removed")
    changed = sum(1 for d in diffs if d["status"] == "changed")

    console.print(
        f"\n  [green]+{added} added[/green]  "
        f"[red]−{removed} removed[/red]  "
        f"[yellow]~{changed} changed[/yellow]  "
        f"[dim]={len(unchanged)} unchanged[/dim]"
    )
    console.print()
