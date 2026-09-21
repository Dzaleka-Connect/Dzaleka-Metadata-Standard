import json
import threading
import uuid
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen
from unittest.mock import patch

import pytest

from dms.services import ServicesError
from dms.web import bind_local_server, make_handler


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    directory = tmp_path_factory.mktemp("web-records")
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(directory))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}", directory
    server.shutdown()
    server.server_close()
    thread.join()


def request(server, path, data=None):
    req = Request(server[0] + path, data=json.dumps(data).encode() if data is not None else None,
                  headers={"Content-Type": "application/json"})
    return urlopen(req)


def record(**fields):
    return {"id": str(uuid.uuid4()), "title": "Test record", "type": "story", "description": "A story.", "language": "en", **fields}


def test_bind_falls_back_when_the_requested_port_is_busy(tmp_path):
    handler = make_handler(tmp_path)
    busy = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    try:
        taken = busy.server_address[1]
        with pytest.raises(OSError) as error:
            bind_local_server(handler, taken, fallback=False)
        assert "already in use" in error.value.strerror
        server = bind_local_server(handler, taken, fallback=True)
        try:
            assert server.server_address[1] != taken
        finally:
            server.server_close()
    finally:
        busy.server_close()


def test_static_ui_and_schema_are_self_contained(server):
    with request(server, "/") as response:
        html = response.read().decode()
        assert '/static/app.js' in html
        assert "script-src 'self';" in response.headers["Content-Security-Policy"]
    for asset in ("app.js", "app.css"):
        with request(server, "/static/" + asset) as response:
            assert response.status == 200 and len(response.read()) > 1000
    with request(server, "/api/schema") as response:
        schema = json.load(response)["schema"]
        assert "Technical" in schema["$defs"]


def test_save_updates_legacy_filename_after_type_change(server):
    data = record()
    legacy = server[1] / ("story_" + data["id"][:8] + ".json")
    legacy.write_text(json.dumps(data))
    data.update(type="photo", location={"name": "Zero point", "latitude": 0, "longitude": 0}, technical={"file_size_bytes": 0})
    with request(server, "/api/save", data) as response:
        result = json.load(response)
        assert result["file"] == legacy.name
    assert json.loads(legacy.read_text()) == data
    assert not (server[1] / f"{data['id']}.json").exists()
    assert not list(server[1].glob(".dms-*.tmp"))


def test_new_ids_with_same_prefix_do_not_collide(server):
    first = record(id="12345678-1234-4234-8234-123456789012")
    second = record(id="12345678-1234-4234-8234-123456789013")
    filenames = []
    for data in (first, second):
        with request(server, "/api/save", data) as response:
            filenames.append(json.load(response)["file"])
    assert filenames[0] != filenames[1]


@pytest.mark.parametrize("fields", [{"id": "../../bad"}, {"date": {"event_date": "2024-02-31"}}, {"technical": {"file_uri": "not a URI"}}])
def test_invalid_formats_rejected(server, fields):
    with pytest.raises(HTTPError) as result:
        request(server, "/api/save", record(**fields))
    assert result.value.code == 400
    assert any(error["validator"] == "format" for error in json.load(result.value)["errors"])


def test_encoded_term_identifier_and_unknown_vocabulary(server):
    with request(server, "/api/taxonomy/relation_types/terms/" + quote("dms:relation-type/has_part", safe="")) as response:
        assert json.load(response)["id"] == "dms:relation-type/has_part"
    with pytest.raises(HTTPError) as error:
        request(server, "/api/taxonomy/missing/terms")
    assert error.value.code == 404


def test_source_rate_limit_header_and_catalog_without_network(server):
    with patch("dms.services.ServicesClient.fetch", side_effect=ServicesError("Busy", 429, 30)) as fetch:
        with request(server, "/api/sources") as response:
            collections = json.load(response)["collections"]
            assert len(collections) == 12
            assert {item["id"] for item in collections} >= {"encyclopedia", "poets"}
        fetch.assert_not_called()
        with pytest.raises(HTTPError) as error:
            request(server, "/api/sources/artworks")
        assert error.value.headers["Retry-After"] == "30"


def test_failed_atomic_write_keeps_previous_record(server):
    data = record()
    with request(server, "/api/save", data) as response:
        path = server[1] / json.load(response)["file"]
    original = path.read_text()
    data["title"] = "Changed"
    with patch("dms.web.os.fsync", side_effect=OSError("disk full")):
        with pytest.raises(HTTPError) as error:
            request(server, "/api/save", data)
        assert error.value.code == 500
    assert path.read_text() == original
    assert not list(server[1].glob(".dms-*.tmp"))


def test_foreign_host_cannot_read_local_records(server):
    req = Request(server[0] + "/api/records", headers={"Host": "attacker.example"})
    with pytest.raises(HTTPError) as error:
        urlopen(req)
    assert error.value.code == 403
