"""
Tests for the DMS Converter module.
"""

import json
import csv
import pytest
from pathlib import Path
from io import StringIO

from dms.converter import csv_to_json, json_to_csv, _csv_row_to_record, _record_to_csv_row


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


class TestCsvToJson:
    """Tests for CSV → JSON conversion."""

    def test_batch_csv_converts(self, tmp_path):
        """The example batch.csv should convert successfully."""
        csv_path = EXAMPLES_DIR / "batch.csv"
        if not csv_path.exists():
            pytest.skip("batch.csv not found")

        output = tmp_path / "output.json"
        records = csv_to_json(csv_path, output)

        assert len(records) == 5
        assert output.exists()

        with open(output) as f:
            data = json.load(f)
        assert len(data) == 5

    def test_required_fields_present(self, tmp_path):
        """Converted records should have all required fields."""
        csv_path = EXAMPLES_DIR / "batch.csv"
        if not csv_path.exists():
            pytest.skip("batch.csv not found")

        records = csv_to_json(csv_path, tmp_path / "out.json")
        for rec in records:
            assert "id" in rec
            assert "title" in rec
            assert "type" in rec
            assert "description" in rec
            assert "language" in rec

    def test_multivalue_creators(self):
        """Pipe-separated creators should be parsed into an array."""
        row = {
            "id": "test-id",
            "title": "Test",
            "type": "story",
            "description": "Test",
            "language": "en",
            "creator_name": "Alice|Bob|Charlie",
            "creator_role": "author|editor|translator",
        }
        record = _csv_row_to_record(row)
        assert len(record["creator"]) == 3
        assert record["creator"][0]["name"] == "Alice"
        assert record["creator"][0]["role"] == "author"
        assert record["creator"][2]["name"] == "Charlie"
        assert record["creator"][2]["role"] == "translator"

    def test_multivalue_subjects(self):
        """Pipe-separated subjects should become an array."""
        row = {
            "id": "test-id",
            "title": "Test",
            "type": "story",
            "description": "Test",
            "language": "en",
            "subject": "history|culture|music",
        }
        record = _csv_row_to_record(row)
        assert record["subject"] == ["history", "culture", "music"]

    def test_location_coordinates_parsed(self):
        """Latitude and longitude should be converted to floats."""
        row = {
            "id": "test-id",
            "title": "Test",
            "type": "photo",
            "description": "Test",
            "language": "en",
            "location_name": "Dzaleka",
            "location_area": "Market",
            "location_latitude": "-13.7833",
            "location_longitude": "33.9833",
        }
        record = _csv_row_to_record(row)
        assert record["location"]["latitude"] == -13.7833
        assert record["location"]["longitude"] == 33.9833

    def test_structured_fields_parsed(self):
        """Structured subject refs, technical metadata, and typed relations should parse."""
        row = {
            "id": "test-id",
            "title": "Test",
            "type": "story",
            "description": "Test",
            "language": "en",
            "creator_name": "Alice",
            "creator_identifier": "dms-person:alice",
            "subject_ref_identifier": "dms-subject:oral-history",
            "subject_ref_label": "oral history",
            "subject_ref_scheme": "DMS Subject Taxonomy",
            "location_name": "Dzaleka",
            "location_identifier": "dms-place:dzaleka",
            "rights_consent_status": "obtained",
            "rights_sensitivity": "trauma-sensitive|personal-data",
            "technical_filename": "test.txt",
            "technical_file_size_bytes": "12",
            "relation_detail_target": "urn:dms:test-source",
            "relation_detail_type": "transcription_of",
        }
        record = _csv_row_to_record(row)
        assert record["creator"][0]["identifier"] == "dms-person:alice"
        assert record["subject_ref"][0]["identifier"] == "dms-subject:oral-history"
        assert record["location"]["identifier"] == "dms-place:dzaleka"
        assert record["rights"]["consent_status"] == "obtained"
        assert record["rights"]["sensitivity"] == ["trauma-sensitive", "personal-data"]
        assert record["technical"]["file_size_bytes"] == 12
        assert record["relation_detail"][0]["relation_type"] == "transcription_of"

    def test_empty_optional_fields_omitted(self):
        """Empty optional fields should not appear in the record."""
        row = {
            "id": "test-id",
            "title": "Test",
            "type": "story",
            "description": "Test",
            "language": "en",
            "creator_name": "",
            "creator_role": "",
            "subject": "",
            "location_name": "",
            "format": "",
        }
        record = _csv_row_to_record(row)
        assert "creator" not in record
        assert "subject" not in record
        assert "location" not in record
        assert "format" not in record

    def test_auto_generates_id(self):
        """If id is empty, a UUID should be generated."""
        row = {
            "id": "",
            "title": "Test",
            "type": "story",
            "description": "Test",
            "language": "en",
        }
        record = _csv_row_to_record(row)
        assert len(record["id"]) == 36  # UUID format


