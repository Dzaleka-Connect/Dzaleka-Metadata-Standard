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
    get_consent_statuses,
    get_sensitivity_values,
    get_relation_types,
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

            identifier = click.prompt(
                click.style("    Creator identifier (leave blank to skip)", fg="cyan"),
                type=str,
                default="",
            ).strip()
            if identifier:
                creator["identifier"] = identifier

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

    if click.confirm(click.style("  Add structured subject references?", fg="yellow"), default=False):
        subject_refs = []
        while True:
            subject_ref = {}
            identifier = click.prompt(
                click.style("    Subject identifier", fg="cyan"),
                type=str,
            ).strip()
            subject_ref["identifier"] = identifier

            label = click.prompt(
                click.style("    Subject label (leave blank to skip)", fg="cyan"),
                type=str,
                default="",
            ).strip()
            if label:
                subject_ref["label"] = label

            scheme = click.prompt(
                click.style("    Scheme name (leave blank to skip)", fg="cyan"),
                type=str,
                default="",
            ).strip()
            if scheme:
                subject_ref["scheme"] = scheme

            subject_refs.append(subject_ref)
            if not click.confirm(click.style("    Add another subject reference?", fg="yellow"), default=False):
                break

        if subject_refs:
            record["subject_ref"] = subject_refs

    # --- Location ---
    if click.confirm(click.style("  Add location?", fg="yellow"), default=True):
        location = {}
        location["name"] = click.prompt(
            click.style("    Location name", fg="cyan"),
            type=str,
            default="Dzaleka Refugee Camp",
        ).strip()

        identifier = click.prompt(
            click.style("    Location identifier (leave blank to skip)", fg="cyan"),
            type=str,
            default="",
        ).strip()
        if identifier:
            location["identifier"] = identifier

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

        consent_statuses = get_consent_statuses()
        console.print(f"    [dim]Consent statuses: {', '.join(consent_statuses)}[/dim]")
        consent_status = click.prompt(
            click.style("    Consent status (leave blank to skip)", fg="cyan"),
            type=str,
            default="",
        ).strip().lower()
        if consent_status and consent_status in consent_statuses:
            rights["consent_status"] = consent_status

        sensitivity_values = get_sensitivity_values()
        console.print(f"    [dim]Sensitivity values: {', '.join(sensitivity_values)}[/dim]")
        sensitivities = click.prompt(
            click.style("    Sensitivity tags (comma-separated, leave blank to skip)", fg="cyan"),
            type=str,
            default="",
        ).strip()
        if sensitivities:
            selected = [s.strip().lower() for s in sensitivities.split(",") if s.strip()]
            valid = [s for s in selected if s in sensitivity_values]
            if valid:
                rights["sensitivity"] = valid

        holder = click.prompt(
            click.style("    Rights holder (leave blank to skip)", fg="cyan"),
            type=str,
            default="",
        ).strip()
        if holder:
            rights["holder"] = holder

        access_note = click.prompt(
            click.style("    Access note (leave blank to skip)", fg="cyan"),
            type=str,
            default="",
        ).strip()
        if access_note:
            rights["access_note"] = access_note

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

        collection_identifier = click.prompt(
            click.style("    Collection identifier (leave blank to skip)", fg="cyan"),
            type=str,
            default="",
        ).strip()
        if collection_identifier:
            source["collection_identifier"] = collection_identifier

        orig_format = click.prompt(
            click.style("    Original format (e.g., 'handwritten notebook')", fg="cyan"),
            type=str,
            default="",
        ).strip()
        if orig_format:
            source["original_format"] = orig_format

        if source:
            record["source"] = source

    # --- Technical metadata ---
    if click.confirm(click.style("  Add technical file metadata?", fg="yellow"), default=False):
        technical = {}
        file_uri = click.prompt(
            click.style("    File URI (leave blank to skip)", fg="cyan"),
            type=str,
            default="",
        ).strip()
        if file_uri:
            technical["file_uri"] = file_uri

        filename = click.prompt(
            click.style("    Filename (leave blank to skip)", fg="cyan"),
            type=str,
            default="",
        ).strip()
        if filename:
            technical["filename"] = filename

        checksum = click.prompt(
            click.style("    Checksum (leave blank to skip)", fg="cyan"),
            type=str,
            default="",
        ).strip()
        if checksum:
            technical["checksum"] = checksum

        checksum_algorithm = click.prompt(
            click.style("    Checksum algorithm (leave blank to skip)", fg="cyan"),
            type=str,
            default="",
        ).strip().lower()
        if checksum_algorithm:
            technical["checksum_algorithm"] = checksum_algorithm

        file_size_bytes = click.prompt(
            click.style("    File size in bytes (leave blank to skip)", fg="cyan"),
            type=str,
            default="",
        ).strip()
        if file_size_bytes:
            technical["file_size_bytes"] = int(file_size_bytes)

        duration_seconds = click.prompt(
            click.style("    Duration in seconds (leave blank to skip)", fg="cyan"),
            type=str,
            default="",
        ).strip()
        if duration_seconds:
            technical["duration_seconds"] = float(duration_seconds)

        page_count = click.prompt(
            click.style("    Page count (leave blank to skip)", fg="cyan"),
            type=str,
            default="",
        ).strip()
        if page_count:
            technical["page_count"] = int(page_count)

        width_px = click.prompt(
            click.style("    Width in pixels (leave blank to skip)", fg="cyan"),
            type=str,
            default="",
        ).strip()
        if width_px:
            technical["width_px"] = int(width_px)

        height_px = click.prompt(
            click.style("    Height in pixels (leave blank to skip)", fg="cyan"),
            type=str,
            default="",
        ).strip()
        if height_px:
            technical["height_px"] = int(height_px)

        if technical:
            record["technical"] = technical

    # --- Typed relations ---
    if click.confirm(click.style("  Add typed relations?", fg="yellow"), default=False):
        relation_types = get_relation_types()
        relation_details = []
        console.print(f"  [dim]Relation types: {', '.join(relation_types)}[/dim]")
        while True:
            relation_detail = {}
            relation_detail["target"] = click.prompt(
                click.style("    Related record or resource identifier", fg="cyan"),
                type=str,
            ).strip()
            relation_type = click.prompt(
                click.style("    Relation type", fg="cyan"),
                type=click.Choice(relation_types, case_sensitive=False),
            )
            relation_detail["relation_type"] = relation_type

            label = click.prompt(
                click.style("    Label (leave blank to skip)", fg="cyan"),
                type=str,
                default="",
            ).strip()
            if label:
                relation_detail["label"] = label

            note = click.prompt(
                click.style("    Note (leave blank to skip)", fg="cyan"),
                type=str,
                default="",
            ).strip()
            if note:
                relation_detail["note"] = note

            relation_details.append(relation_detail)
            if not click.confirm(click.style("    Add another typed relation?", fg="yellow"), default=False):
                break

        if relation_details:
            record["relation_detail"] = relation_details

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
