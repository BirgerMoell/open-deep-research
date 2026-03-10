from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Tuple

from .config import Settings
from .research import DeepResearchEngine


def build_handler(settings: Settings):
    engine = DeepResearchEngine(settings)

    class ResearchHandler(BaseHTTPRequestHandler):
        def _write_json(self, payload, status=HTTPStatus.OK) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/research":
                self._write_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)
                return
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8")
            try:
                payload = json.loads(raw)
                question = str(payload["question"]).strip()
            except Exception:
                self._write_json({"error": "invalid JSON body"}, status=HTTPStatus.BAD_REQUEST)
                return
            try:
                result = engine.run(
                    question,
                    output_dir=Path(payload["output_dir"]) if payload.get("output_dir") else None,
                    final_papers=int(payload.get("final_papers", 8)),
                    no_llm=bool(payload.get("no_llm", False)),
                )
            except Exception as exc:
                self._write_json({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            self._write_json(result.to_dict())

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/health":
                self._write_json({"ok": True})
                return
            self._write_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)

        def log_message(self, format: str, *args) -> None:
            return

    return ResearchHandler


def serve(settings: Settings, host: str, port: int) -> Tuple[str, int]:
    server = ThreadingHTTPServer((host, port), build_handler(settings))
    try:
        server.serve_forever()
    finally:
        server.server_close()
    return host, port

