import http.client
import json
import socket
import threading
import time
import unittest

import app


class _Submission:
    def __init__(self, data: dict):
        self._data = data

    def to_dict(self) -> dict:
        return dict(self._data)


class FakeService:
    def __init__(self) -> None:
        self._items = []
        self._next_id = 1

    def list_sections(self):
        return {
            "featured": {"title": "Featured", "limit": 10},
            "experimental": {"title": "Experimental", "limit": 20},
        }

    def list_submissions(self, status=None):
        if status is None:
            return [dict(x) for x in self._items]
        return [dict(x) for x in self._items if x.get("status") == status]

    def list_catalog(self):
        return [dict(x) for x in self._items if x.get("status") == "approved"]

    def submit_content(self, payload):
        required = {
            "title",
            "creator_name",
            "duration_minutes",
            "category",
            "world_original",
            "has_subtitles_or_voiceover",
            "resolution",
            "description",
        }
        missing = sorted(required - set(payload))
        if missing:
            raise ValueError(f"Missing fields: {', '.join(missing)}")
        if payload.get("resolution") != "1080p":
            raise ValueError("Minimum resolution is 1080p")

        item = {
            "id": self._next_id,
            "title": payload["title"],
            "creator_name": payload["creator_name"],
            "duration_minutes": payload["duration_minutes"],
            "category": payload["category"],
            "world_original": payload["world_original"],
            "has_subtitles_or_voiceover": payload["has_subtitles_or_voiceover"],
            "resolution": payload["resolution"],
            "description": payload["description"],
            "keywords": payload.get("keywords", []),
            "status": "pending_ai",
            "moderation_reason": None,
            "section": None,
        }
        self._items.append(item)
        self._next_id += 1
        return _Submission(item)

    def review_submission(self, submission_id, decision, moderation_reason, section=None):
        found = None
        for x in self._items:
            if x["id"] == submission_id:
                found = x
                break
        if not found:
            raise KeyError(f"Submission {submission_id} not found")

        if found["status"] != "pending_human":
            raise ValueError("Human review is allowed only for pending_human submissions")

        found["status"] = decision
        found["moderation_reason"] = moderation_reason
        found["section"] = section if decision == "approved" else None
        return dict(found)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class QuietHandler(app.NeuroFilmsHandler):
    def log_message(self, format, *args):  # noqa: A003
        return


class HttpApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.host = "127.0.0.1"
        cls.port = _free_port()
        cls.httpd = app.ThreadingHTTPServer((cls.host, cls.port), QuietHandler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.05)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=1)

    def setUp(self) -> None:
        app.service = FakeService()

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

    def _request_raw(self, method: str, path: str, body: str, content_type="application/json"):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=5)
        headers = {"Content-Type": content_type}
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
        self.assertIn("featured", data)

    def test_submit_valid_content(self):
        status, data = self._request("POST", "/api/v1/submissions", self._valid_submission())
        self.assertEqual(status, 201)
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
        self.assertTrue(any(x["id"] == created["id"] for x in items))

        status, filtered = self._request("GET", "/api/v1/submissions?status=pending_ai")
        self.assertEqual(status, 200)
        self.assertTrue(all(x["status"] == "pending_ai" for x in filtered))

    def test_review_missing_submission(self):
        payload = {"decision": "approved", "moderation_reason": "ok", "section": "featured"}
        status, data = self._request("POST", "/api/v1/submissions/999/review", payload)
        self.assertEqual(status, 404)
        self.assertIn("error", data)

    def test_review_rejected_when_not_pending_human(self):
        status, created = self._request("POST", "/api/v1/submissions", self._valid_submission())
        self.assertEqual(status, 201)

        payload = {"decision": "approved", "moderation_reason": "ok", "section": "featured"}
        status, data = self._request("POST", f"/api/v1/submissions/{created['id']}/review", payload)
        self.assertEqual(status, 400)
        self.assertIn("error", data)

    def test_catalog_endpoint(self):
        status, data = self._request("GET", "/api/v1/catalog")
        self.assertEqual(status, 200)
        self.assertIsInstance(data, list)

    def test_unknown_route_returns_404(self):
        status, data = self._request("GET", "/api/v1/nope")
        self.assertEqual(status, 404)
        self.assertIn("error", data)

    def test_invalid_json_returns_400(self):
        status, data = self._request_raw("POST", "/api/v1/submissions", "{bad json")
        self.assertEqual(status, 400)
        self.assertIn("error", data)


if __name__ == "__main__":
    unittest.main()
