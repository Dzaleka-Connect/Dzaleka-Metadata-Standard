"""
DMS Validator

Provides validation of DMS records against the JSON Schema,
with human-friendly error reporting using Rich.
"""

import json
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from dms.schema import load_schema, get_required_fields

console = Console()


# Human-readable names for JSON Schema paths
FIELD_LABELS = {
    "id": "ID",
    "title": "Title",
    "creator": "Creator(s)",
    "date": "Date",
    "description": "Description",
    "type": "Type",
    "subject": "Subject/Tags",
    "language": "Language",
    "location": "Location",
    "rights": "Rights",
    "source": "Source",
    "format": "Format",
    "relation": "Related Records",
    "coverage": "Coverage",
    "schema_version": "Schema Version",
}


def _humanize_path(path: list) -> str:
    """Convert a JSON path list to a human-readable string."""
    parts = []
    for segment in path:
        if isinstance(segment, int):
            parts.append(f"[{segment}]")
        else:
            label = FIELD_LABELS.get(segment, segment)
            parts.append(label)
    return " → ".join(parts) if parts else "(root)"


def _format_error(error: ValidationError) -> dict:
    """Format a single validation error into a human-friendly dict."""
    path = list(error.absolute_path)
    field = _humanize_path(path)

    # Customize message based on error type
    if error.validator == "required":
        missing = error.message.split("'")[1] if "'" in error.message else error.message
        label = FIELD_LABELS.get(missing, missing)
        message = f"Required field '{label}' is missing."
    elif error.validator == "enum":
        allowed = error.schema.get("enum", [])
        message = f"Invalid value '{error.instance}'. Allowed: {', '.join(str(v) for v in allowed)}"
    elif error.validator == "type":
        expected = error.schema.get("type", "unknown")
        message = f"Expected type '{expected}', got '{type(error.instance).__name__}'."
    elif error.validator == "minLength":
        message = "Value cannot be empty."
    elif error.validator == "pattern":
        message = f"Value '{error.instance}' does not match expected format."
    elif error.validator == "format":
        fmt = error.schema.get("format", "unknown")
        message = f"Value '{error.instance}' is not a valid {fmt}."
    elif error.validator == "additionalProperties":
        message = error.message
    else:
        message = error.message

    return {
        "field": field,
        "message": message,
        "validator": error.validator,
        "path": ".".join(str(p) for p in path) if path else "$",
    }


def validate_record(record: dict) -> list[dict]:
    """Validate a single DMS record against the schema.

    Args:
        record: A dictionary representing a DMS record.

    Returns:
        A list of error dicts. Empty list means the record is valid.
        Each error dict has keys: field, message, validator, path.
    """
    schema = load_schema()
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(record), key=lambda e: list(e.absolute_path))
    return [_format_error(e) for e in errors]


def validate_file(filepath: str | Path) -> tuple[bool, list[dict]]:
    """Validate a JSON file against the DMS schema.

    Args:
        filepath: Path to a JSON file.

    Returns:
        Tuple of (is_valid, errors).
    """
    filepath = Path(filepath)

    if not filepath.exists():
        return False, [{"field": "(file)", "message": f"File not found: {filepath}", "validator": "file", "path": ""}]

    if not filepath.suffix == ".json":
        return False, [{"field": "(file)", "message": f"Expected .json file, got '{filepath.suffix}'", "validator": "file", "path": ""}]

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, [{"field": "(file)", "message": f"Invalid JSON: {e}", "validator": "file", "path": ""}]

    errors = validate_record(data)
    return len(errors) == 0, errors


def validate_directory(dirpath: str | Path) -> dict:
    """Validate all .json files in a directory.

    Args:
        dirpath: Path to a directory containing JSON files.

    Returns:
        Dict with keys: total, valid, invalid, results (list of per-file results).
    """
    dirpath = Path(dirpath)
    json_files = sorted(dirpath.glob("*.json"))

    results = []
    valid_count = 0
    invalid_count = 0

    for fp in json_files:
        is_valid, errors = validate_file(fp)
        results.append({
            "file": str(fp.name),
            "valid": is_valid,
            "errors": errors,
        })
        if is_valid:
            valid_count += 1
        else:
            invalid_count += 1

    return {
        "total": len(json_files),
        "valid": valid_count,
        "invalid": invalid_count,
        "results": results,
    }


def get_warnings(record: dict) -> list[str]:
    """Return warnings for recommended (but not required) fields that are missing.

    Args:
        record: A dictionary representing a DMS record.

    Returns:
        List of warning messages.
    """
    recommended = ["creator", "date", "subject", "location", "rights", "source", "format"]
    warnings = []
    for field in recommended:
        if field not in record:
            label = FIELD_LABELS.get(field, field)
            warnings.append(f"Recommended field '{label}' is not provided.")
    return warnings


def print_validation_result(filepath: str, is_valid: bool, errors: list[dict], warnings: list[str] | None = None):
    """Pretty-print validation results using Rich."""
    if is_valid:
        console.print(Panel(
            f"[bold green]✓ VALID[/bold green]  {filepath}",
            box=box.ROUNDED,
            border_style="green",
        ))
        if warnings:
            for w in warnings:
                console.print(f"  [yellow]⚠ {w}[/yellow]")
    else:
        console.print(Panel(
            f"[bold red]✗ INVALID[/bold red]  {filepath}",
            box=box.ROUNDED,
            border_style="red",
        ))
        table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold")
        table.add_column("Field", style="cyan", min_width=15)
        table.add_column("Issue", style="white")
        for err in errors:
            table.add_row(err["field"], err["message"])
        console.print(table)


def print_batch_summary(result: dict):
    """Pretty-print batch validation summary."""
    total = result["total"]
    valid = result["valid"]
    invalid = result["invalid"]

    if total == 0:
        console.print("[yellow]No .json files found in directory.[/yellow]")
        return

    style = "green" if invalid == 0 else "red"
    console.print()
    console.print(Panel(
        f"[bold]Batch Validation Summary[/bold]\n\n"
        f"  Total files:  {total}\n"
        f"  [green]Valid:        {valid}[/green]\n"
        f"  [red]Invalid:      {invalid}[/red]",
        box=box.ROUNDED,
        border_style=style,
    ))
