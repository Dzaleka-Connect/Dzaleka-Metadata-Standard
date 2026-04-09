"""
DMS Converter

Bidirectional conversion between CSV and JSON formats
for DMS metadata records.
"""

import csv
import json
import uuid
from datetime import date
from pathlib import Path
from io import StringIO

from rich.console import Console
from rich.panel import Panel
from rich import box

console = Console()

# Mapping of flat CSV column names to nested JSON paths
CSV_COLUMNS = [
    "id",
    "title",
    "type",
    "description",
    "language",
    "creator_name",
    "creator_identifier",
    "creator_role",
    "date_created",
    "date_event",
    "subject",
    "subject_ref_identifier",
    "subject_ref_label",
    "subject_ref_scheme",
    "location_name",
    "location_identifier",
    "location_area",
    "location_latitude",
    "location_longitude",
    "format",
    "rights_license",
    "rights_access_level",
    "rights_consent_status",
    "rights_sensitivity",
    "rights_access_note",
    "rights_holder",
    "source_contributor",
    "source_collection",
    "source_collection_identifier",
    "source_original_format",
    "technical_file_uri",
    "technical_filename",
    "technical_checksum",
    "technical_checksum_algorithm",
    "technical_file_size_bytes",
    "technical_duration_seconds",
    "technical_page_count",
    "technical_width_px",
    "technical_height_px",
    "relation_detail_target",
    "relation_detail_type",
    "relation_detail_label",
    "relation_detail_note",
    "schema_version",
]

# Delimiter for multi-value fields in CSV
MULTI_VALUE_DELIMITER = "|"


def csv_to_json(csv_path: str | Path, output_path: str | Path | None = None) -> list[dict]:
    """Convert a CSV file to a list of DMS JSON records.

    Args:
        csv_path: Path to the input CSV file.
        output_path: Optional path to write JSON output.

    Returns:
        List of DMS record dicts.
    """
    csv_path = Path(csv_path)

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        records = []

        for row in reader:
            record = _csv_row_to_record(row)
            records.append(record)

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if output_path.suffix == ".json":
            # Write all records to a single JSON array
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2, ensure_ascii=False)
                f.write("\n")
        else:
            # Write individual files
            output_path.mkdir(parents=True, exist_ok=True)
            for rec in records:
                fp = output_path / f"{rec.get('type', 'record')}_{rec['id'][:8]}.json"
                with open(fp, "w", encoding="utf-8") as f:
                    json.dump(rec, f, indent=2, ensure_ascii=False)
                    f.write("\n")

    console.print(f"  [green]✓ Converted {len(records)} records from CSV[/green]")
    return records


def json_to_csv(json_path: str | Path, output_path: str | Path | None = None) -> str:
    """Convert a JSON file (single record or array) to CSV format.

    Args:
        json_path: Path to the input JSON file.
        output_path: Optional path to write CSV output.

    Returns:
        CSV content as a string.
    """
    json_path = Path(json_path)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        records = [data]
    elif isinstance(data, list):
        records = data
    else:
        raise ValueError(f"Expected JSON object or array, got {type(data).__name__}")

    rows = [_record_to_csv_row(rec) for rec in records]

    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    csv_content = output.getvalue()

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(csv_content)

    console.print(f"  [green]✓ Converted {len(records)} records to CSV[/green]")
    return csv_content


