"""
DMS Command-Line Interface

Usage:
    dms init [--type TYPE] [--output FILE]   Create a new DMS record interactively
    dms validate FILE                        Validate a JSON file against the DMS schema
    dms validate --dir DIRECTORY             Validate all JSON files in a directory
    dms convert csv2json FILE                Convert CSV to JSON records
    dms convert json2csv FILE                Convert JSON record(s) to CSV
    dms export FILE                          Export a record as JSON-LD
    dms export --dir DIRECTORY               Export all records as a JSON-LD graph
    dms search --dir DIR [FILTERS]           Search records by type, subject, creator, etc.
    dms diff FILE_A FILE_B                   Compare two records field by field
    dms report --dir DIR [--format html|md]  Generate a browsable catalogue
    dms stats --dir DIRECTORY                Show collection statistics
    dms info                                 Show schema version and field summary
"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from dms import __version__, __schema_version__

console = Console()


@click.group()
@click.version_option(__version__, prog_name="dms")
def main():
    """Dzaleka Metadata Standard — CLI tools for heritage metadata."""
    pass


# ─── init ────────────────────────────────────────────────────────────────────

@main.command()
@click.option("-o", "--output", type=click.Path(), default=None, help="Output file path for the generated record.")
@click.option("-t", "--type", "record_type", type=str, default=None, help="Pre-set the heritage type (e.g., poem, site, story).")
def init(output, record_type):
    """Create a new DMS metadata record interactively.

    Use --type to skip the type selection prompt:

        dms init --type poem
        dms init --type site --output mysite.json
    """
    from dms.generator import generate_record
    try:
        generate_record(output_path=output, preset_type=record_type)
    except click.Abort:
        console.print("\n[yellow]Cancelled.[/yellow]")


# ─── validate ────────────────────────────────────────────────────────────────

@main.command()
@click.argument("file", required=False, type=click.Path(exists=False))
@click.option("-d", "--dir", "directory", type=click.Path(exists=True, file_okay=False), help="Validate all .json files in a directory.")
def validate(file, directory):
    """Validate a DMS record against the schema.

    Provide a FILE path to validate a single record, or use --dir to validate
    all .json files in a directory.
    """
    import json
    from dms.validator import (
        validate_file,
        validate_directory,
        get_warnings,
        print_validation_result,
        print_batch_summary,
    )

    if directory:
        result = validate_directory(directory)
        for r in result["results"]:
            filepath = f"{directory}/{r['file']}"
            if r["valid"]:
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        rec = json.load(f)
                    warnings = get_warnings(rec)
                except Exception:
                    warnings = []
                print_validation_result(filepath, True, [], warnings)
            else:
                print_validation_result(filepath, False, r["errors"])
        print_batch_summary(result)

        # Exit with non-zero code if any records are invalid
        if result.get("invalid", 0) > 0:
            raise SystemExit(1)

    elif file:
        is_valid, errors = validate_file(file)
        warnings = []
        if is_valid:
            try:
                with open(file, "r", encoding="utf-8") as f:
                    rec = json.load(f)
                warnings = get_warnings(rec)
            except Exception:
                pass
        print_validation_result(file, is_valid, errors, warnings)
        if not is_valid:
            raise SystemExit(1)
    else:
        console.print("[red]Error: Provide a FILE path or use --dir to validate a directory.[/red]")
        raise SystemExit(1)


# ─── convert ─────────────────────────────────────────────────────────────────

@main.group()
def convert():
    """Convert between CSV and JSON formats."""
    pass


@convert.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("-o", "--output", type=click.Path(), default=None, help="Output file or directory path.")
def csv2json(file, output):
    """Convert a CSV file to DMS JSON record(s).

    By default, outputs to FILE_converted.json to avoid overwriting
    existing JSON files.
    """
    from dms.converter import csv_to_json

    if output is None:
        from pathlib import Path
        stem = Path(file).stem
        parent = Path(file).parent
        output = parent / f"{stem}_converted.json"

    records = csv_to_json(file, output)
    console.print(f"  [dim]{len(records)} record(s) written to {output}[/dim]")


@convert.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("-o", "--output", type=click.Path(), default=None, help="Output CSV file path.")
def json2csv(file, output):
    """Convert DMS JSON record(s) to CSV format."""
    from dms.converter import json_to_csv

    if output is None:
        from pathlib import Path
        output = Path(file).with_suffix(".csv")

    json_to_csv(file, output)
    console.print(f"  [dim]Written to {output}[/dim]")


# ─── export ──────────────────────────────────────────────────────────────────

@main.command("export")
@click.argument("file", required=False, type=click.Path(exists=True))
@click.option("-d", "--dir", "directory", type=click.Path(exists=True, file_okay=False), help="Export all .json files in a directory as a JSON-LD graph.")
@click.option("-o", "--output", type=click.Path(), default=None, help="Output JSON-LD file path.")
def export_cmd(file, directory, output):
    """Export DMS record(s) as JSON-LD for linked data publishing.

    Provide a FILE to export a single record, or use --dir to export
    all records in a directory as a @graph document.
    """
    from dms.exporter import export_jsonld, export_dir_jsonld

    if directory:
        if output is None:
            from pathlib import Path
            output = Path(directory) / "collection.jsonld"
        export_dir_jsonld(directory, output)
        console.print(f"  [dim]Written to {output}[/dim]")

    elif file:
        if output is None:
            from pathlib import Path
            output = Path(file).with_suffix(".jsonld")
        export_jsonld(file, output)
        console.print(f"  [dim]Written to {output}[/dim]")

    else:
        console.print("[red]Error: Provide a FILE path or use --dir to export a directory.[/red]")
        raise SystemExit(1)


# ─── search ──────────────────────────────────────────────────────────────────

@main.command()
@click.option("-d", "--dir", "directory", type=click.Path(exists=True, file_okay=False), required=True, help="Directory of DMS records to search.")
@click.option("-t", "--type", "type_filter", type=str, default=None, help="Filter by heritage type (e.g., poem, story, photo).")
@click.option("-s", "--subject", "subject_filter", type=str, default=None, help="Filter by subject tag (partial match).")
@click.option("-c", "--creator", "creator_filter", type=str, default=None, help="Filter by creator name (partial match).")
@click.option("-l", "--language", "language_filter", type=str, default=None, help="Filter by language code (e.g., en, sw).")
@click.option("--from", "date_from", type=str, default=None, help="Include records created on or after this date (YYYY-MM-DD).")
@click.option("--to", "date_to", type=str, default=None, help="Include records created on or before this date (YYYY-MM-DD).")
@click.option("-q", "--query", type=str, default=None, help="Free-text search across title, description, and subjects.")
@click.option("--verbose", is_flag=True, default=False, help="Show descriptions in results.")
def search(directory, type_filter, subject_filter, creator_filter, language_filter, date_from, date_to, query, verbose):
    """Search and filter DMS records.

    Examples:

        dms search --dir records/ --type poem

        dms search --dir records/ --subject "displacement" --language en

        dms search --dir records/ --creator "Espérance" --verbose

        dms search --dir records/ -q "refugee" --from 2024-01-01
    """
    from dms.search import search_records, print_results

    matches = search_records(
        directory,
        type_filter=type_filter,
        subject_filter=subject_filter,
        creator_filter=creator_filter,
        language_filter=language_filter,
        date_from=date_from,
        date_to=date_to,
        query=query,
    )
    print_results(matches, show_description=verbose)


# ─── diff ────────────────────────────────────────────────────────────────────

@main.command()
@click.argument("file_a", type=click.Path(exists=True))
@click.argument("file_b", type=click.Path(exists=True))
@click.option("-a", "--all", "show_all", is_flag=True, default=False, help="Show unchanged fields too.")
def diff(file_a, file_b, show_all):
    """Compare two DMS records and show field-level differences.

    Examples:

        dms diff records/story_v1.json records/story_v2.json

        dms diff examples/poem.json examples/story.json --all
    """
    from dms.diff import diff_files, print_diff

    try:
        diffs = diff_files(file_a, file_b)
        print_diff(diffs, path_a=file_a, path_b=file_b, show_unchanged=show_all)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


# ─── report ──────────────────────────────────────────────────────────────────

@main.command()
@click.option("-d", "--dir", "directory", type=click.Path(exists=True, file_okay=False), required=True, help="Directory of DMS records.")
@click.option("-o", "--output", type=click.Path(), default=None, help="Output file path.")
@click.option("-f", "--format", "fmt", type=click.Choice(["html", "md"], case_sensitive=False), default="html", help="Output format (default: html).")
@click.option("--title", type=str, default="Dzaleka Heritage Collection", help="Report title.")
def report(directory, output, fmt, title):
    """Generate a browsable catalogue from a directory of DMS records.

    Examples:

        dms report --dir records/

        dms report --dir records/ --format md --output catalogue.md

        dms report --dir examples/ --title "Example Collection"
    """
    from dms.report import generate_html_report, generate_md_report

    if fmt == "html":
        if output is None:
            from pathlib import Path
            output = Path(directory) / "report.html"
        generate_html_report(directory, output, title=title)
    else:
        if output is None:
            from pathlib import Path
            output = Path(directory) / "report.md"
        generate_md_report(directory, output, title=title)

    console.print(f"  [dim]Open {output} to view.[/dim]")


# ─── stats ───────────────────────────────────────────────────────────────────

@main.command()
@click.option("-d", "--dir", "directory", type=click.Path(exists=True, file_okay=False), required=True, help="Directory of DMS records to analyze.")
def stats(directory):
    """Show collection statistics for a directory of DMS records."""
    from dms.stats import gather_stats, print_stats

    data = gather_stats(directory)
    print_stats(data)


# ─── info ────────────────────────────────────────────────────────────────────

@main.command()
def info():
    """Show DMS schema version and field summary."""
    from dms.schema import (
        get_schema_version,
        get_required_fields,
        get_field_descriptions,
        get_type_enum,
        get_creator_roles,
        get_access_levels,
    )

    console.print()
    console.print(Panel(
        f"[bold bright_blue]Dzaleka Metadata Standard (DMS)[/bold bright_blue]\n"
        f"[dim]An open-source metadata standard for documenting\n"
        f"and sharing Dzaleka's digital heritage.[/dim]\n\n"
        f"  CLI version:    [cyan]{__version__}[/cyan]\n"
        f"  Schema version: [cyan]{get_schema_version()}[/cyan]",
        box=box.DOUBLE,
        border_style="bright_blue",
    ))

    required = set(get_required_fields())
    descriptions = get_field_descriptions()

    table = Table(
        title="Schema Fields",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Field", style="white", min_width=16)
    table.add_column("Required", justify="center", min_width=10)
    table.add_column("Description", style="dim")

    for field, desc in descriptions.items():
        req = "[bold green]✓ Yes[/bold green]" if field in required else "[dim]No[/dim]"
        table.add_row(field, req, desc)

    console.print(table)

    console.print(f"\n  [bold]Heritage Types:[/bold] {', '.join(get_type_enum())}")
    console.print(f"  [bold]Creator Roles:[/bold] {', '.join(get_creator_roles())}")
    console.print(f"  [bold]Access Levels:[/bold] {', '.join(get_access_levels())}")
    console.print()

# ─── sync ──────────────────────────────────────────────────────────────────────

@main.command()
@click.option("-d", "--dir", "directory", type=click.Path(exists=True, file_okay=False), default="records", help="Directory of DMS records to sync.")
@click.option("-r", "--remote", type=str, default=None, help="Set the GitHub/GitLab remote URL to back up to.")
@click.option("-m", "--message", type=str, default=None, help="Custom commit message.")
def sync(directory, remote, message):
    """Securely back up and synchronize JSON records via Git.

    Automatically versions your records offline, and pushes them 
    to a centralized repository if you have internet access.

    Examples:

        dms sync

        dms sync --remote git@github.com:Dzaleka-Connect/Core-Archive.git

        dms sync --message "Added new oral histories"
    """
    from dms.sync import sync_records
    
    sync_records(directory=directory, remote=remote, message=message)


# ─── web ─────────────────────────────────────────────────────────────────────

@main.command()
@click.option("-p", "--port", type=int, default=8080, help="Port to run the web server on.")
@click.option("-d", "--dir", "directory", type=click.Path(), default="records", help="Directory for saving records.")
@click.option("--no-open", is_flag=True, default=False, help="Don't auto-open the browser.")
def web(port, directory, no_open):
    """Launch the DMS web UI in your browser.

    A local web form for creating, validating, and managing
    heritage metadata records — no terminal required.

    Examples:

        dms web

        dms web --port 3000 --dir my_records/

        dms web --no-open
    """
    from dms.web import start_server
    start_server(port=port, records_dir=directory, open_browser=not no_open)


if __name__ == "__main__":
    main()
