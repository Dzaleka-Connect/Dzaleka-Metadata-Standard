"""
DMS Web UI

A local web server providing a browser-based form for creating,
validating, and managing DMS metadata records. Uses only Python's
built-in http.server — no additional dependencies required.

Usage:
    dms web                    # Start on port 8080
    dms web --port 3000        # Custom port
    dms web --dir records/     # Set records directory
"""

import json
import uuid
import webbrowser
from datetime import date
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from rich.console import Console

console = Console()

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


def get_schema_info() -> dict:
    """Gather schema metadata for the web UI."""
    from dms.schema import (
        get_schema_version,
        get_type_enum,
        get_creator_roles,
        get_access_levels,
        get_consent_statuses,
        get_sensitivity_values,
        get_relation_types,
        get_checksum_algorithms,
        get_required_fields,
        get_field_descriptions,
    )
    return {
        "version": get_schema_version(),
        "types": get_type_enum(),
        "roles": get_creator_roles(),
        "access_levels": get_access_levels(),
        "consent_statuses": get_consent_statuses(),
        "sensitivity_values": get_sensitivity_values(),
        "relation_types": get_relation_types(),
        "checksum_algorithms": get_checksum_algorithms(),
        "required": get_required_fields(),
        "fields": get_field_descriptions(),
    }


