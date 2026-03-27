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
        get_required_fields,
        get_field_descriptions,
    )
    return {
        "version": get_schema_version(),
        "types": get_type_enum(),
        "roles": get_creator_roles(),
        "access_levels": get_access_levels(),
        "required": get_required_fields(),
        "fields": get_field_descriptions(),
    }


def make_handler(records_dir: Path):
    """Create a request handler class with the given records directory."""

    class DMSHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            # Suppress default logging
            pass

        def _send_json(self, data: dict | list, status: int = 200):
            body = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def _send_html(self, html: str, status: int = 200):
            body = html.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            parsed = urlparse(self.path)
            path = parsed.path

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

            else:
                self.send_error(404)

        def do_POST(self):
            parsed = urlparse(self.path)
            path = parsed.path

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
                from dms.validator import validate_record
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
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
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
