import unittest

from neurofilms_service import NeuroFilmsService, ValidationError


class NeuroFilmsServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = NeuroFilmsService()
        self.valid_payload = {
            "title": "Neon Dreams",
            "creator_name": "Olena K",
            "duration_minutes": 5.5,
            "category": "music_visions",
            "world_original": True,
            "has_subtitles_or_voiceover": True,
            "resolution": "1080p",
            "description": "Original cyberpunk music vision",
            "keywords": ["cyberpunk", "music", "ai"],
        }

    def test_submit_content_success(self) -> None:
        submission = self.service.submit_content(self.valid_payload)
        self.assertEqual(submission.id, 1)
        self.assertEqual(submission.status, "pending")

    def test_submit_content_rejects_banned_ip(self) -> None:
        payload = dict(self.valid_payload)
        payload["description"] = "A Marvel style superhero story"
        with self.assertRaises(ValidationError):
            self.service.submit_content(payload)

    def test_review_submission_approve_and_publish_to_catalog(self) -> None:
        submission = self.service.submit_content(self.valid_payload)
        reviewed = self.service.review_submission(
            submission.id,
            decision="approved",
            moderation_reason="Fits MVP quality bar",
            section="featured",
        )
        self.assertEqual(reviewed["status"], "approved")
        catalog = self.service.list_catalog()
        self.assertEqual(len(catalog["featured"]), 1)

    def test_duration_rule_2_to_10_minutes(self) -> None:
        payload = dict(self.valid_payload)
        payload["duration_minutes"] = 1.5
        with self.assertRaises(ValidationError):
            self.service.submit_content(payload)


if __name__ == "__main__":
    unittest.main()