def make_handler(records_dir: Path):
    """Create a request handler class with the given records directory."""

    class DMSHandler(BaseHTTPRequestHandler):
        server_version = "DMSVault/1.1"
        sys_version = ""

        def log_message(self, format, *args):
            # Suppress default logging
            pass

        def _allowed_local_origins(self) -> set[str]:
            port = getattr(self.server, "server_port", 8080)
            return {
                f"http://127.0.0.1:{port}",
                f"http://localhost:{port}",
            }

        def _request_origin(self) -> str | None:
            origin = self.headers.get("Origin")
            if origin:
                return origin.rstrip("/")

            referer = self.headers.get("Referer")
            if referer:
                parsed = urlparse(referer)
                if parsed.scheme and parsed.hostname:
                    port = parsed.port or (443 if parsed.scheme == "https" else 80)
                    return f"{parsed.scheme}://{parsed.hostname}:{port}"
            return None

        def _origin_is_allowed(self) -> bool:
            origin = self._request_origin()
            if origin is None:
                return True
            return origin in self._allowed_local_origins()

        def _send_bytes(self, body: bytes, content_type: str, status: int = 200):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "same-origin")
            self.send_header("Cross-Origin-Opener-Policy", "same-origin")
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
                "script-src 'self' 'unsafe-inline'; connect-src 'self'; object-src 'none'; "
                "base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
            )
            origin = self._request_origin()
            if origin and origin in self._allowed_local_origins():
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, data: dict | list, status: int = 200):
            body = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
            self._send_bytes(body, "application/json; charset=utf-8", status=status)

        def _send_html(self, html: str, status: int = 200):
            body = html.encode("utf-8")
            self._send_bytes(body, "text/html; charset=utf-8", status=status)

        def _parse_int(self, value: str | None) -> int | None:
            if value in (None, ""):
                return None
            try:
                return int(value)
            except ValueError:
                return None

        def _parse_bool(self, value: str | None) -> bool:
            if value is None:
                return False
            return value.strip().lower() in {"1", "true", "yes", "on"}

        def _taxonomy_format(self, query: dict[str, list[str]]) -> str:
            explicit = query.get("format", [""])[0].strip().lower()
            if explicit in {"json", "jsonld", "ttl", "rdfxml", "html"}:
                return explicit

            accept = self.headers.get("Accept", "").lower()
            if "text/html" in accept:
                return "html"
            if "text/turtle" in accept or "application/x-turtle" in accept:
                return "ttl"
            if "application/rdf+xml" in accept:
                return "rdfxml"
            if "application/ld+json" in accept:
                return "jsonld"
            return "json"

        def _send_taxonomy_document(self, taxonomy: dict, response_format: str):
            from dms.taxonomy import taxonomy_to_jsonld, taxonomy_to_rdfxml, taxonomy_to_turtle

            if response_format == "jsonld":
                self._send_bytes(
                    json.dumps(taxonomy_to_jsonld(taxonomy), indent=2, ensure_ascii=False).encode("utf-8"),
                    "application/ld+json; charset=utf-8",
                )
                return
            if response_format == "ttl":
                self._send_bytes(
                    taxonomy_to_turtle(taxonomy).encode("utf-8"),
                    "text/turtle; charset=utf-8",
                )
                return
            if response_format == "rdfxml":
                self._send_bytes(
                    taxonomy_to_rdfxml(taxonomy).encode("utf-8"),
                    "application/rdf+xml; charset=utf-8",
                )
                return
            self._send_json(taxonomy)

        def _send_term(self, vocabulary: str, term_info: dict, response_format: str):
            from dms.taxonomy import get_subset_taxonomy, term_to_html

            if response_format == "html":
                self._send_html(term_to_html(vocabulary, term_info))
                return

            if response_format in {"jsonld", "ttl", "rdfxml"}:
                taxonomy = get_subset_taxonomy(vocabulary, ids=[term_info["short_id"]], include_deprecated=True)
                self._send_taxonomy_document(taxonomy, response_format)
                return

            self._send_json(term_info)

        def do_GET(self):
            parsed = urlparse(self.path)
            path = parsed.path
            query = parse_qs(parsed.query)

            if path == "/" or path == "/index.html":
                template = TEMPLATE_DIR / "index.html"
                if template.exists():
                    self._send_html(template.read_text(encoding="utf-8"))
                else:
                    self._send_html("<h1>Template not found</h1>", 500)

            elif path == "/api/schema":
                self._send_json(get_schema_info())

            elif path == "/api/records":
                records = []
                records_dir.mkdir(parents=True, exist_ok=True)
                for jf in sorted(records_dir.glob("*.json")):
                    try:
                        with open(jf, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        if isinstance(data, dict):
                            data["_file"] = jf.name
                            records.append(data)
                    except (json.JSONDecodeError, OSError):
                        pass
                self._send_json(records)

            elif path == "/api/new-id":
                self._send_json({"id": str(uuid.uuid4())})

            elif path.startswith("/api/taxonomy"):
                from dms.taxonomy import (
                    get_vocabulary_list,
                    get_subset_taxonomy,
                    load_taxonomy,
                    get_terms,
                    get_term_info,
                    get_deprecated_terms,
                    get_change_log,
                    get_vocabulary_structure,
                )

                parts = path.strip("/").split("/")
                response_format = self._taxonomy_format(query)
                ids = [item.strip() for item in query.get("ids", [""])[0].split(",") if item.strip()]
                search_query = query.get("q", [""])[0].strip() or None
                include_deprecated = self._parse_bool(query.get("include_deprecated", [""])[0]) or self._parse_bool(query.get("deprecated", [""])[0])
                limit = self._parse_int(query.get("limit", [""])[0])
                offset = self._parse_int(query.get("offset", [""])[0]) or 0

                # /api/taxonomy
                if len(parts) == 2:
                    self._send_json({"vocabularies": get_vocabulary_list()})
                    return

                # /api/taxonomy/<voc>
                voc = parts[2]
                if len(parts) == 3:
                    try:
                        if not ids and not search_query and limit is None and offset == 0 and not include_deprecated:
                            taxonomy = load_taxonomy(voc)
                        else:
                            taxonomy = get_subset_taxonomy(
                                voc,
                                ids=ids or None,
                                q=search_query,
                                include_deprecated=include_deprecated,
                                limit=limit,
                                offset=offset,
                            )
                        self._send_taxonomy_document(taxonomy, response_format)
                    except FileNotFoundError:
                        self.send_error(404, f"Vocabulary '{voc}' not found.")
                    return

                # /api/taxonomy/<voc>/<subpath>
                sub = parts[3]
                if sub == "terms":
                    if len(parts) == 5:
                        term_info = get_term_info(voc, parts[4])
                        if not term_info:
                            self.send_error(404, f"Term '{parts[4]}' not found in '{voc}'.")
                            return
                        self._send_term(voc, term_info, response_format)
                        return

                    terms = get_terms(
                        voc,
                        ids=ids or None,
                        q=search_query,
                        include_deprecated=include_deprecated,
                        limit=limit,
                        offset=offset,
                    )
                    if response_format in {"jsonld", "ttl", "rdfxml"}:
                        taxonomy = get_subset_taxonomy(
                            voc,
                            ids=ids or None,
                            q=search_query,
                            include_deprecated=include_deprecated,
                            limit=limit,
                            offset=offset,
                        )
                        self._send_taxonomy_document(taxonomy, response_format)
                        return
                    self._send_json(
                        {
                            "vocabulary": voc,
                            "count": len(terms),
                            "terms": terms,
                        }
                    )
                elif sub == "deprecated":
                    deprecated_terms = get_deprecated_terms(voc)
                    if response_format in {"jsonld", "ttl", "rdfxml"}:
                        taxonomy = get_subset_taxonomy(
                            voc,
                            ids=[term.get("id", "") for term in deprecated_terms],
                            include_deprecated=True,
                        )
                        self._send_taxonomy_document(taxonomy, response_format)
                        return
                    self._send_json(deprecated_terms)
                elif sub in {"history", "changes"}:
                    term_filter = query.get("term", [""])[0].strip() or None
                    self._send_json(get_change_log(voc, term_id=term_filter))
                elif sub == "structure":
                    self._send_json(get_vocabulary_structure(voc))
                else:
                    # Specific term
                    term_info = get_term_info(voc, sub)
                    if not term_info:
                        self.send_error(404, f"Term '{sub}' not found in '{voc}'.")
                        return
                    self._send_term(voc, term_info, response_format)

            else:
                self.send_error(404)

        def do_POST(self):
            parsed = urlparse(self.path)
            path = parsed.path

            if not self._origin_is_allowed():
                self._send_json({"error": "Cross-origin requests are not allowed."}, 403)
                return

            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            try:
                data = json.loads(body) if body else {}
            except json.JSONDecodeError:
                self._send_json({"error": "Invalid JSON"}, 400)
                return

            if path == "/api/validate":
                from dms.validator import validate_record, get_warnings
                errors = validate_record(data)
                is_valid = len(errors) == 0
                warnings = get_warnings(data) if is_valid else []
                self._send_json({
                    "valid": is_valid,
                    "errors": errors,
                    "warnings": warnings,
                })

            elif path == "/api/save":
                from dms.validator import validate_record, get_warnings
                errors = validate_record(data)
                is_valid = len(errors) == 0
                if not is_valid:
                    self._send_json({
                        "saved": False,
                        "error": "Record is not valid",
                        "errors": errors,
                    }, 400)
                    return

                records_dir.mkdir(parents=True, exist_ok=True)
                warnings = get_warnings(data)
                rec_type = data.get("type", "record")
                rec_id = data.get("id", str(uuid.uuid4()))[:8]
                filename = f"{rec_type}_{rec_id}.json"
                filepath = records_dir / filename

                # Remove internal fields
                clean = {k: v for k, v in data.items() if not k.startswith("_")}
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(clean, f, indent=2, ensure_ascii=False)
                    f.write("\n")

                console.print(f"  [green]✓ Saved:[/green] {filepath}")
                self._send_json({
                    "saved": True,
                    "file": filename,
                    "path": str(filepath),
                    "warnings": warnings,
                })

            elif path == "/api/export-jsonld":
                from dms.exporter import record_to_jsonld
                try:
                    jsonld = record_to_jsonld(data)
                    self._send_json(jsonld)
                except Exception as e:
                    self._send_json({"error": str(e)}, 500)

            else:
                self.send_error(404)

        def do_OPTIONS(self):
            if not self._origin_is_allowed():
                self._send_json({"error": "Cross-origin requests are not allowed."}, 403)
                return

            self.send_response(200)
            origin = self._request_origin()
            if origin and origin in self._allowed_local_origins():
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "same-origin")
            self.send_header("Cross-Origin-Opener-Policy", "same-origin")
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            self.end_headers()

    return DMSHandler


def start_server(port: int = 8080, records_dir: str | Path = "records", open_browser: bool = True):
    """Start the DMS web UI server.

    Args:
        port: Port to listen on.
        records_dir: Directory for saving records.
        open_browser: Whether to auto-open the browser.
    """
    records_path = Path(records_dir).resolve()
    records_path.mkdir(parents=True, exist_ok=True)

    handler = make_handler(records_path)
    server = HTTPServer(("127.0.0.1", port), handler)

    url = f"http://127.0.0.1:{port}"

    console.print()
    console.print(f"  [bold bright_blue]DMS Web UI[/bold bright_blue]")
    console.print(f"  [dim]Records directory:[/dim] {records_path}")
    console.print(f"  [dim]Server running at:[/dim] [bold cyan]{url}[/bold cyan]")
    console.print(f"  [dim]Press Ctrl+C to stop.[/dim]")
    console.print()

    if open_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        console.print("\n  [yellow]Server stopped.[/yellow]")
        server.server_close()
