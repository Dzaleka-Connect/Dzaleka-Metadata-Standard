"""Read published Dzaleka Services collections and prepare reviewable DMS drafts."""

import copy
import json
import math
import re
import ssl
import time
import uuid
from datetime import date
from threading import Lock
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlparse
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

import certifi

from dms.schema import get_schema_version
from dms import __version__

BASE_URL = "https://services.dzaleka.com"
COLLECTIONS = {
    "encyclopedia": {"label": "Encyclopedia", "path": "/api/encyclopedia", "type": "document", "items_key": "entries", "paginated": True},
    "artworks": {"label": "Public art", "path": "/api/artworks", "type": "artwork", "items_key": "artworks"},
    "photos": {"label": "Photos", "path": "/api/photos", "type": "photo", "items_key": "photos"},
    "events": {"label": "Events", "path": "/api/events", "type": "event", "items_key": "events"},
    "community-voices": {"label": "Community stories", "path": "/api/community-voices", "type": "story", "items_key": "community-voices"},
    "resources": {"label": "Resources", "path": "/api/resources", "type": "document", "items_key": "resources"},
    "news": {"label": "News", "path": "/api/news", "type": "document", "items_key": "news"},
    "poets": {"label": "Poets", "path": "/api/poets", "type": "document", "items_key": "poets"},
    "artists": {"label": "Artists", "path": "/api/artists", "type": "document", "items_key": "artists"},
    "dancers": {"label": "Dancers", "path": "/api/dancers", "type": "document", "items_key": "dancers"},
    "services": {"label": "Services", "path": "/api/services", "type": "document", "items_key": "services"},
    "spatial": {"label": "Places and sites", "path": "/api/v1/spatial.json", "type": "site", "items_key": "features"},
}
ENCYCLOPEDIA_TYPES = {
    "person": "document", "organization": "document", "place": "site", "overview": "document",
    "event": "event", "film": "video", "book": "document", "topic": "document",
}
DIRECTORY_ROLES = {"poets": "poet", "artists": "artist", "dancers": "artist"}
MAX_BYTES = 8 * 1024 * 1024
CACHE_SECONDS = 300
MAX_PAGES = 20


class ServicesError(Exception):
    def __init__(self, message, status=502, retry_after=None):
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _ssl_context() -> ssl.SSLContext:
    """Use certifi so macOS Python.org builds can verify public HTTPS certificates."""
    return ssl.create_default_context(cafile=certifi.where())


def _opener():
    return build_opener(_NoRedirect(), HTTPSHandler(context=_ssl_context()))


def _unreachable_message(error: BaseException) -> str:
    text = f"{error} {getattr(error, 'reason', '')}".lower()
    if "certificate" in text or isinstance(getattr(error, "reason", None), ssl.SSLError):
        return "Cannot verify the Dzaleka Services HTTPS certificate. Update certifi or run Python's Install Certificates command."
    if "timed out" in text or isinstance(error, TimeoutError):
        return "Dzaleka Services timed out. Try again."
    return "Cannot reach Dzaleka Services. Check your connection and try again."


