"""
DMS Schema Loading and Resolution

Handles loading the JSON Schema from the dms/data/schema/ directory
and provides utilities for schema introspection.
"""

import json
from pathlib import Path
from functools import lru_cache


SCHEMA_DIR = Path(__file__).resolve().parent / "data" / "schema"
SCHEMA_FILE = SCHEMA_DIR / "dms.json"


@lru_cache(maxsize=1)
def load_schema() -> dict:
    """Load and return the DMS JSON Schema.

    Returns:
        dict: The parsed JSON Schema.

    Raises:
        FileNotFoundError: If the schema file is not found.
        json.JSONDecodeError: If the schema file is not valid JSON.
    """
    if not SCHEMA_FILE.exists():
        raise FileNotFoundError(
            f"DMS schema not found at {SCHEMA_FILE}. "
            "Ensure the dms/data/schema/ directory is present."
        )
    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_schema_version() -> str:
    """Return the schema version string."""
    schema = load_schema()
    version_prop = schema.get("properties", {}).get("schema_version", {})
    return version_prop.get("const", "unknown")


def get_required_fields() -> list[str]:
    """Return a list of required field names."""
    schema = load_schema()
    return schema.get("required", [])


def get_type_enum() -> list[str]:
    """Return the list of valid heritage item types."""
    schema = load_schema()
    return (
        schema.get("properties", {})
        .get("type", {})
        .get("enum", [])
    )


def get_field_descriptions() -> dict[str, str]:
    """Return a mapping of field names to their descriptions."""
    schema = load_schema()
    properties = schema.get("properties", {})
    return {
        name: prop.get("description", "No description available.")
        for name, prop in properties.items()
    }


def get_creator_roles() -> list[str]:
    """Return the list of valid creator roles."""
    schema = load_schema()
    defs = schema.get("$defs", {})
    creator = defs.get("Creator", {})
    role_prop = creator.get("properties", {}).get("role", {})
    return role_prop.get("enum", [])


def get_access_levels() -> list[str]:
    """Return the list of valid access levels."""
    schema = load_schema()
    defs = schema.get("$defs", {})
    rights = defs.get("Rights", {})
    access_prop = rights.get("properties", {}).get("access_level", {})
    return access_prop.get("enum", [])


def get_consent_statuses() -> list[str]:
    """Return the list of valid consent statuses."""
    schema = load_schema()
    defs = schema.get("$defs", {})
    rights = defs.get("Rights", {})
    consent_prop = rights.get("properties", {}).get("consent_status", {})
    return consent_prop.get("enum", [])


def get_sensitivity_values() -> list[str]:
    """Return the list of valid sensitivity values."""
    schema = load_schema()
    defs = schema.get("$defs", {})
    rights = defs.get("Rights", {})
    sensitivity_prop = rights.get("properties", {}).get("sensitivity", {})
    items = sensitivity_prop.get("items", {})
    return items.get("enum", [])


def get_relation_types() -> list[str]:
    """Return the list of valid typed relation values."""
    schema = load_schema()
    defs = schema.get("$defs", {})
    relation = defs.get("RelationDetail", {})
    relation_type_prop = relation.get("properties", {}).get("relation_type", {})
    return relation_type_prop.get("enum", [])
