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
    "subject_ref": "Subject References",
    "language": "Language",
    "location": "Location",
    "rights": "Rights",
    "source": "Source",
    "format": "Format",
    "technical": "Technical Metadata",
    "relation": "Related Records",
    "relation_detail": "Typed Relations",
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


def _semantic_error(path: list, message: str, validator: str = "semantic") -> dict:
    """Create a human-friendly semantic validation error."""
    return {
        "field": _humanize_path(path),
        "message": message,
        "validator": validator,
        "path": ".".join(str(p) for p in path) if path else "$",
    }


def _find_deprecated_term_by_label(label: str) -> tuple[str, dict] | None:
    """Look up a deprecated managed DMS term by preferred or short label."""
    from dms.taxonomy import get_deprecated_terms, get_vocabulary_list

    wanted = str(label or "").strip().lower()
    if not wanted:
        return None

    for vocabulary in get_vocabulary_list():
        for term in get_deprecated_terms(vocabulary):
            term_label = str(term.get("label", "")).strip().lower()
            full_id = str(term.get("id", "")).strip().lower()
            short_id = str(term.get("id", "")).rsplit("/", 1)[-1].lower()
            if wanted in {term_label, short_id, full_id}:
                return vocabulary, term
    return None


def _validate_subject_references(record: dict) -> list[dict]:
    """Validate managed DMS concept references beyond raw JSON Schema shape."""
    from dms.taxonomy import (
        get_term_info,
        infer_vocabulary_from_identifier,
        is_managed_dms_identifier,
        load_taxonomy,
    )

    errors = []
    seen_identifiers = set()

    for index, ref in enumerate(record.get("subject_ref", [])):
        identifier = str(ref.get("identifier", "")).strip()
        if not identifier:
            continue

        if identifier in seen_identifiers:
            errors.append(
                _semantic_error(
                    ["subject_ref", index, "identifier"],
                    f"Duplicate subject reference '{identifier}' is not allowed.",
                    validator="duplicate",
                )
            )
            continue
        seen_identifiers.add(identifier)

        if not is_managed_dms_identifier(identifier):
            continue

        vocabulary = infer_vocabulary_from_identifier(identifier)
        if vocabulary is None:
            errors.append(
                _semantic_error(
                    ["subject_ref", index, "identifier"],
                    f"Managed DMS identifier '{identifier}' does not map to a known DMS vocabulary.",
                    validator="taxonomy",
                )
            )
            continue

        term = get_term_info(vocabulary, identifier)
        if term is None:
            errors.append(
                _semantic_error(
                    ["subject_ref", index, "identifier"],
                    f"Managed DMS identifier '{identifier}' is not defined in the '{vocabulary}' vocabulary.",
                    validator="taxonomy",
                )
            )
            continue

        if term.get("deprecated"):
            replacement = str(term.get("supersededBy", "")).strip()
            replacement_text = f" Use '{replacement}' instead." if replacement else ""
            errors.append(
                _semantic_error(
                    ["subject_ref", index, "identifier"],
                    f"Managed DMS identifier '{identifier}' is deprecated and cannot be used in new records.{replacement_text}",
                    validator="taxonomy",
                )
            )
            continue

        provided_scheme = str(ref.get("scheme", "")).strip()
        if provided_scheme:
            expected_scheme = str(load_taxonomy(vocabulary).get("label", "")).strip()
            if expected_scheme and provided_scheme != expected_scheme:
                errors.append(
                    _semantic_error(
                        ["subject_ref", index, "scheme"],
                        f"Scheme '{provided_scheme}' does not match the managed DMS vocabulary label '{expected_scheme}'.",
                        validator="taxonomy",
                    )
                )

        provided_label = str(ref.get("label", "")).strip()
        expected_label = str(term.get("label", "")).strip()
        if provided_label and expected_label and provided_label != expected_label:
            errors.append(
                _semantic_error(
                    ["subject_ref", index, "label"],
                    f"Label '{provided_label}' does not match the canonical DMS label '{expected_label}' for '{identifier}'.",
                    validator="taxonomy",
                )
            )

    return errors


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
    formatted = [_format_error(e) for e in errors]
    if formatted:
        return formatted

    semantic_errors = _validate_subject_references(record)
    return formatted + semantic_errors


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

    rights = record.get("rights", {})
    access_level = rights.get("access_level")
    access_note = str(rights.get("access_note", "")).strip()
    consent_status = rights.get("consent_status")
    sensitivity = rights.get("sensitivity", [])
    if access_level in {"restricted", "community-only"} and not access_note:
        warnings.append("Restricted records should include a rights access note explaining the review or access context.")
    if access_level == "public" and consent_status in {"pending", "unknown", "withheld"}:
        warnings.append(
            f"Access level is public while consent status is '{consent_status}'. Review rights before publishing."
        )
    if access_level == "public" and sensitivity:
        warnings.append("Public access is set even though sensitivity markers are present. Confirm this is intentional.")

    technical = record.get("technical", {})
    checksum = str(technical.get("checksum", "")).strip()
    checksum_algorithm = str(technical.get("checksum_algorithm", "")).strip()
    if checksum and not checksum_algorithm:
        warnings.append("Technical metadata includes a checksum but no checksum algorithm.")
    if checksum_algorithm and not checksum:
        warnings.append("Technical metadata includes a checksum algorithm but no checksum value.")

    for ref in record.get("subject_ref", []):
        identifier = str(ref.get("identifier", "")).strip()
        if not identifier:
            continue
        deprecated_match = _find_deprecated_term_by_label(identifier)
        if deprecated_match:
            vocabulary, term = deprecated_match
            replacement = term.get("supersededBy")
            replacement_text = f" Use '{replacement}' instead." if replacement else ""
            warnings.append(
                f"Subject reference '{identifier}' points to a deprecated term in '{vocabulary}'.{replacement_text}"
            )

    for tag in record.get("subject", []):
        deprecated_match = _find_deprecated_term_by_label(tag)
        if deprecated_match:
            vocabulary, term = deprecated_match
            replacement = term.get("supersededBy")
            replacement_text = f" Prefer '{replacement}' instead." if replacement else ""
            warnings.append(
                f"Subject tag '{tag}' matches a deprecated term in '{vocabulary}'.{replacement_text}"
            )
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
