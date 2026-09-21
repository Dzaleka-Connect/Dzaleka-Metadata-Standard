"""Read published Dzaleka Services collections and prepare reviewable DMS drafts."""

import copy
import json
import math
import re
import time
import uuid
from datetime import date
from threading import Lock
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from dms.schema import get_schema_version
from dms import __version__

BASE_URL = "https://services.dzaleka.com"
COLLECTIONS = {
    "artworks": ("Public art", "/api/artworks", "artwork"),
    "photos": ("Photos", "/api/photos", "photo"),
    "events": ("Events", "/api/events", "event"),
    "community-voices": ("Community stories", "/api/community-voices", "story"),
    "resources": ("Resources", "/api/resources", "document"),
    "news": ("News", "/api/news", "document"),
    "spatial": ("Places and sites", "/api/v1/spatial.json", "site"),
}
MAX_BYTES = 8 * 1024 * 1024
CACHE_SECONDS = 300


class ServicesError(Exception):
    def __init__(self, message, status=502, retry_after=None):
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def collection_list():
    return [{"id": key, "label": spec[0], "url": BASE_URL + spec[1]}
            for key, spec in COLLECTIONS.items()]


def _text(value):
    return value.strip() if isinstance(value, str) else ""


def _safe_url(value):
    value = _text(value)
    if not value:
        return ""
    try:
        url = urljoin(BASE_URL, value)
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username:
            return ""
        parsed.port  # Reject malformed ports before returning a browser link.
    except ValueError:
        return ""
    return quote(url, safe=":/?#[]@!$&'()*+,;=%")


def normalize_collection(collection, payload):
    """Keep source identity explicit; never infer permission from publication."""
    label, path, record_type = COLLECTIONS[collection]
    if not isinstance(payload, dict):
        raise ServicesError("Dzaleka Services returned an unexpected response.")
    spatial = collection == "spatial"
    container = payload.get("data")
    items = payload.get("features") if spatial else (
        container.get(collection) if isinstance(container, dict) else None)
    if not isinstance(items, list):
        raise ServicesError("Dzaleka Services returned an unexpected collection format.")
    result = []
    for item in items:
        if not isinstance(item, dict):
            continue
        data = item.get("properties") if spatial else item
        if not isinstance(data, dict):
            continue
        identifier = _text(item.get("id")) or _text(data.get("id"))
        title = _text(data.get("title")) or _text(data.get("name"))
        if not identifier or not title:
            continue
        source_uri = BASE_URL + path + "#" + quote(identifier, safe="")
        description = next((_text(data.get(key)) for key in
                            ("description", "summary", "excerpt", "detailedDescription")
                            if _text(data.get(key))), "")
        raw_creator = next((data[key] for key in
                            ("photographer", "artistName", "author", "organizer")
                            if data.get(key)), "")
        creator = _text(raw_creator.get("name")) if isinstance(raw_creator, dict) else _text(raw_creator)
        raw_tags = data.get("tags", [])
        tags = list(dict.fromkeys(_text(tag) for tag in raw_tags if _text(tag))) if isinstance(raw_tags, list) else []
        location = _text(data.get("location")) or (_text(data.get("name")) if spatial else "")
        entry = {
            "identifier": identifier, "title": title, "description": description,
            "collection": collection, "collection_label": label, "type": record_type,
            "source_uri": source_uri, "url": _safe_url(data.get("url")) or source_uri,
            "creator": creator, "tags": tags, "location": location,
            "area": _text(data.get("zone")) or _text(data.get("campZone")),
            "source_date": _text(data.get("date")) or _text(data.get("dateInstalled")) or _text(data.get("surveyDate")),
            "license": _text(data.get("license")) or (_text(payload.get("license")) if spatial else ""),
            "attribution": _text(payload.get("attribution")) if spatial else "",
        }
        # Event/story illustrations are not the digital representation of the item.
        file_value = data.get("image") if collection == "photos" else data.get("downloadUrl")
        entry["file_uri"] = _safe_url(file_value)
        geometry = item.get("geometry") or {}
        geometry = geometry if isinstance(geometry, dict) else {}
        coords = geometry.get("coordinates")
        if spatial and geometry.get("type") == "Point" and isinstance(coords, list) and len(coords) >= 2:
            lon, lat = coords[:2]
            if all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in (lon, lat)) and -180 <= lon <= 180 and -90 <= lat <= 90:
                entry["latitude"], entry["longitude"] = lat, lon
        result.append(entry)
    return result


