"""
DMS Search

Query and filter DMS records in a directory by type, subject,
creator, language, date range, and free-text search.
"""

import json
from pathlib import Path
from datetime import date

from rich.console import Console
from rich.table import Table
from rich import box

console = Console()


def load_records(dir_path: str | Path) -> list[tuple[str, dict]]:
    """Load all valid DMS records from a directory.

    Returns:
        List of (filename, record_dict) tuples.
    """
    dir_path = Path(dir_path)
    results = []

    for jf in sorted(dir_path.glob("*.json")):
        try:
            with open(jf, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                results.append((jf.name, data))
            elif isinstance(data, list):
                for i, rec in enumerate(data):
                    if isinstance(rec, dict):
                        results.append((f"{jf.name}[{i}]", rec))
        except (json.JSONDecodeError, OSError):
            pass

    return results


def search_records(
    dir_path: str | Path,
    type_filter: str | None = None,
    subject_filter: str | None = None,
    creator_filter: str | None = None,
    language_filter: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    query: str | None = None,
) -> list[tuple[str, dict]]:
    """Search DMS records with multiple filter criteria.

    All filters are combined with AND logic.

    Args:
        dir_path: Directory to search.
        type_filter: Match records with this type.
        subject_filter: Match records containing this subject tag.
        creator_filter: Match records with this creator name (partial match).
        language_filter: Match records with this language code.
        date_from: Include records with created date >= this (YYYY-MM-DD).
        date_to: Include records with created date <= this (YYYY-MM-DD).
        query: Free-text search across title, description, and subjects.

    Returns:
        List of (filename, record) tuples that match all criteria.
    """
    records = load_records(dir_path)
    matches = []

    for filename, rec in records:
        # Type filter
        if type_filter and rec.get("type", "") != type_filter:
            continue

        # Language filter
        if language_filter and rec.get("language", "") != language_filter:
            continue

        # Subject filter
        if subject_filter:
            subjects = rec.get("subject", [])
            if not isinstance(subjects, list):
                subjects = []
            subject_lower = subject_filter.lower()
            if not any(subject_lower in s.lower() for s in subjects):
                continue

        # Creator filter
        if creator_filter:
            creators = rec.get("creator", [])
            if not isinstance(creators, list):
                creators = []
            creator_lower = creator_filter.lower()
            found = any(
                creator_lower in c.get("name", "").lower()
                for c in creators
                if isinstance(c, dict)
            )
            if not found:
                continue

        # Date range filter
        if date_from or date_to:
            date_info = rec.get("date", {})
            created = date_info.get("created", "") if isinstance(date_info, dict) else ""
            if created:
                try:
                    rec_date = date.fromisoformat(created)
                    if date_from and rec_date < date.fromisoformat(date_from):
                        continue
                    if date_to and rec_date > date.fromisoformat(date_to):
                        continue
                except ValueError:
                    continue
            else:
                continue  # No date, can't match date range

        # Free-text query
        if query:
            query_lower = query.lower()
            searchable = " ".join([
                rec.get("title", ""),
                rec.get("description", ""),
                " ".join(rec.get("subject", [])) if isinstance(rec.get("subject"), list) else "",
            ]).lower()
            if query_lower not in searchable:
                continue

        matches.append((filename, rec))

    return matches


def print_results(matches: list[tuple[str, dict]], show_description: bool = False) -> None:
    """Print search results as a formatted table."""
    if not matches:
        console.print("  [yellow]No records matched your search.[/yellow]")
        return

    table = Table(
        title=f"Search Results ({len(matches)} found)",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("File", style="white", min_width=16)
    table.add_column("Title", style="bold", min_width=20, max_width=40)
    table.add_column("Type", style="cyan", min_width=8)
    table.add_column("Language", justify="center", min_width=5)
    table.add_column("Creator", style="dim", min_width=16, max_width=30)

    for filename, rec in matches:
        creators = rec.get("creator", [])
        creator_str = ", ".join(
            c.get("name", "") for c in creators if isinstance(c, dict)
        ) if isinstance(creators, list) else ""

        table.add_row(
            filename,
            rec.get("title", "Untitled"),
            rec.get("type", "—"),
            rec.get("language", "—"),
            creator_str or "—",
        )

    console.print(table)

    if show_description:
        console.print()
        for filename, rec in matches:
            desc = rec.get("description", "")
            if desc:
                short = desc[:120] + "…" if len(desc) > 120 else desc
                console.print(f"  [bold]{filename}[/bold]: [dim]{short}[/dim]")