def _csv_row_to_record(row: dict) -> dict:
    """Convert a single CSV row dict to a DMS record dict."""
    record = {}

    # ID
    record["id"] = row.get("id", "").strip() or str(uuid.uuid4())

    # Required fields
    record["title"] = row.get("title", "").strip()
    record["type"] = row.get("type", "").strip()
    record["description"] = row.get("description", "").strip()
    record["language"] = row.get("language", "en").strip()

    # Creator
    creator_name = row.get("creator_name", "").strip()
    if creator_name:
        names = creator_name.split(MULTI_VALUE_DELIMITER)
        identifiers = row.get("creator_identifier", "").strip().split(MULTI_VALUE_DELIMITER)
        roles = row.get("creator_role", "").strip().split(MULTI_VALUE_DELIMITER)
        creators = []
        for i, name in enumerate(names):
            name = name.strip()
            if not name:
                continue
            creator = {"name": name}
            if i < len(identifiers) and identifiers[i].strip():
                creator["identifier"] = identifiers[i].strip()
            if i < len(roles) and roles[i].strip():
                creator["role"] = roles[i].strip()
            creators.append(creator)
        if creators:
            record["creator"] = creators

    # Date
    date_info = {}
    date_created = row.get("date_created", "").strip()
    if date_created:
        date_info["created"] = date_created
    date_event = row.get("date_event", "").strip()
    if date_event:
        date_info["event_date"] = date_event
    if date_info:
        record["date"] = date_info

    # Subject
    subject = row.get("subject", "").strip()
    if subject:
        record["subject"] = [s.strip() for s in subject.split(MULTI_VALUE_DELIMITER) if s.strip()]

    subject_ref_ids = row.get("subject_ref_identifier", "").strip().split(MULTI_VALUE_DELIMITER)
    subject_ref_labels = row.get("subject_ref_label", "").strip().split(MULTI_VALUE_DELIMITER)
    subject_ref_schemes = row.get("subject_ref_scheme", "").strip().split(MULTI_VALUE_DELIMITER)
    subject_refs = []
    for i, identifier in enumerate(subject_ref_ids):
        identifier = identifier.strip()
        if not identifier:
            continue
        subject_ref = {"identifier": identifier}
        if i < len(subject_ref_labels) and subject_ref_labels[i].strip():
            subject_ref["label"] = subject_ref_labels[i].strip()
        if i < len(subject_ref_schemes) and subject_ref_schemes[i].strip():
            subject_ref["scheme"] = subject_ref_schemes[i].strip()
        subject_refs.append(subject_ref)
    if subject_refs:
        record["subject_ref"] = subject_refs

    # Location
    location = {}
    loc_name = row.get("location_name", "").strip()
    if loc_name:
        location["name"] = loc_name
    loc_identifier = row.get("location_identifier", "").strip()
    if loc_identifier:
        location["identifier"] = loc_identifier
    loc_area = row.get("location_area", "").strip()
    if loc_area:
        location["area"] = loc_area
    loc_lat = row.get("location_latitude", "").strip()
    if loc_lat:
        try:
            location["latitude"] = float(loc_lat)
        except ValueError:
            pass
    loc_lon = row.get("location_longitude", "").strip()
    if loc_lon:
        try:
            location["longitude"] = float(loc_lon)
        except ValueError:
            pass
    if location:
        record["location"] = location

    # Format
    fmt = row.get("format", "").strip()
    if fmt:
        record["format"] = fmt

    # Rights
    rights = {}
    lic = row.get("rights_license", "").strip()
    if lic:
        rights["license"] = lic
    access = row.get("rights_access_level", "").strip()
    if access:
        rights["access_level"] = access
    consent_status = row.get("rights_consent_status", "").strip()
    if consent_status:
        rights["consent_status"] = consent_status
    sensitivity = row.get("rights_sensitivity", "").strip()
    if sensitivity:
        rights["sensitivity"] = [s.strip() for s in sensitivity.split(MULTI_VALUE_DELIMITER) if s.strip()]
    access_note = row.get("rights_access_note", "").strip()
    if access_note:
        rights["access_note"] = access_note
    holder = row.get("rights_holder", "").strip()
    if holder:
        rights["holder"] = holder
    if rights:
        record["rights"] = rights

    # Source
    source = {}
    contrib = row.get("source_contributor", "").strip()
    if contrib:
        source["contributor"] = contrib
    collection = row.get("source_collection", "").strip()
    if collection:
        source["collection"] = collection
    collection_identifier = row.get("source_collection_identifier", "").strip()
    if collection_identifier:
        source["collection_identifier"] = collection_identifier
    orig_fmt = row.get("source_original_format", "").strip()
    if orig_fmt:
        source["original_format"] = orig_fmt
    if source:
        record["source"] = source

    # Technical
    technical = {}
    file_uri = row.get("technical_file_uri", "").strip()
    if file_uri:
        technical["file_uri"] = file_uri
    filename = row.get("technical_filename", "").strip()
    if filename:
        technical["filename"] = filename
    checksum = row.get("technical_checksum", "").strip()
    if checksum:
        technical["checksum"] = checksum
    checksum_algorithm = row.get("technical_checksum_algorithm", "").strip()
    if checksum_algorithm:
        technical["checksum_algorithm"] = checksum_algorithm
    file_size_bytes = row.get("technical_file_size_bytes", "").strip()
    if file_size_bytes:
        try:
            technical["file_size_bytes"] = int(file_size_bytes)
        except ValueError:
            pass
    duration_seconds = row.get("technical_duration_seconds", "").strip()
    if duration_seconds:
        try:
            technical["duration_seconds"] = float(duration_seconds)
        except ValueError:
            pass
    page_count = row.get("technical_page_count", "").strip()
    if page_count:
        try:
            technical["page_count"] = int(page_count)
        except ValueError:
            pass
    width_px = row.get("technical_width_px", "").strip()
    if width_px:
        try:
            technical["width_px"] = int(width_px)
        except ValueError:
            pass
    height_px = row.get("technical_height_px", "").strip()
    if height_px:
        try:
            technical["height_px"] = int(height_px)
        except ValueError:
            pass
    if technical:
        record["technical"] = technical

    # Typed relations
    relation_targets = row.get("relation_detail_target", "").strip().split(MULTI_VALUE_DELIMITER)
    relation_types = row.get("relation_detail_type", "").strip().split(MULTI_VALUE_DELIMITER)
    relation_labels = row.get("relation_detail_label", "").strip().split(MULTI_VALUE_DELIMITER)
    relation_notes = row.get("relation_detail_note", "").strip().split(MULTI_VALUE_DELIMITER)
    relation_details = []
    for i, target in enumerate(relation_targets):
        target = target.strip()
        relation_type = relation_types[i].strip() if i < len(relation_types) else ""
        if not target or not relation_type:
            continue
        relation_detail = {"target": target, "relation_type": relation_type}
        if i < len(relation_labels) and relation_labels[i].strip():
            relation_detail["label"] = relation_labels[i].strip()
        if i < len(relation_notes) and relation_notes[i].strip():
            relation_detail["note"] = relation_notes[i].strip()
        relation_details.append(relation_detail)
    if relation_details:
        record["relation_detail"] = relation_details

    # Schema version
    sv = row.get("schema_version", "").strip()
    if sv:
        record["schema_version"] = sv

    return record


