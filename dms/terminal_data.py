"""Read-only collection data for the terminal workspace."""

import json
from dataclasses import dataclass, field
from pathlib import Path

from dms.validator import get_warnings, validate_record

MAX_RECORD_BYTES = 8 * 1024 * 1024


def display_text(value, fallback="Not recorded") -> str:
    """Keep file content literal and strip terminal control characters."""
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        return fallback
    text = str(value)
    return "".join(char for char in text if char.isprintable() or char == "\n").strip() or fallback


def compact_path(path: Path, max_len: int = 42) -> str:
    """Show a home-relative path the way a shell would."""
    try:
        resolved = path.expanduser().resolve()
        home = Path.home().resolve()
        if resolved == home:
            text = "~"
        else:
            text = "~/" + resolved.relative_to(home).as_posix()
    except (OSError, ValueError):
        text = display_text(str(path), str(path))
    if len(text) <= max_len:
        return text
    parts = Path(text).parts
    if len(parts) >= 2:
        return "…/" + "/".join(parts[-2:])
    return "…" + text[-(max_len - 1):]


@dataclass
class RecordEntry:
    key: str
    record: dict | None = None
    errors: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def title(self) -> str:
        return display_text(self.record.get("title"), "Untitled record") if self.record is not None else self.key

    @property
    def status(self) -> str:
        return "Invalid" if self.errors else "Review" if self.warnings else "Valid"

    def matches(self, query: str, record_type: str = "all", review_only: bool = False) -> bool:
        if review_only and not (self.errors or self.warnings):
            return False
        record = self.record or {}
        if record_type != "all" and record.get("type") != record_type:
            return False
        return query.casefold() in (self.key + " " + json.dumps(record, ensure_ascii=False)).casefold()


def collection_counts(entries: list[RecordEntry]) -> tuple[int, int, int, int]:
    """Return total, schema-valid, invalid, and review-note counts."""
    total = len(entries)
    invalid = sum(1 for entry in entries if entry.errors)
    review = sum(1 for entry in entries if not entry.errors and entry.warnings)
    return total, total - invalid, invalid, review


def resolve_schema_field(schema: dict, key: str) -> dict:
    """Merge a field definition with its $ref target when present."""
    definition = dict(schema.get("properties", {}).get(key, {}))
    ref = definition.get("$ref", "")
    if ref:
        base = schema.get("$defs", {}).get(ref.rsplit("/", 1)[-1], {})
        definition = {**base, **definition}
    return definition


def _file_error(key: str, message: str) -> RecordEntry:
    return RecordEntry(key, errors=[{"field": "File", "message": message, "path": "$", "validator": "file"}])


def read_collection(directory: Path) -> list[RecordEntry]:
    """Include unreadable and malformed files rather than hiding them."""
    if not directory.exists():
        return []
    entries = []
    for path in sorted(directory.glob("*.json")):
        try:
            if path.stat().st_size > MAX_RECORD_BYTES:
                entries.append(_file_error(path.name, "File exceeds the terminal reader's 8 MB limit."))
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            entries.append(_file_error(path.name, str(error)))
            continue
        records = list(enumerate(data)) if isinstance(data, list) else [(None, data)]
        if not records:
            entries.append(_file_error(path.name, "The JSON array contains no records."))
        for index, record in records:
            key = path.name if index is None else f"{path.name}[{index}]"
            if not isinstance(record, dict):
                entries.append(_file_error(key, "Expected a DMS record object."))
                continue
            errors = validate_record(record)
            entries.append(RecordEntry(key, record, errors, get_warnings(record) if not errors else []))
    return entries
