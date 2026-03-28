"""
DMS JSON-LD Exporter

Converts DMS records to JSON-LD format using the DMS context,
enabling linked data publishing and semantic web interoperability.
"""

import json
from pathlib import Path

from rich.console import Console

console = Console()

CONTEXT_FILE = Path(__file__).resolve().parent / "data" / "schema" / "dms.jsonld"


def load_context() -> dict:
    """Load the DMS JSON-LD context."""
    if not CONTEXT_FILE.exists():
        raise FileNotFoundError(
            f"DMS JSON-LD context not found at {CONTEXT_FILE}. "
            "Ensure the schema/ directory is present."
        )
    with open(CONTEXT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("@context", data)


def record_to_jsonld(record: dict) -> dict:
    """Convert a single DMS record to JSON-LD format.

    Wraps the record with @context and @type, and maps
    the DMS 'type' field to appropriate Schema.org / BIBO types.

    Args:
        record: A DMS record dict.

    Returns:
        A JSON-LD document dict.
    """
    context = load_context()

    # Map DMS types to Schema.org @type values
    type_map = {
        "story": "schema:Article",
        "photo": "schema:Photograph",
        "document": "schema:DigitalDocument",
        "audio": "schema:AudioObject",
        "video": "schema:VideoObject",
        "event": "schema:Event",
        "map": "schema:Map",
        "artwork": "schema:VisualArtwork",
        "site": "schema:Place",
        "poem": "schema:CreativeWork",
    }

    doc = {"@context": context}

    # Set @type based on the DMS type field
    dms_type = record.get("type", "")
    schema_type = type_map.get(dms_type, "schema:CreativeWork")
    doc["@type"] = ["dms:HeritageRecord", schema_type]

    # Set @id from the record id
    if "id" in record:
        doc["@id"] = f"urn:dms:{record['id']}"

    # Copy all record fields
    for key, value in record.items():
        if key == "id":
            doc["dc:identifier"] = value
        elif key == "creator" and isinstance(value, list):
            # Annotate creators with @type
            creators = []
            for c in value:
                creator_ld = {"@type": "foaf:Person"}
                creator_ld.update(c)
                creators.append(creator_ld)
            doc["creator"] = creators
        elif key == "location" and isinstance(value, dict):
            loc_ld = {"@type": "schema:Place"}
            loc_ld.update(value)
            doc["location"] = loc_ld
        else:
            doc[key] = value

    return doc


def export_jsonld(
    input_path: str | Path,
    output_path: str | Path | None = None,
) -> dict | list[dict]:
    """Export a DMS JSON file as JSON-LD.

    Args:
        input_path: Path to a DMS JSON record or array of records.
        output_path: Optional output file path. If None, returns the result.

    Returns:
        JSON-LD document(s).
    """
    input_path = Path(input_path)

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        result = record_to_jsonld(data)
    elif isinstance(data, list):
        result = [record_to_jsonld(rec) for rec in data]
    else:
        raise ValueError(f"Expected JSON object or array, got {type(data).__name__}")

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
            f.write("\n")

    count = 1 if isinstance(data, dict) else len(data)
    console.print(f"  [green]✓ Exported {count} record(s) as JSON-LD[/green]")

    return result


def export_dir_jsonld(
    dir_path: str | Path,
    output_path: str | Path | None = None,
) -> list[dict]:
    """Export all JSON files in a directory as a JSON-LD @graph.

    Args:
        dir_path: Directory containing DMS JSON files.
        output_path: Optional output file path.

    Returns:
        A JSON-LD document with @graph containing all records.
    """
    dir_path = Path(dir_path)
    json_files = sorted(dir_path.glob("*.json"))

    records = []
    for jf in json_files:
        try:
            with open(jf, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                records.append(record_to_jsonld(data))
            elif isinstance(data, list):
                records.extend(record_to_jsonld(rec) for rec in data)
        except (json.JSONDecodeError, ValueError):
            console.print(f"  [yellow]⚠ Skipped {jf.name} (not valid JSON)[/yellow]")

    context = load_context()
    graph_doc = {
        "@context": context,
        "@graph": records,
    }

    # Strip individual @context from graph members
    for rec in graph_doc["@graph"]:
        rec.pop("@context", None)

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(graph_doc, f, indent=2, ensure_ascii=False)
            f.write("\n")

    console.print(f"  [green]✓ Exported {len(records)} record(s) as JSON-LD graph[/green]")

    return graph_doc
