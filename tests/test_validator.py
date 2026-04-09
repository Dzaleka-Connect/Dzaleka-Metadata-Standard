"""
Tests for the DMS Validator module.
"""

import json
import pytest
from pathlib import Path

from dms.validator import validate_record, validate_file, validate_directory, get_warnings


FIXTURES_DIR = Path(__file__).parent / "fixtures"
EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


class TestValidateRecord:
    """Tests for validate_record()."""

    def test_valid_minimal_record(self):
        """A record with only required fields should pass."""
        record = {
            "id": "b3e7c8a1-4d5f-6e7a-8b9c-0d1e2f3a4b5c",
            "title": "Test Record",
            "type": "story",
            "description": "A test heritage record.",
            "language": "en",
        }
        errors = validate_record(record)
        assert errors == [], f"Expected no errors, got: {errors}"

    def test_valid_full_record(self):
        """A record with all fields should pass."""
        record = json.loads(FIXTURES_DIR.joinpath("valid_record.json").read_text())
        errors = validate_record(record)
        assert errors == [], f"Expected no errors, got: {errors}"

    def test_missing_required_title(self):
        """Missing 'title' should produce an error."""
        record = {
            "id": "b3e7c8a1-4d5f-6e7a-8b9c-0d1e2f3a4b5c",
            "type": "story",
            "description": "A test record.",
            "language": "en",
        }
        errors = validate_record(record)
        assert len(errors) > 0
        assert any("title" in e["message"].lower() or "Title" in e["message"] for e in errors)

    def test_missing_required_type(self):
        """Missing 'type' should produce an error."""
        record = {
            "id": "b3e7c8a1-4d5f-6e7a-8b9c-0d1e2f3a4b5c",
            "title": "Test",
            "description": "A test record.",
            "language": "en",
        }
        errors = validate_record(record)
        assert len(errors) > 0

    def test_missing_required_description(self):
        """Missing 'description' should produce an error."""
        record = {
            "id": "b3e7c8a1-4d5f-6e7a-8b9c-0d1e2f3a4b5c",
            "title": "Test",
            "type": "story",
            "language": "en",
        }
        errors = validate_record(record)
        assert len(errors) > 0

    def test_missing_required_language(self):
        """Missing 'language' should produce an error."""
        record = {
            "id": "b3e7c8a1-4d5f-6e7a-8b9c-0d1e2f3a4b5c",
            "title": "Test",
            "type": "story",
            "description": "A test record.",
        }
        errors = validate_record(record)
        assert len(errors) > 0

    def test_missing_multiple_required_fields(self):
        """Missing multiple required fields should produce multiple errors."""
        record = {
            "id": "b3e7c8a1-4d5f-6e7a-8b9c-0d1e2f3a4b5c",
        }
        errors = validate_record(record)
        assert len(errors) >= 3  # title, type, description, language minus one for id

    def test_invalid_type_enum(self):
        """Invalid 'type' value should produce an error."""
        record = {
            "id": "b3e7c8a1-4d5f-6e7a-8b9c-0d1e2f3a4b5c",
            "title": "Test",
            "type": "unknown_type",
            "description": "A test record.",
            "language": "en",
        }
        errors = validate_record(record)
        assert len(errors) > 0
        assert any("unknown_type" in e["message"] for e in errors)

    def test_all_valid_types(self):
        """All enum type values should pass validation."""
        valid_types = ["story", "photo", "document", "audio", "video", "event", "map", "artwork", "site", "poem"]
        for t in valid_types:
            record = {
                "id": "b3e7c8a1-4d5f-6e7a-8b9c-0d1e2f3a4b5c",
                "title": "Test",
                "type": t,
                "description": "A test record.",
                "language": "en",
            }
            errors = validate_record(record)
            assert errors == [], f"Type '{t}' should be valid, got: {errors}"

    def test_invalid_language_format(self):
        """Language not matching BCP 47 pattern should fail."""
        record = {
            "id": "b3e7c8a1-4d5f-6e7a-8b9c-0d1e2f3a4b5c",
            "title": "Test",
            "type": "story",
            "description": "A test record.",
            "language": "english",  # Should be 'en'
        }
        errors = validate_record(record)
        assert len(errors) > 0

    def test_valid_language_codes(self):
        """Common language codes should pass."""
        codes = ["en", "sw", "fr", "rw", "so"]
        for code in codes:
            record = {
                "id": "b3e7c8a1-4d5f-6e7a-8b9c-0d1e2f3a4b5c",
                "title": "Test",
                "type": "story",
                "description": "A test record.",
                "language": code,
            }
            errors = validate_record(record)
            assert errors == [], f"Language '{code}' should be valid, got: {errors}"

    def test_empty_title_fails(self):
        """An empty title should fail validation."""
        record = {
            "id": "b3e7c8a1-4d5f-6e7a-8b9c-0d1e2f3a4b5c",
            "title": "",
            "type": "story",
            "description": "A test record.",
            "language": "en",
        }
        errors = validate_record(record)
        assert len(errors) > 0

    def test_additional_properties_rejected(self):
        """Unknown fields should be rejected."""
        record = {
            "id": "b3e7c8a1-4d5f-6e7a-8b9c-0d1e2f3a4b5c",
            "title": "Test",
            "type": "story",
            "description": "A test record.",
            "language": "en",
            "unknown_field": "should fail",
        }
        errors = validate_record(record)
        assert len(errors) > 0

    def test_invalid_access_level(self):
        """Invalid access_level should fail."""
        record = {
            "id": "b3e7c8a1-4d5f-6e7a-8b9c-0d1e2f3a4b5c",
            "title": "Test",
            "type": "story",
            "description": "A test record.",
            "language": "en",
            "rights": {
                "access_level": "top-secret",
            },
        }
        errors = validate_record(record)
        assert len(errors) > 0

    def test_valid_creator(self):
        """A well-formed creator array should pass."""
        record = {
            "id": "b3e7c8a1-4d5f-6e7a-8b9c-0d1e2f3a4b5c",
            "title": "Test",
            "type": "story",
            "description": "A test record.",
            "language": "en",
            "creator": [
                {"name": "Alice", "role": "author"},
                {"name": "Bob", "role": "editor", "affiliation": "Heritage Project"},
            ],
        }
        errors = validate_record(record)
        assert errors == [], f"Expected no errors, got: {errors}"

    def test_invalid_creator_role(self):
        """An invalid creator role should fail."""
        record = {
            "id": "b3e7c8a1-4d5f-6e7a-8b9c-0d1e2f3a4b5c",
            "title": "Test",
            "type": "story",
            "description": "A test record.",
            "language": "en",
            "creator": [
                {"name": "Alice", "role": "wizard"},
            ],
        }
        errors = validate_record(record)
        assert len(errors) > 0

    def test_location_with_coordinates(self):
        """A location with valid coordinates should pass."""
        record = {
            "id": "b3e7c8a1-4d5f-6e7a-8b9c-0d1e2f3a4b5c",
            "title": "Test",
            "type": "photo",
            "description": "A test record.",
            "language": "en",
            "location": {
                "name": "Dzaleka Refugee Camp",
                "area": "Market Area",
                "latitude": -13.7833,
                "longitude": 33.9833,
            },
        }
        errors = validate_record(record)
        assert errors == [], f"Expected no errors, got: {errors}"

    def test_location_invalid_latitude(self):
        """Latitude outside -90 to 90 should fail."""
        record = {
            "id": "b3e7c8a1-4d5f-6e7a-8b9c-0d1e2f3a4b5c",
            "title": "Test",
            "type": "photo",
            "description": "A test record.",
            "language": "en",
            "location": {
                "name": "Test",
                "latitude": 999,
                "longitude": 33.9833,
            },
        }
        errors = validate_record(record)
        assert len(errors) > 0

    def test_valid_typed_relation(self):
        """A typed relation should validate when target and type are present."""
        record = {
            "id": "b3e7c8a1-4d5f-6e7a-8b9c-0d1e2f3a4b5c",
            "title": "Test",
            "type": "story",
            "description": "A test record.",
            "language": "en",
            "relation_detail": [
                {
                    "target": "urn:dms:source-recording:test",
                    "relation_type": "transcription_of",
                }
            ],
        }
        errors = validate_record(record)
        assert errors == [], f"Expected no errors, got: {errors}"

    def test_invalid_typed_relation_type(self):
        """An unknown relation_type should fail."""
        record = {
            "id": "b3e7c8a1-4d5f-6e7a-8b9c-0d1e2f3a4b5c",
            "title": "Test",
            "type": "story",
            "description": "A test record.",
            "language": "en",
            "relation_detail": [
                {
                    "target": "urn:dms:source-recording:test",
                    "relation_type": "linked_to",
                }
            ],
        }
        errors = validate_record(record)
        assert len(errors) > 0

    def test_invalid_technical_metadata(self):
        """Negative technical values should fail."""
        record = {
            "id": "b3e7c8a1-4d5f-6e7a-8b9c-0d1e2f3a4b5c",
            "title": "Test",
            "type": "audio",
            "description": "A test record.",
            "language": "en",
            "technical": {
                "file_size_bytes": -1,
                "duration_seconds": -10,
            },
        }
        errors = validate_record(record)
        assert len(errors) > 0

    def test_invalid_rights_consent_status(self):
        """An unknown consent_status should fail."""
        record = {
            "id": "b3e7c8a1-4d5f-6e7a-8b9c-0d1e2f3a4b5c",
            "title": "Test",
            "type": "story",
            "description": "A test record.",
            "language": "en",
            "rights": {
                "consent_status": "maybe",
            },
        }
        errors = validate_record(record)
        assert len(errors) > 0