def _record_to_csv_row(record: dict) -> dict:
    """Convert a DMS record dict to a flat CSV row dict."""
    row = {}

    row["id"] = record.get("id", "")
    row["title"] = record.get("title", "")
    row["type"] = record.get("type", "")
    row["description"] = record.get("description", "")
    row["language"] = record.get("language", "")

    # Creator
    creators = record.get("creator", [])
    if creators:
        row["creator_name"] = MULTI_VALUE_DELIMITER.join(c.get("name", "") for c in creators)
        row["creator_identifier"] = MULTI_VALUE_DELIMITER.join(c.get("identifier", "") for c in creators)
        row["creator_role"] = MULTI_VALUE_DELIMITER.join(c.get("role", "") for c in creators)
    else:
        row["creator_name"] = ""
        row["creator_identifier"] = ""
        row["creator_role"] = ""

    # Date
    date_info = record.get("date", {})
    row["date_created"] = date_info.get("created", "")
    row["date_event"] = date_info.get("event_date", "")

    # Subject
    subjects = record.get("subject", [])
    row["subject"] = MULTI_VALUE_DELIMITER.join(subjects)

    subject_refs = record.get("subject_ref", [])
    if subject_refs:
        row["subject_ref_identifier"] = MULTI_VALUE_DELIMITER.join(s.get("identifier", "") for s in subject_refs)
        row["subject_ref_label"] = MULTI_VALUE_DELIMITER.join(s.get("label", "") for s in subject_refs)
        row["subject_ref_scheme"] = MULTI_VALUE_DELIMITER.join(s.get("scheme", "") for s in subject_refs)
    else:
        row["subject_ref_identifier"] = ""
        row["subject_ref_label"] = ""
        row["subject_ref_scheme"] = ""

    # Location
    location = record.get("location", {})
    row["location_name"] = location.get("name", "")
    row["location_identifier"] = location.get("identifier", "")
    row["location_area"] = location.get("area", "")
    row["location_latitude"] = str(location.get("latitude", "")) if "latitude" in location else ""
    row["location_longitude"] = str(location.get("longitude", "")) if "longitude" in location else ""

    # Format
    row["format"] = record.get("format", "")

    # Rights
    rights = record.get("rights", {})
    row["rights_license"] = rights.get("license", "")
    row["rights_access_level"] = rights.get("access_level", "")
    row["rights_consent_status"] = rights.get("consent_status", "")
    sensitivities = rights.get("sensitivity", [])
    row["rights_sensitivity"] = MULTI_VALUE_DELIMITER.join(sensitivities) if isinstance(sensitivities, list) else ""
    row["rights_access_note"] = rights.get("access_note", "")
    row["rights_holder"] = rights.get("holder", "")

    # Source
    source = record.get("source", {})
    row["source_contributor"] = source.get("contributor", "")
    row["source_collection"] = source.get("collection", "")
    row["source_collection_identifier"] = source.get("collection_identifier", "")
    row["source_original_format"] = source.get("original_format", "")

    # Technical
    technical = record.get("technical", {})
    row["technical_file_uri"] = technical.get("file_uri", "")
    row["technical_filename"] = technical.get("filename", "")
    row["technical_checksum"] = technical.get("checksum", "")
    row["technical_checksum_algorithm"] = technical.get("checksum_algorithm", "")
    row["technical_file_size_bytes"] = technical.get("file_size_bytes", "")
    row["technical_duration_seconds"] = technical.get("duration_seconds", "")
    row["technical_page_count"] = technical.get("page_count", "")
    row["technical_width_px"] = technical.get("width_px", "")
    row["technical_height_px"] = technical.get("height_px", "")

    # Typed relations
    relation_details = record.get("relation_detail", [])
    if relation_details:
        row["relation_detail_target"] = MULTI_VALUE_DELIMITER.join(r.get("target", "") for r in relation_details)
        row["relation_detail_type"] = MULTI_VALUE_DELIMITER.join(r.get("relation_type", "") for r in relation_details)
        row["relation_detail_label"] = MULTI_VALUE_DELIMITER.join(r.get("label", "") for r in relation_details)
        row["relation_detail_note"] = MULTI_VALUE_DELIMITER.join(r.get("note", "") for r in relation_details)
    else:
        row["relation_detail_target"] = ""
        row["relation_detail_type"] = ""
        row["relation_detail_label"] = ""
        row["relation_detail_note"] = ""

    # Schema version
    row["schema_version"] = record.get("schema_version", "")

    return row
