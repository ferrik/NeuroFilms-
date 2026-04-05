from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any


SECTIONS = {
    "featured": {"title": "Featured", "limit": 10},
    "new_drops": {"title": "New Drops", "limit": 20},
    "music_visions": {"title": "Music Visions", "limit": 20},
    "experimental": {"title": "Experimental", "limit": 20},
    "creator_spotlight": {"title": "Creator Spotlight", "limit": 50},
}

BANNED_IP_KEYWORDS = (
    "marvel",
    "dc",
    "harry potter",
    "disney",
    "star wars",
)


@dataclass(slots=True)
class Submission:
    id: int
    title: str
    creator_name: str
    duration_minutes: float
    category: str
    world_original: bool
    has_subtitles_or_voiceover: bool
    resolution: str
    description: str
    keywords: list[str]
    status: str = "pending"
    moderation_reason: str | None = None
    section: str | None = None
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ValidationError(ValueError):
    """Raised when a submission violates platform rules."""


class NeuroFilmsService:
    """In-memory service for NeuroFilms MVP moderation and curation."""

    def __init__(self) -> None:
        self._submissions: dict[int, Submission] = {}
        self._next_id = 1

    def list_sections(self) -> dict[str, dict[str, Any]]:
        return SECTIONS

    def submit_content(self, payload: dict[str, Any]) -> Submission:
        self._validate_payload(payload)
        submission = Submission(
            id=self._next_id,
            title=payload["title"].strip(),
            creator_name=payload["creator_name"].strip(),
            duration_minutes=float(payload["duration_minutes"]),
            category=payload["category"],
            world_original=bool(payload["world_original"]),
            has_subtitles_or_voiceover=bool(payload["has_subtitles_or_voiceover"]),
            resolution=payload["resolution"],
            description=payload["description"].strip(),
            keywords=[str(k).strip().lower() for k in payload.get("keywords", [])],
            created_at=datetime.utcnow().isoformat(timespec="seconds") + "Z",
        )
        self._submissions[submission.id] = submission
        self._next_id += 1
        return submission

    def list_submissions(self, status: str | None = None) -> list[dict[str, Any]]:
        submissions = self._submissions.values()
        if status:
            submissions = [s for s in submissions if s.status == status]
        return [submission.to_dict() for submission in submissions]

    def review_submission(
        self,
        submission_id: int,
        *,
        decision: str,
        moderation_reason: str,
        section: str | None = None,
    ) -> dict[str, Any]:
        submission = self._submissions.get(submission_id)
        if not submission:
            raise KeyError(f"Submission {submission_id} not found")

        if decision not in {"approved", "rejected"}:
            raise ValidationError("Decision must be 'approved' or 'rejected'")

        if decision == "approved":
            if section not in SECTIONS:
                raise ValidationError("Approved content must have a valid section")
            submission.section = section
        else:
            submission.section = None

        submission.status = decision
        submission.moderation_reason = moderation_reason.strip()
        return submission.to_dict()

    def list_catalog(self) -> dict[str, list[dict[str, Any]]]:
        catalog: dict[str, list[dict[str, Any]]] = {section: [] for section in SECTIONS}
        for submission in self._submissions.values():
            if submission.status == "approved" and submission.section:
                catalog[submission.section].append(submission.to_dict())

        for section, config in SECTIONS.items():
            catalog[section] = catalog[section][: int(config["limit"])]
        return catalog

    def _validate_payload(self, payload: dict[str, Any]) -> None:
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
            raise ValidationError(f"Missing fields: {', '.join(missing)}")

        duration = float(payload["duration_minutes"])
        if duration < 2 or duration > 10:
            raise ValidationError("Duration must be between 2 and 10 minutes")

        if payload["resolution"] != "1080p":
            raise ValidationError("Minimum resolution is 1080p")

        if not payload["world_original"]:
            raise ValidationError("Only original worlds are allowed")

        if not payload["has_subtitles_or_voiceover"]:
            raise ValidationError("Submission requires subtitles or voiceover")

        all_text = " ".join(
            [
                str(payload["title"]),
                str(payload["description"]),
                " ".join(str(k) for k in payload.get("keywords", [])),
            ]
        ).lower()

        if any(ip in all_text for ip in BANNED_IP_KEYWORDS):
            raise ValidationError("Known franchise IP is not allowed")

        forbidden_terms = ("deepfake", "18+", "porn", "gore", "extreme violence")
        if any(term in all_text for term in forbidden_terms):
            raise ValidationError("Submission violates content safety rules")
