"""Async HTTP API for Charlie Munger analysis.

Endpoints:
  POST /api/munger/analyze   — Start a new analysis job
  GET  /api/munger/status/<id> — Poll job status
  GET  /api/munger/jobs       — List all jobs
  GET  /munger                — Serve the web frontend

Jobs run in background threads.  State is held in memory (lost on restart).
"""

import json
import socket
import sys
import threading
import time
import traceback
import uuid
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from sec_edgar.munger_worker import run_analysis

MUNGER_HTML = Path(__file__).resolve().parent.parent / "munger.html"

# ── In-memory job store ──────────────────────────────────────────────

_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()


def _new_job(ticker: str) -> str:
    job_id = uuid.uuid4().hex[:12]
    with _jobs_lock:
        _jobs[job_id] = {
            "id": job_id,
            "ticker": ticker.upper(),
            "status": "queued",
            "stage": "queued",
            "created": time.time(),
            "updated": time.time(),
            "report": None,
            "error": None,
        }
    return job_id


def _update_job(job_id: str, **kwargs):
    with _jobs_lock:
        if job_id in _jobs:
            _jobs[job_id].update(kwargs, updated=time.time())


def _get_job(job_id: str) -> dict | None:
    with _jobs_lock:
        return _jobs.get(job_id, None)


def _list_jobs() -> list[dict]:
    with _jobs_lock:
        return [
            {k: v for k, v in j.items() if k != "report"}
            for j in sorted(_jobs.values(), key=lambda j: j["created"], reverse=True)
        ]


# ── Background worker thread ────────────────────────────────────────

def _run_job(job_id: str, ticker: str, user_agent: str | None):
    def on_progress(stage: str):
        _update_job(job_id, stage=stage, status="running")

    try:
        _update_job(job_id, status="running", stage="starting")
        report = run_analysis(ticker, user_agent=user_agent, on_progress=on_progress)
        _update_job(job_id, status="complete", stage="done", report=report)
    except Exception as exc:
        tb = traceback.format_exc()
        _update_job(job_id, status="error", stage="failed", error=str(exc))
        print(f"[munger] Job {job_id} failed: {exc}\n{tb}", file=sys.stderr)


# ── HTTP Handler ─────────────────────────────────────────────────────

class MungerHandler(SimpleHTTPRequestHandler):
    """Handle API routes and serve the frontend."""

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path in ("", "/munger"):
            self._serve_file(MUNGER_HTML, "text/html")

        elif path == "/api/munger/jobs":
            self._json_response(_list_jobs())

        elif path.startswith("/api/munger/status/"):
            job_id = path.split("/")[-1]
            job = _get_job(job_id)
            if job:
                self._json_response(job)
            else:
                self._json_response({"error": "Job not found"}, status=404)

        else:
            self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/api/munger/analyze":
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len) if content_len else b"{}"
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                self._json_response({"error": "Invalid JSON"}, status=400)
                return

            ticker = payload.get("ticker", "").strip().upper()
            if not ticker:
                self._json_response({"error": "Missing 'ticker' field"}, status=400)
                return

            user_agent = payload.get("user_agent")
            job_id = _new_job(ticker)

            # Launch background thread
            t = threading.Thread(
                target=_run_job,
                args=(job_id, ticker, user_agent),
                daemon=True,
            )
            t.start()

            self._json_response({"job_id": job_id, "ticker": ticker}, status=202)
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    # ── Helpers ───────────────────────────────────────────────────────

    def _json_response(self, data, status=200):
        body = json.dumps(data, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, path, content_type):
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", len(data))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(data)

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, fmt, *args):
        # Minimal logging — just POST requests
        if args and "POST" in str(args[0]):
            print(f"[munger] {fmt % args}")


# ── Server entrypoint ────────────────────────────────────────────────

def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    server = HTTPServer(("localhost", port), MungerHandler)
    server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    print(f"Charlie Munger API running at http://localhost:{port}")
    print(f"  POST /api/munger/analyze  — start analysis")
    print(f"  GET  /api/munger/status/{{id}} — poll status")
    print(f"  GET  /munger              — web frontend")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
