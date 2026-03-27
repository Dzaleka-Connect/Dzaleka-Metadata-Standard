"""
DMS Record Generator

Interactive wizard for creating new DMS metadata records.
Uses Click prompts and Rich formatting for a pleasant CLI experience.
"""

import json
import uuid
from datetime import date
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from dms.schema import (
    get_type_enum,
    get_creator_roles,
    get_access_levels,
    get_schema_version,
)

console = Console()


def generate_record(output_path: str | Path | None = None, preset_type: str | None = None) -> dict:
    """Run an interactive wizard to generate a new DMS metadata record.

    Args:
        output_path: Optional file path to write the record to.
        preset_type: If provided, skip the type selection prompt and use this value.

    Returns:
        The generated record as a dict.
    """
    console.print(Panel(
        "[bold]DMS Record Generator[/bold]\n"
        "Create a new Dzaleka Metadata Standard record.\n"
        "Press Ctrl+C to cancel at any time.",
        box=box.DOUBLE,
        border_style="bright_blue",
    ))

    record = {}

    # --- ID (auto-generated) ---
    record["id"] = str(uuid.uuid4())
    console.print(f"  [dim]Generated ID:[/dim] {record['id']}")

    # --- Schema version ---
    record["schema_version"] = get_schema_version()

    # --- Title (required) ---
    record["title"] = click.prompt(
        click.style("  Title", fg="cyan"),
        type=str,
    ).strip()

    # --- Type (required) ---
    types = get_type_enum()
    if preset_type and preset_type in types:
        record["type"] = preset_type
        console.print(f"  [dim]Type (preset):[/dim] {preset_type}")
    else:
        if preset_type:
            console.print(f"  [yellow]Unknown type '{preset_type}', please select:[/yellow]")
        console.print(f"  [dim]Available types: {', '.join(types)}[/dim]")
        record["type"] = click.prompt(
            click.style("  Type", fg="cyan"),
            type=click.Choice(types, case_sensitive=False),
        )

    # --- Description (required) ---
    record["description"] = click.prompt(
        click.style("  Description", fg="cyan"),
        type=str,
    ).strip()

    # --- Language (required) ---
    record["language"] = click.prompt(
        click.style("  Language code (e.g., en, sw, fr, rw)", fg="cyan"),
        type=str,
        default="en",
    ).strip().lower()

    # --- Creator (recommended) ---
    if click.confirm(click.style("  Add creator(s)?", fg="yellow"), default=True):
        creators = []
        while True:
            creator = {}
            creator["name"] = click.prompt(
                click.style("    Creator name", fg="cyan"),
                type=str,
            ).strip()

            roles = get_creator_roles()
            console.print(f"    [dim]Available roles: {', '.join(roles)}[/dim]")
            role = click.prompt(
                click.style("    Role (leave blank to skip)", fg="cyan"),
                type=str,
                default="",
            ).strip().lower()
            if role and role in roles:
                creator["role"] = role

            affiliation = click.prompt(
                click.style("    Affiliation (leave blank to skip)", fg="cyan"),
                type=str,
                default="",
            ).strip()
            if affiliation:
                creator["affiliation"] = affiliation

            creators.append(creator)

            if not click.confirm(click.style("    Add another creator?", fg="yellow"), default=False):
                break
        record["creator"] = creators

    # --- Date ---
    record["date"] = {
        "created": date.today().isoformat(),
    }
    event_date = click.prompt(
        click.style("  Event/original date (YYYY-MM-DD, leave blank to skip)", fg="cyan"),
        type=str,
        default="",
    ).strip()
    if event_date:
        record["date"]["event_date"] = event_date

    # --- Subject/Tags ---
    tags_input = click.prompt(
        click.style("  Tags/keywords (comma-separated, leave blank to skip)", fg="cyan"),
        type=str,
        default="",
    ).strip()
    if tags_input:
        record["subject"] = [t.strip() for t in tags_input.split(",") if t.strip()]

    # --- Location ---
    if click.confirm(click.style("  Add location?", fg="yellow"), default=True):
        location = {}
        location["name"] = click.prompt(
            click.style("    Location name", fg="cyan"),
            type=str,
            default="Dzaleka Refugee Camp",
        ).strip()

        area = click.prompt(
            click.style("    Area/section (leave blank to skip)", fg="cyan"),
            type=str,
            default="",
        ).strip()
        if area:
            location["area"] = area

        if click.confirm(click.style("    Add coordinates?", fg="yellow"), default=False):
            location["latitude"] = click.prompt(
                click.style("    Latitude", fg="cyan"),
                type=float,
                default=-13.7833,
            )
            location["longitude"] = click.prompt(
                click.style("    Longitude", fg="cyan"),
                type=float,
                default=33.9833,
            )

        record["location"] = location

    # --- Format ---
    fmt = click.prompt(
        click.style("  MIME type (e.g., image/jpeg, audio/mpeg — leave blank to skip)", fg="cyan"),
        type=str,
        default="",
    ).strip()
    if fmt:
        record["format"] = fmt

    # --- Rights ---
    if click.confirm(click.style("  Add rights/licensing info?", fg="yellow"), default=True):
        rights = {}
        license_id = click.prompt(
            click.style("    License (e.g., CC-BY-4.0)", fg="cyan"),
            type=str,
            default="CC-BY-4.0",
        ).strip()
        if license_id:
            rights["license"] = license_id

        levels = get_access_levels()
        console.print(f"    [dim]Access levels: {', '.join(levels)}[/dim]")
        access = click.prompt(
            click.style("    Access level", fg="cyan"),
            type=click.Choice(levels, case_sensitive=False),
            default="public",
        )
        rights["access_level"] = access

        holder = click.prompt(
            click.style("    Rights holder (leave blank to skip)", fg="cyan"),
            type=str,
            default="",
        ).strip()
        if holder:
            rights["holder"] = holder

        record["rights"] = rights

    # --- Source ---
    if click.confirm(click.style("  Add source/provenance info?", fg="yellow"), default=False):
        source = {}
        contributor = click.prompt(
            click.style("    Contributor name", fg="cyan"),
            type=str,
            default="",
        ).strip()
        if contributor:
            source["contributor"] = contributor

        collection = click.prompt(
            click.style("    Collection name", fg="cyan"),
            type=str,
            default="",
        ).strip()
        if collection:
            source["collection"] = collection

        orig_format = click.prompt(
            click.style("    Original format (e.g., 'handwritten notebook')", fg="cyan"),
            type=str,
            default="",
        ).strip()
        if orig_format:
            source["original_format"] = orig_format

        if source:
            record["source"] = source

    # --- Output ---
    record_json = json.dumps(record, indent=2, ensure_ascii=False)

    console.print()
    console.print(Panel(
        record_json,
        title="[bold green]Generated DMS Record[/bold green]",
        box=box.ROUNDED,
        border_style="green",
    ))

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(record_json + "\n")
        console.print(f"\n  [green]✓ Saved to {output_path}[/green]")
    else:
        # Default: write to current directory
        suggested = f"{record['type']}_{record['id'][:8]}.json"
        if click.confirm(click.style(f"  Save to ./{suggested}?", fg="yellow"), default=True):
            with open(suggested, "w", encoding="utf-8") as f:
                f.write(record_json + "\n")
            console.print(f"\n  [green]✓ Saved to {suggested}[/green]")

    return record
