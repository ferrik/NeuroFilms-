from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from neurofilms_service import NeuroFilmsService, ValidationError

service = NeuroFilmsService()


class NeuroFilmsHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, status: int, payload: dict | list) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8"))

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send(HTTPStatus.OK, {"status": "ok"})
            return
        if parsed.path == "/api/v1/sections":
            self._send(HTTPStatus.OK, service.list_sections())
            return
        if parsed.path == "/api/v1/submissions":
            query = parse_qs(parsed.query)
            status = query.get("status", [None])[0]
            self._send(HTTPStatus.OK, service.list_submissions(status=status))
            return
        if parsed.path == "/api/v1/catalog":
            self._send(HTTPStatus.OK, service.list_catalog())
            return

        self._send(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        try:
            if self.path == "/api/v1/submissions":
                payload = self._read_json()
                submission = service.submit_content(payload).to_dict()
                self._send(HTTPStatus.CREATED, submission)
                return

            if self.path.startswith("/api/v1/submissions/") and self.path.endswith("/review"):
                parts = self.path.strip("/").split("/")
                submission_id = int(parts[3])
                payload = self._read_json()
                result = service.review_submission(
                    submission_id,
                    decision=payload.get("decision", ""),
                    moderation_reason=payload.get("moderation_reason", ""),
                    section=payload.get("section"),
                )
                self._send(HTTPStatus.OK, result)
                return
        except ValidationError as error:
            self._send(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return
        except KeyError as error:
            self._send(HTTPStatus.NOT_FOUND, {"error": str(error)})
            return
        except json.JSONDecodeError:
            self._send(HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON"})
            return

        self._send(HTTPStatus.NOT_FOUND, {"error": "Not found"})


def run(host: str = "127.0.0.1", port: int = 8080) -> None:
    httpd = ThreadingHTTPServer((host, port), NeuroFilmsHandler)
    print(f"NeuroFilms service running on http://{host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    run()
