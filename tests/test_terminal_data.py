"""Tests for the read-only terminal collection reader."""

import json
from pathlib import Path

from dms.schema import load_schema
from dms.terminal_data import (
    collection_counts,
    compact_path,
    display_text,
    read_collection,
    resolve_schema_field,
)

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_display_text_strips_control_characters_and_rejects_bools():
    assert display_text("Title\x1b[31m") == "Title[31m"
    assert display_text(True) == "Not recorded"
    assert display_text({"name": "x"}) == "Not recorded"
    assert display_text("  \n  ") == "Not recorded"
    assert display_text(4) == "4"


def test_compact_path_uses_home_prefix(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    nested = tmp_path / "records"
    nested.mkdir()
    assert compact_path(nested) == "~/records"
    assert compact_path(tmp_path) == "~"
    deep = tmp_path / "Documents" / "Dzaleka Digital Heritage" / "Dzaleka Metadata Standard" / "examples"
    deep.mkdir(parents=True)
    shortened = compact_path(deep)
    assert shortened.startswith("…/")
    assert shortened.endswith("examples")


def test_read_collection_keeps_invalid_and_unreadable_files(tmp_path):
    (tmp_path / "ok.json").write_text(FIXTURES_DIR.joinpath("valid_record.json").read_text())
    (tmp_path / "bad.json").write_text("{")
    (tmp_path / "list.json").write_text(json.dumps([{"title": "only title"}, "not-an-object"]))
    (tmp_path / "empty.json").write_text("[]")
    entries = read_collection(tmp_path)
    keys = [entry.key for entry in entries]
    assert "ok.json" in keys
    assert "bad.json" in keys
    assert "list.json[0]" in keys
    assert "list.json[1]" in keys
    assert "empty.json" in keys
    by_key = {entry.key: entry for entry in entries}
    assert by_key["ok.json"].status in {"Valid", "Review"}
    assert by_key["bad.json"].status == "Invalid"
    assert by_key["list.json[1]"].errors[0]["message"] == "Expected a DMS record object."
    assert by_key["empty.json"].errors[0]["message"] == "The JSON array contains no records."


def test_read_collection_honors_size_limit(tmp_path, monkeypatch):
    monkeypatch.setattr("dms.terminal_data.MAX_RECORD_BYTES", 8)
    (tmp_path / "huge.json").write_text('{"title": "too big"}')
    entries = read_collection(tmp_path)
    assert entries[0].status == "Invalid"
    assert "8 MB" in entries[0].errors[0]["message"]


def test_read_collection_missing_directory(tmp_path):
    assert read_collection(tmp_path / "missing") == []


def test_examples_are_readable():
    entries = read_collection(EXAMPLES_DIR)
    assert any(entry.key == "story.json" and entry.record for entry in entries)
    total, valid, invalid, review = collection_counts(entries)
    assert total == len(entries)
    assert valid + invalid == total
    assert review >= 0


def test_record_entry_filters():
    entries = read_collection(EXAMPLES_DIR)
    story = next(entry for entry in entries if entry.record and entry.record.get("type") == "story")
    assert story.matches("hope")
    assert story.matches("", "story")
    assert not story.matches("", "poem")
    review_hits = [entry for entry in entries if entry.matches("", "all", review_only=True)]
    assert all(entry.errors or entry.warnings for entry in review_hits)


def test_resolve_schema_field_merges_ref():
    schema = load_schema()
    rights = resolve_schema_field(schema, "rights")
    assert "properties" in rights or "$ref" in rights
    title = resolve_schema_field(schema, "title")
    assert "description" in title
