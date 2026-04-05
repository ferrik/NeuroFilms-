import http.client
import json
import socket
import threading
import time
import unittest

import app
from neurofilms_service import NeuroFilmsService


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class HttpApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.host = "127.0.0.1"
        cls.port = _free_port()
        cls.httpd = app.ThreadingHTTPServer((cls.host, cls.port), app.NeuroFilmsHandler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.05)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=1)

    def setUp(self) -> None:
        app.service = NeuroFilmsService()

    def _request(self, method: str, path: str, payload: dict | None = None):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=5)
        body = None
        headers = {}
        if payload is not None:
            body = json.dumps(payload)
            headers["Content-Type"] = "application/json"
        conn.request(method, path, body=body, headers=headers)
        resp = conn.getresponse()
        raw = resp.read().decode("utf-8")
        conn.close()
        data = json.loads(raw) if raw else None
        return resp.status, data

    def _valid_submission(self) -> dict:
        return {
            "title": "Original Neon City",
            "creator_name": "Acer Creator",
            "duration_minutes": 5,
            "category": "experimental",
            "world_original": True,
            "has_subtitles_or_voiceover": True,
            "resolution": "1080p",
            "description": "Original world short film",
            "keywords": ["original", "neon"],
        }

    def test_health(self):
        status, data = self._request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(data, {"status": "ok"})

    def test_sections(self):
        status, data = self._request("GET", "/api/v1/sections")
        self.assertEqual(status, 200)
        self.assertIsInstance(data, dict)
        self.assertIn("featured", data)

    def test_submit_valid_content(self):
        status, data = self._request("POST", "/api/v1/submissions", self._valid_submission())
        self.assertEqual(status, 201)
        self.assertIn("id", data)
        self.assertEqual(data["status"], "pending_ai")

    def test_submit_invalid_content(self):
        bad = self._valid_submission()
        bad["resolution"] = "720p"
        status, data = self._request("POST", "/api/v1/submissions", bad)
        self.assertEqual(status, 400)
        self.assertIn("error", data)

    def test_list_submissions_and_filter(self):
        status, created = self._request("POST", "/api/v1/submissions", self._valid_submission())
        self.assertEqual(status, 201)

        status, items = self._request("GET", "/api/v1/submissions")
        self.assertEqual(status, 200)
        self.assertIsInstance(items, list)
        self.assertTrue(any(x["id"] == created["id"] for x in items))

        status, filtered = self._request("GET", "/api/v1/submissions?status=pending_ai")
        self.assertEqual(status, 200)
        self.assertTrue(all(x["status"] == "pending_ai" for x in filtered))

    def test_review_missing_submission(self):
        payload = {
            "decision": "approved",
            "moderation_reason": "ok",
            "section": "featured",
        }
        status, data = self._request("POST", "/api/v1/submissions/999/review", payload)
        self.assertEqual(status, 404)
        self.assertIn("error", data)

    def test_review_rejected_when_not_pending_human(self):
        status, created = self._request("POST", "/api/v1/submissions", self._valid_submission())
        self.assertEqual(status, 201)

        payload = {
            "decision": "approved",
            "moderation_reason": "ok",
            "section": "featured",
        }
        status, data = self._request(
            "POST",
            f"/api/v1/submissions/{created['id']}/review",
            payload,
        )
        self.assertEqual(status, 400)
        self.assertIn("error", data)

    def test_catalog_endpoint(self):
        status, data = self._request("GET", "/api/v1/catalog")
        self.assertEqual(status, 200)
        self.assertIsInstance(data, list)


if __name__ == "__main__":
    unittest.main()
