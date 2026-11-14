"""Local mock of the SEC file layout for tests. NOT the SEC. Serves files from a directory tree and can simulate
403 blocks. Records every request (path + User-Agent) so tests can assert fair-access behaviour."""
from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class MockSec:
    def __init__(self, root: Path, block_once: set[str] | None = None, always_block: bool = False):
        self.root, self.block_once, self.always_block = Path(root), set(block_once or ()), always_block
        self.requests: list[tuple[float, str, str]] = []
        self._lock = threading.Lock()
        outer = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):  # silence
                pass

            def do_GET(self):
                import time
                path = self.path.split("?")[0]
                with outer._lock:
                    outer.requests.append((time.monotonic(), path, self.headers.get("User-Agent", "")))
                    blocked = outer.always_block
                    if not blocked and path in outer.block_once:
                        outer.block_once.discard(path)      # block exactly once
                        blocked = True
                if blocked:
                    self.send_response(403)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                f = outer.root / path.lstrip("/")
                if f.is_file():
                    data = f.read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                else:
                    self.send_response(404)
                    self.send_header("Content-Length", "0")
                    self.end_headers()

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()