def collection_list():
    return [{"id": key, "label": spec["label"], "url": BASE_URL + spec["path"]}
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


def _license_text(value):
    if isinstance(value, dict):
        return _text(value.get("name")) or _text(value.get("url"))
    return _text(value)


def _payload_items(collection, payload):
    spec = COLLECTIONS[collection]
    if collection == "spatial":
        return payload.get("features")
    container = payload.get("data")
    return container.get(spec["items_key"]) if isinstance(container, dict) else None


def _encyclopedia_tags(data):
    tags = [_text(data.get("category")), _text(data.get("entryType"))]
    aliases = data.get("aliases")
    if isinstance(aliases, list):
        tags.extend(_text(alias) for alias in aliases)
    return list(dict.fromkeys(tag for tag in tags if tag))


def _encyclopedia_location(data):
    facts = data.get("facts")
    if not isinstance(facts, list):
        return ""
    for fact in facts:
        if not isinstance(fact, dict):
            continue
        label = _text(fact.get("label")).casefold()
        if label in {"location", "raised in", "based in"}:
            return _text(fact.get("value"))
    return ""


def _record_type(collection, data):
    if collection == "encyclopedia":
        return ENCYCLOPEDIA_TYPES.get(_text(data.get("entryType")), COLLECTIONS[collection]["type"])
    return COLLECTIONS[collection]["type"]


def normalize_collection(collection, payload):
    """Keep source identity explicit; never infer permission from publication."""
    spec = COLLECTIONS[collection]
    if not isinstance(payload, dict):
        raise ServicesError("Dzaleka Services returned an unexpected response.")
    items = _payload_items(collection, payload)
    if not isinstance(items, list):
        raise ServicesError("Dzaleka Services returned an unexpected collection format.")
    spatial = collection == "spatial"
    result = []
    for item in items:
        if not isinstance(item, dict):
            continue
        data = item.get("properties") if spatial else item
        if not isinstance(data, dict):
            continue
        identifier = _text(item.get("id")) or _text(data.get("id")) or _text(data.get("slug"))
        title = _text(data.get("title")) or _text(data.get("name"))
        if not identifier or not title:
            continue
        source_uri = BASE_URL + spec["path"] + "#" + quote(identifier, safe="")
        description = next((_text(data.get(key)) for key in
                            ("description", "summary", "excerpt", "detailedDescription")
                            if _text(data.get(key))), "")
        raw_creator = next((data[key] for key in
                            ("photographer", "artistName", "author", "organizer")
                            if data.get(key)), "")
        creator = _text(raw_creator.get("name")) if isinstance(raw_creator, dict) else _text(raw_creator)
        if not creator and collection in DIRECTORY_ROLES:
            creator = title
        raw_tags = data.get("tags", [])
        tags = list(dict.fromkeys(_text(tag) for tag in raw_tags if _text(tag))) if isinstance(raw_tags, list) else []
        if collection == "encyclopedia":
            tags = list(dict.fromkeys(tags + _encyclopedia_tags(data)))
        location = _text(data.get("location")) or _text(data.get("birthplace")) or (
            _text(data.get("name")) if spatial else "")
        if collection == "encyclopedia" and not location:
            location = _encyclopedia_location(data)
        license_text = _license_text(data.get("license")) or _license_text(payload.get("license"))
        attribution = _text(payload.get("attribution"))
        payload_license = payload.get("license")
        if isinstance(payload_license, dict):
            attribution = attribution or _text(payload_license.get("attribution"))
        entry = {
            "identifier": identifier, "title": title, "description": description,
            "collection": collection, "collection_label": spec["label"], "type": _record_type(collection, data),
            "source_uri": source_uri, "url": _safe_url(data.get("url")) or source_uri,
            "creator": creator, "tags": tags, "location": location,
            "area": _text(data.get("zone")) or _text(data.get("campZone")),
            "source_date": (_text(data.get("date")) or _text(data.get("dateInstalled"))
                            or _text(data.get("surveyDate")) or _text(data.get("datePublished"))
                            or _text(data.get("lastReviewed"))),
            "reviewed": _text(data.get("lastReviewed")),
            "license": license_text, "attribution": attribution,
            "related": [],
        }
        related = data.get("relatedEntries")
        if isinstance(related, list):
            entry["related"] = [_text(slug) for slug in related if _text(slug)][:10]
        # Portraits and event illustrations are not the digital representation of the item.
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
    spec = COLLECTIONS[entry["collection"]]
    record = {
        "id": str(uuid.uuid4()), "title": entry["title"], "type": entry["type"],
        "description": entry["description"], "language": "",
        "date": {"created": date.today().isoformat()},
        "source": {"collection": entry["collection_label"],
                   "collection_identifier": BASE_URL + spec["path"],
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
        roles = {"photos": "photographer", "artworks": "artist", "events": "organizer", **DIRECTORY_ROLES}
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
    for slug in entry.get("related") or []:
        record["relation_detail"].append({
            "target": BASE_URL + "/api/encyclopedia#" + quote(slug, safe=""),
            "relation_type": "references",
            "label": slug,
        })
    raw_date = entry.get("source_date", "")
    if raw_date:
        try:
            if not re.match(r"^\d{4}-\d{2}-\d{2}(?:T|$)", raw_date):
                raise ValueError
            record["date"]["event_date"] = date.fromisoformat(raw_date[:10]).isoformat()
        except ValueError:
            record["coverage"] = {"period": raw_date}
    reviewed = entry.get("reviewed", "")
    if reviewed and re.match(r"^\d{4}-\d{2}-\d{2}(?:T|$)", reviewed):
        record["date"]["modified"] = date.fromisoformat(reviewed[:10]).isoformat()
    return record


def _request_path(collection, page=1):
    spec = COLLECTIONS[collection]
    if spec.get("paginated"):
        return f"{spec['path']}?perPage=100&page={int(page)}"
    return spec["path"]


class ServicesClient:
    def __init__(self):
        self._cache = {}
        self._lock = Lock()
        self._retry_at = 0

    def _read_json(self, path):
        request = Request(BASE_URL + path, headers={
            "Accept": "application/json", "API-Version": "1.0.0", "User-Agent": f"DMS/{__version__}"})
        try:
            with _opener().open(request, timeout=20) as response:
                body = response.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise ServicesError("Source response is too large to load.")
            return json.loads(body)
        except HTTPError as error:
            if error.code == 429:
                raw_retry = error.headers.get("Retry-After", "60")
                retry = min(3600, max(1, int(raw_retry))) if raw_retry.isdigit() else 60
                self._retry_at = time.monotonic() + retry
                raise ServicesError("Dzaleka Services is busy. Try again shortly.", 429, retry) from error
            raise ServicesError("Dzaleka Services could not load this collection.") from error
        except (URLError, OSError, TimeoutError) as error:
            raise ServicesError(_unreachable_message(error), 503) from error
        except (ValueError, UnicodeError) as error:
            raise ServicesError("Dzaleka Services returned unreadable data.") from error

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
            payload = self._read_json(_request_path(collection))
            entries = normalize_collection(collection, payload)
            if COLLECTIONS[collection].get("paginated"):
                meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
                total_pages = meta.get("totalPages")
                if isinstance(total_pages, int) and total_pages > 1:
                    for page in range(2, min(total_pages, MAX_PAGES) + 1):
                        entries.extend(normalize_collection(collection, self._read_json(_request_path(collection, page))))
            self._cache[collection] = (time.monotonic(), entries)
            return copy.deepcopy(entries), False