def source_to_draft(entry):
    record = {
        "id": str(uuid.uuid4()), "title": entry["title"], "type": entry["type"],
        "description": entry["description"], "language": "",
        "date": {"created": date.today().isoformat()},
        "source": {"collection": entry["collection_label"],
                   "collection_identifier": BASE_URL + COLLECTIONS[entry["collection"]][1],
                   "contributor": "Dzaleka Online Services"},
        "relation_detail": [{"target": entry["source_uri"], "relation_type": "references",
                             "label": entry["title"]}],
        "rights": {"access_level": "restricted", "consent_status": "unknown",
                   "access_note": "Imported from a published source. Review consent and reuse rights before sharing."},
        "schema_version": get_schema_version(),
    }
    if entry.get("license"):
        record["rights"]["license"] = entry["license"]
    if entry.get("attribution"):
        record["rights"]["access_note"] += " Source attribution: " + entry["attribution"]
    if entry.get("creator") and entry["creator"].lower() != "unknown":
        roles = {"photos": "photographer", "artworks": "artist", "events": "organizer"}
        record["creator"] = [{"name": entry["creator"], "role": roles.get(entry["collection"], "author")}]
    if entry.get("tags"):
        record["subject"] = list(entry["tags"])
    if entry.get("location"):
        record["location"] = {"name": entry["location"]}
        if entry.get("area"):
            record["location"]["area"] = entry["area"]
        if entry["collection"] == "spatial":
            record["location"]["identifier"] = entry["source_uri"]
        for key in ("latitude", "longitude"):
            if key in entry:
                record["location"][key] = entry[key]
    if entry.get("file_uri"):
        record["technical"] = {"file_uri": entry["file_uri"]}
    raw_date = entry.get("source_date", "")
    if raw_date:
        try:
            if not re.match(r"^\d{4}-\d{2}-\d{2}(?:T|$)", raw_date):
                raise ValueError
            record["date"]["event_date"] = date.fromisoformat(raw_date[:10]).isoformat()
        except ValueError:
            record["coverage"] = {"period": raw_date}
    return record


class ServicesClient:
    def __init__(self):
        self._cache = {}
        self._lock = Lock()
        self._retry_at = 0

    def fetch(self, collection):
        if collection not in COLLECTIONS:
            raise ServicesError("Unknown source collection.", 404)
        with self._lock:
            now = time.monotonic()
            cached = self._cache.get(collection)
            if cached and now - cached[0] < CACHE_SECONDS:
                return copy.deepcopy(cached[1]), True
            if now < self._retry_at:
                raise ServicesError("Dzaleka Services is busy. Try again shortly.", 429, math.ceil(self._retry_at - now))
            request = Request(BASE_URL + COLLECTIONS[collection][1], headers={
                "Accept": "application/json", "API-Version": "1.0.0", "User-Agent": f"DMS/{__version__}"})
            try:
                with build_opener(_NoRedirect()).open(request, timeout=10) as response:
                    body = response.read(MAX_BYTES + 1)
                if len(body) > MAX_BYTES:
                    raise ServicesError("Source response is too large to load.")
                entries = normalize_collection(collection, json.loads(body))
            except HTTPError as error:
                if error.code == 429:
                    raw_retry = error.headers.get("Retry-After", "60")
                    retry = min(3600, max(1, int(raw_retry))) if raw_retry.isdigit() else 60
                    self._retry_at = time.monotonic() + retry
                    raise ServicesError("Dzaleka Services is busy. Try again shortly.", 429, retry) from error
                raise ServicesError("Dzaleka Services could not load this collection.") from error
            except (URLError, OSError, TimeoutError) as error:
                raise ServicesError("Cannot reach Dzaleka Services. Check your connection and try again.", 503) from error
            except (ValueError, UnicodeError) as error:
                raise ServicesError("Dzaleka Services returned unreadable data.") from error
            self._cache[collection] = (time.monotonic(), entries)
            return copy.deepcopy(entries), False
