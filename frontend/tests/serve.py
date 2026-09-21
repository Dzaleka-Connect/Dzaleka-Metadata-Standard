"""Isolated localhost server for browser tests; never touches the real archive."""
import tempfile
from pathlib import Path
from http.server import ThreadingHTTPServer

from dms.web import make_handler

with tempfile.TemporaryDirectory(prefix="dms-browser-") as directory:
    with ThreadingHTTPServer(("127.0.0.1", 0), make_handler(Path(directory))) as server:
        print(f"http://127.0.0.1:{server.server_port}", flush=True)
        server.serve_forever()