class TestValidateFile:
    """Tests for validate_file()."""

    def test_valid_fixture(self):
        """The valid fixture file should pass."""
        is_valid, errors = validate_file(FIXTURES_DIR / "valid_record.json")
        assert is_valid, f"Expected valid, got errors: {errors}"

    def test_invalid_fixture(self):
        """The invalid fixture file should fail."""
        is_valid, errors = validate_file(FIXTURES_DIR / "invalid_record.json")
        assert not is_valid
        assert len(errors) > 0

    def test_nonexistent_file(self):
        """A missing file should return an error."""
        is_valid, errors = validate_file("/nonexistent/file.json")
        assert not is_valid
        assert any("not found" in e["message"].lower() for e in errors)

    def test_non_json_file(self):
        """A non-.json file should be rejected."""
        is_valid, errors = validate_file(FIXTURES_DIR.parent.parent / "README.md")
        assert not is_valid


class TestValidateExamples:
    """All example records should be valid."""

    @pytest.mark.parametrize("filename", [
        "story.json",
        "photo.json",
        "document.json",
        "audio.json",
        "event.json",
        "site.json",
        "mural.json",
        "poem.json",
    ])
    def test_example_valid(self, filename):
        """Each example record should pass validation."""
        filepath = EXAMPLES_DIR / filename
        if not filepath.exists():
            pytest.skip(f"Example file {filename} not found")
        is_valid, errors = validate_file(filepath)
        assert is_valid, f"{filename} should be valid, got errors: {errors}"


class TestGetWarnings:
    """Tests for get_warnings()."""

    def test_minimal_record_has_warnings(self):
        """A minimal record should have warnings for missing recommended fields."""
        record = {
            "id": "test",
            "title": "Test",
            "type": "story",
            "description": "Test",
            "language": "en",
        }
        warnings = get_warnings(record)
        assert len(warnings) > 0
        assert any("Creator" in w for w in warnings)

    def test_full_record_no_warnings(self):
        """A full record should have no warnings."""
        record = json.loads(FIXTURES_DIR.joinpath("valid_record.json").read_text())
        warnings = get_warnings(record)
        assert warnings == []
