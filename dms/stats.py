"""
DMS Stats

Generate statistics and summaries for a collection of DMS records.
"""

import json
from pathlib import Path
from collections import Counter

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()


def gather_stats(dir_path: str | Path) -> dict:
    """Scan a directory of DMS JSON files and compute collection statistics.

    Args:
        dir_path: Directory containing DMS JSON files.

    Returns:
        Dict with keys: total, valid, by_type, by_language, by_access_level,
        creators, subjects_top, missing_fields.
    """
    dir_path = Path(dir_path)
    json_files = sorted(dir_path.glob("*.json"))

    stats = {
        "total": 0,
        "valid": 0,
        "invalid": 0,
        "by_type": Counter(),
        "by_language": Counter(),
        "by_access_level": Counter(),
        "creators": Counter(),
        "subjects_top": Counter(),
        "missing_fields": Counter(),
        "files": [],
    }

    recommended_fields = ["creator", "date", "subject", "location", "rights"]

    for jf in json_files:
        try:
            with open(jf, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            stats["invalid"] += 1
            stats["total"] += 1
            continue

        records = [data] if isinstance(data, dict) else data if isinstance(data, list) else []

        for rec in records:
            if not isinstance(rec, dict):
                continue

            stats["total"] += 1

            # Type
            t = rec.get("type", "unknown")
            stats["by_type"][t] += 1

            # Language
            lang = rec.get("language", "unknown")
            stats["by_language"][lang] += 1

            # Access level
            rights = rec.get("rights", {})
            if isinstance(rights, dict):
                access = rights.get("access_level", "unspecified")
            else:
                access = "unspecified"
            stats["by_access_level"][access] += 1

            # Creators
            creators = rec.get("creator", [])
            if isinstance(creators, list):
                for c in creators:
                    if isinstance(c, dict) and "name" in c:
                        stats["creators"][c["name"]] += 1

            # Subjects
            subjects = rec.get("subject", [])
            if isinstance(subjects, list):
                for s in subjects:
                    stats["subjects_top"][s] += 1

            # Missing recommended fields
            for field in recommended_fields:
                if field not in rec:
                    stats["missing_fields"][field] += 1

            # Check validity (basic: has required fields)
            required = {"id", "title", "type", "description", "language"}
            if required.issubset(rec.keys()):
                stats["valid"] += 1
            else:
                stats["invalid"] += 1

            stats["files"].append({
                "file": jf.name,
                "title": rec.get("title", "Untitled"),
                "type": t,
            })

    return stats


def print_stats(stats: dict) -> None:
    """Print a formatted statistics report to the console."""

    # Header
    console.print()
    console.print(Panel(
        f"[bold bright_blue]Collection Statistics[/bold bright_blue]\n\n"
        f"  Total records:   [cyan]{stats['total']}[/cyan]\n"
        f"  Valid:           [green]{stats['valid']}[/green]\n"
        f"  Invalid:         [red]{stats['invalid']}[/red]",
        box=box.DOUBLE,
        border_style="bright_blue",
    ))

    # By type
    if stats["by_type"]:
        table = Table(
            title="Records by Type",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Type", style="white", min_width=12)
        table.add_column("Count", justify="right", style="cyan", min_width=8)
        table.add_column("Bar", style="green")

        max_count = max(stats["by_type"].values()) if stats["by_type"] else 1
        for t, count in stats["by_type"].most_common():
            bar = "█" * int(20 * count / max_count)
            table.add_row(t, str(count), bar)
        console.print(table)

    # By language
    if stats["by_language"]:
        table = Table(
            title="Records by Language",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Language", style="white", min_width=12)
        table.add_column("Count", justify="right", style="cyan", min_width=8)
        for lang, count in stats["by_language"].most_common():
            table.add_row(lang, str(count))
        console.print(table)

    # By access level
    if stats["by_access_level"]:
        table = Table(
            title="Records by Access Level",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Access Level", style="white", min_width=14)
        table.add_column("Count", justify="right", style="cyan", min_width=8)
        for level, count in stats["by_access_level"].most_common():
            table.add_row(level, str(count))
        console.print(table)

    # Top subjects
    if stats["subjects_top"]:
        table = Table(
            title="Top 15 Subjects",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Subject", style="white", min_width=20)
        table.add_column("Count", justify="right", style="cyan", min_width=8)
        for subj, count in stats["subjects_top"].most_common(15):
            table.add_row(subj, str(count))
        console.print(table)

    # Top creators
    if stats["creators"]:
        table = Table(
            title="Contributors",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Creator", style="white", min_width=20)
        table.add_column("Records", justify="right", style="cyan", min_width=8)
        for creator, count in stats["creators"].most_common(10):
            table.add_row(creator, str(count))
        console.print(table)

    # Missing fields heatmap
    if stats["missing_fields"]:
        console.print()
        console.print("[bold]Missing Recommended Fields:[/bold]")
        for field, count in stats["missing_fields"].most_common():
            pct = int(100 * count / stats["total"]) if stats["total"] else 0
            bar = "░" * int(20 * count / stats["total"]) if stats["total"] else ""
            console.print(f"  [yellow]{field:>12}[/yellow]  {count}/{stats['total']} ({pct}%)  {bar}")

    console.print()
