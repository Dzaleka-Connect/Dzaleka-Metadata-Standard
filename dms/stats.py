"""
DMS Stats

Generate statistics and summaries for a collection of DMS records.
"""

import json
from pathlib import Path
from collections import Counter

from dms.style import console, heading, make_table


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

    heading("Collection")
    console.print(f"  [dim]Records[/dim]   {stats['total']}")
    console.print(f"  [dim]Valid[/dim]     [green]{stats['valid']}[/green]")
    console.print(f"  [dim]Invalid[/dim]   [red]{stats['invalid']}[/red]")
    console.print()

    def _count_table(title: str, counter, columns: tuple[str, str]) -> None:
        table = make_table(title)
        table.add_column(columns[0], min_width=12)
        table.add_column(columns[1], justify="right", min_width=8)
        if title == "Type":
            table.add_column("", style="green")
            max_count = max(counter.values()) if counter else 1
            for name, count in counter.most_common():
                table.add_row(str(name), str(count), "█" * int(20 * count / max_count))
        else:
            for name, count in counter.most_common():
                table.add_row(str(name), str(count))
        console.print(table)

    if stats["by_type"]:
        _count_table("Type", stats["by_type"], ("Type", "Count"))
    if stats["by_language"]:
        _count_table("Language", stats["by_language"], ("Language", "Count"))
    if stats["by_access_level"]:
        _count_table("Access", stats["by_access_level"], ("Access level", "Count"))
    if stats["subjects_top"]:
        table = make_table("Subjects")
        table.add_column("Subject", min_width=20)
        table.add_column("Count", justify="right", min_width=8)
        for subj, count in stats["subjects_top"].most_common(15):
            table.add_row(subj, str(count))
        console.print(table)
    if stats["creators"]:
        table = make_table("Contributors")
        table.add_column("Creator", min_width=20)
        table.add_column("Records", justify="right", min_width=8)
        for creator, count in stats["creators"].most_common(10):
            table.add_row(creator, str(count))
        console.print(table)

    if stats["missing_fields"]:
        console.print()
        console.print("  [bold]Missing recommended fields[/bold]")
        for field, count in stats["missing_fields"].most_common():
            pct = int(100 * count / stats["total"]) if stats["total"] else 0
            bar = "·" * int(20 * count / stats["total"]) if stats["total"] else ""
            console.print(f"  [dim]{field:>12}[/dim]  {count}/{stats['total']} ({pct}%)  {bar}")

    console.print()