class TestJsonToCsv:
    """Tests for JSON → CSV conversion."""

    def test_single_record_converts(self, tmp_path):
        """A single JSON record should convert to CSV."""
        json_path = EXAMPLES_DIR / "story.json"
        if not json_path.exists():
            pytest.skip("story.json not found")

        output = tmp_path / "output.csv"
        csv_content = json_to_csv(json_path, output)

        assert output.exists()
        reader = csv.DictReader(StringIO(csv_content))
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["title"] == "Journey to Dzaleka: A Story of Hope"

    def test_array_converts(self, tmp_path):
        """A JSON array of records should produce multiple CSV rows."""
        # First create a JSON array file
        records = [
            {
                "id": "id-1",
                "title": "Record 1",
                "type": "story",
                "description": "First",
                "language": "en",
            },
            {
                "id": "id-2",
                "title": "Record 2",
                "type": "photo",
                "description": "Second",
                "language": "fr",
            },
        ]
        json_path = tmp_path / "array.json"
        with open(json_path, "w") as f:
            json.dump(records, f)

        csv_content = json_to_csv(json_path)
        reader = csv.DictReader(StringIO(csv_content))
        rows = list(reader)
        assert len(rows) == 2

    def test_creators_flattened(self):
        """Creator array should be flattened with pipe separators."""
        record = {
            "creator": [
                {"name": "Alice", "role": "author"},
                {"name": "Bob", "role": "editor"},
            ]
        }
        row = _record_to_csv_row(record)
        assert row["creator_name"] == "Alice|Bob"
        assert row["creator_role"] == "author|editor"

    def test_subjects_flattened(self):
        """Subject array should be pipe-separated."""
        record = {"subject": ["history", "culture", "music"]}
        row = _record_to_csv_row(record)
        assert row["subject"] == "history|culture|music"

    def test_structured_fields_flattened(self):
        """Structured v1.1 fields should flatten into CSV columns."""
        record = {
            "creator": [{"name": "Alice", "identifier": "dms-person:alice", "role": "author"}],
            "subject_ref": [{"identifier": "dms-subject:oral-history", "label": "oral history", "scheme": "DMS Subject Taxonomy"}],
            "location": {"name": "Dzaleka", "identifier": "dms-place:dzaleka"},
            "rights": {"consent_status": "obtained", "sensitivity": ["trauma-sensitive"]},
            "technical": {"filename": "test.txt", "file_size_bytes": 12},
            "relation_detail": [{"target": "urn:dms:test-source", "relation_type": "transcription_of"}],
        }
        row = _record_to_csv_row(record)
        assert row["creator_identifier"] == "dms-person:alice"
        assert row["subject_ref_identifier"] == "dms-subject:oral-history"
        assert row["location_identifier"] == "dms-place:dzaleka"
        assert row["rights_consent_status"] == "obtained"
        assert row["rights_sensitivity"] == "trauma-sensitive"
        assert row["technical_file_size_bytes"] == 12
        assert row["relation_detail_type"] == "transcription_of"


class TestRoundTrip:
    """Tests for CSV → JSON → CSV round-trip fidelity."""

    def test_roundtrip_preserves_data(self, tmp_path):
        """Converting CSV → JSON → CSV should preserve field values."""
        csv_path = EXAMPLES_DIR / "batch.csv"
        if not csv_path.exists():
            pytest.skip("batch.csv not found")

        # CSV → JSON
        json_output = tmp_path / "records.json"
        records = csv_to_json(csv_path, json_output)

        # JSON → CSV
        csv_output = tmp_path / "roundtrip.csv"
        json_to_csv(json_output, csv_output)

        # Read both CSV files and compare key fields
        with open(csv_path) as f:
            original_rows = list(csv.DictReader(f))

        with open(csv_output) as f:
            roundtrip_rows = list(csv.DictReader(f))

        assert len(original_rows) == len(roundtrip_rows)

        for orig, rt in zip(original_rows, roundtrip_rows):
            assert orig["title"] == rt["title"]
            assert orig["type"] == rt["type"]
            assert orig["language"] == rt["language"]
            assert orig["id"] == rt["id"]
