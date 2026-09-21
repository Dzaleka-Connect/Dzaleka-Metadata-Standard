import json
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest

from dms.services import ServicesClient, ServicesError, normalize_collection, source_to_draft
from dms.validator import validate_record


def artwork(**fields):
    payload = {"data": {"artworks": [{"id": "mural-1", "title": "Community mural", **fields}]}}
    return normalize_collection("artworks", payload)[0]


def test_artwork_draft_requires_review_without_inventing_details():
    draft = source_to_draft(artwork(artistName="Unknown", dateInstalled="Approximate, 2013"))
    assert draft["language"] == draft["description"] == ""
    assert "creator" not in draft
    assert "event_date" not in draft["date"]
    assert draft["coverage"]["period"] == "Approximate, 2013"
    assert draft["rights"]["access_level"] == "restricted"
    assert draft["rights"]["consent_status"] == "unknown"
    assert "license" not in draft["rights"]
    assert draft["relation_detail"][0]["target"].endswith("/api/artworks#mural-1")
    draft.update(language="en", description="Painted with community participation.")
    assert validate_record(draft) == []


@pytest.mark.parametrize("raw,expected", [("2024-06-20T12:00:00Z", "2024-06-20"), ("2026-06", None), ("2024-02-31", None)])
def test_dates_preserve_uncertainty(raw, expected):
    draft = source_to_draft(artwork(dateInstalled=raw))
    assert draft["date"].get("event_date") == expected
    if expected is None:
        assert draft["coverage"]["period"] == raw


def test_spatial_coordinates_and_attribution_are_preserved():
    payload = {"type": "FeatureCollection", "license": "CC-BY-4.0", "attribution": "Community map contributors", "features": [
        {"id": "zero", "properties": {"name": "Origin", "summary": "Survey point"},
         "geometry": {"type": "Point", "coordinates": [0, 0]}},
        {"id": "bad", "properties": {"name": "Bad coordinates"}, "geometry": {"type": "Point", "coordinates": [True, 200]}},
        {"id": "null", "properties": {"name": "No geometry"}, "geometry": None},
    ]}
    entries = normalize_collection("spatial", payload)
    draft = source_to_draft(entries[0])
    assert draft["location"]["latitude"] == draft["location"]["longitude"] == 0
    assert draft["rights"]["license"] == "CC-BY-4.0"
    assert "Community map contributors" in draft["rights"]["access_note"]
    assert all("latitude" not in entry for entry in entries[1:])


def test_photo_file_and_creator_mapping_and_unsafe_urls():
    payload = {"data": {"photos": [{"id": "p1", "title": "Photo", "image": "/photo.jpg", "photographer": {"name": "Amina"}, "tags": ["art", "art", None]}]}}
    entry = normalize_collection("photos", payload)[0]
    draft = source_to_draft(entry)
    assert draft["creator"] == [{"name": "Amina", "role": "photographer"}]
    assert draft["technical"]["file_uri"] == "https://services.dzaleka.com/photo.jpg"
    assert draft["subject"] == ["art"]
    payload["data"]["photos"][0]["image"] = "javascript:alert(1)"
    assert normalize_collection("photos", payload)[0]["file_uri"] == ""


@pytest.mark.parametrize("url,expected", [("/images/Camp photo.jpg", "https://services.dzaleka.com/images/Camp%20photo.jpg"),
                                         ("/images/Camp%20photo.jpg", "https://services.dzaleka.com/images/Camp%20photo.jpg"),
                                         ("https://[invalid", "")])
def test_source_file_urls_are_encoded_and_malformed_urls_are_ignored(url, expected):
    entry = normalize_collection("photos", {"data": {"photos": [{"id": "p1", "title": "Photo", "image": url}]}})[0]
    assert entry["file_uri"] == expected


@pytest.mark.parametrize("collection", ["artworks", "photos", "events", "community-voices", "resources", "news"])
def test_supported_collection_envelopes(collection):
    entries = normalize_collection(collection, {"data": {collection: [{"id": "one", "title": "One"}]}})
    assert len(entries) == 1
    draft = source_to_draft(entries[0])
    draft.update(language="en", description="Reviewed description")
    assert validate_record(draft) == []


@pytest.mark.parametrize("payload", [None, [], {}, {"data": []}, {"data": {"artworks": {}}}])
def test_bad_envelopes_fail_cleanly(payload):
    with pytest.raises(ServicesError):
        normalize_collection("artworks", payload)


def test_cache_is_defensive_and_expiration_fetches_again():
    response = MagicMock()
    response.__enter__.return_value.read.return_value = json.dumps({"data": {"artworks": [{"id": "one", "title": "One"}]}}).encode()
    with patch("dms.services.build_opener") as opener, patch("dms.services.time.monotonic", return_value=0) as clock:
        opener.return_value.open.return_value = response
        client = ServicesClient()
        entries, cached = client.fetch("artworks")
        assert not cached
        entries[0]["title"] = "Changed"
        second, cached = client.fetch("artworks")
        assert cached and second[0]["title"] == "One"
        assert opener.return_value.open.call_count == 1
        clock.return_value = 301
        assert client.fetch("artworks")[1] is False
        assert opener.return_value.open.call_count == 2


def test_rate_limit_is_respected_across_collections():
    with patch("dms.services.build_opener") as opener:
        opener.return_value.open.side_effect = HTTPError("url", 429, "busy", {"Retry-After": "30"}, None)
        client = ServicesClient()
        for collection in ("artworks", "photos"):
            with pytest.raises(ServicesError) as result:
                client.fetch(collection)
            assert result.value.status == 429
            assert 0 < result.value.retry_after <= 30
        assert opener.return_value.open.call_count == 1


def test_unknown_collection_never_connects():
    with patch("dms.services.build_opener") as opener:
        with pytest.raises(ServicesError) as result:
            ServicesClient().fetch("../../other-host")
        assert result.value.status == 404
        opener.assert_not_called()


def test_offline_error_is_actionable():
    with patch("dms.services.build_opener") as opener:
        opener.return_value.open.side_effect = URLError("offline")
        with pytest.raises(ServicesError) as result:
            ServicesClient().fetch("artworks")
        assert result.value.status == 503
