"""Minimal HTTP server for the SEC EDGAR data viewer."""

import json
import os
import socket
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "output"
VIEWER_PATH = Path(__file__).parent / "viewer.html"


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self._serve_file(VIEWER_PATH, "text/html")
        elif self.path == "/api/files":
            tickers = sorted(
                p.stem for p in OUTPUT_DIR.glob("*.json")
            )
            self._json_response(tickers)
        elif self.path.startswith("/api/data/"):
            ticker = self.path[len("/api/data/"):]
            fp = OUTPUT_DIR / f"{ticker}.json"
            if fp.exists():
                self._serve_file(fp, "application/json")
            else:
                self.send_error(404)
        else:
            self.send_error(404)

    def _json_response(self, data):
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, path, content_type):
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", len(data))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        pass  # silent


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    server = HTTPServer(("localhost", port), Handler)
    server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    print(f"Open http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
