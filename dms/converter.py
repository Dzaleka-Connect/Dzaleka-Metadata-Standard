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
    "creator_role",
    "date_created",
    "date_event",
    "subject",
    "location_name",
    "location_area",
    "location_latitude",
    "location_longitude",
    "format",
    "rights_license",
    "rights_access_level",
    "rights_holder",
    "source_contributor",
    "source_collection",
    "source_original_format",
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
        roles = row.get("creator_role", "").strip().split(MULTI_VALUE_DELIMITER)
        creators = []
        for i, name in enumerate(names):
            name = name.strip()
            if not name:
                continue
            creator = {"name": name}
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

    # Location
    location = {}
    loc_name = row.get("location_name", "").strip()
    if loc_name:
        location["name"] = loc_name
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
    orig_fmt = row.get("source_original_format", "").strip()
    if orig_fmt:
        source["original_format"] = orig_fmt
    if source:
        record["source"] = source

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
        row["creator_role"] = MULTI_VALUE_DELIMITER.join(c.get("role", "") for c in creators)
    else:
        row["creator_name"] = ""
        row["creator_role"] = ""

    # Date
    date_info = record.get("date", {})
    row["date_created"] = date_info.get("created", "")
    row["date_event"] = date_info.get("event_date", "")

    # Subject
    subjects = record.get("subject", [])
    row["subject"] = MULTI_VALUE_DELIMITER.join(subjects)

    # Location
    location = record.get("location", {})
    row["location_name"] = location.get("name", "")
    row["location_area"] = location.get("area", "")
    row["location_latitude"] = str(location.get("latitude", "")) if "latitude" in location else ""
    row["location_longitude"] = str(location.get("longitude", "")) if "longitude" in location else ""

    # Format
    row["format"] = record.get("format", "")

    # Rights
    rights = record.get("rights", {})
    row["rights_license"] = rights.get("license", "")
    row["rights_access_level"] = rights.get("access_level", "")
    row["rights_holder"] = rights.get("holder", "")

    # Source
    source = record.get("source", {})
    row["source_contributor"] = source.get("contributor", "")
    row["source_collection"] = source.get("collection", "")
    row["source_original_format"] = source.get("original_format", "")

    # Schema version
    row["schema_version"] = record.get("schema_version", "")

    return row
