import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import MagicLinkToken, StudentIdentity


class CanvasAPIError(Exception):
    pass


@dataclass
class CanvasStudentCandidate:
    canvas_user_id: int
    full_name: str
    short_name: str
    sortable_name: str
    email: str
    login_id: str


class CanvasClient:
    def __init__(self):
        self.base_url = settings.CANVAS_API_URL.rstrip("/")
        self.token = settings.CANVAS_API_TOKEN
        if not self.base_url or not self.token:
            raise CanvasAPIError("Canvas API configuration missing")

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

    def search_course_students(self, course_id: str, search_term: str) -> list[CanvasStudentCandidate]:
        url = f"{self.base_url}/api/v1/courses/{course_id}/search_users"
        params = {
            "search_term": search_term,
            "enrollment_type[]": "student",
        }
        response = requests.get(url=url, headers=self.headers, params=params, timeout=15)
        if response.status_code >= 400:
            raise CanvasAPIError(f"Canvas search failed ({response.status_code})")

        raw = response.json()
        candidates = []
        for item in raw:
            canvas_id = item.get("id")
            if canvas_id is None:
                continue
            candidates.append(
                CanvasStudentCandidate(
                    canvas_user_id=int(canvas_id),
                    full_name=item.get("name", ""),
                    short_name=item.get("short_name", ""),
                    sortable_name=item.get("sortable_name", ""),
                    email=item.get("email") or item.get("primary_email") or "",
                    login_id=(item.get("login_id") or item.get("sis_login_id") or ""),
                )
            )
        return candidates

    def send_magic_link_message(self, canvas_user_id: int, link: str) -> None:
        url = f"{self.base_url}/api/v1/conversations"
        subject = "Your login link"
        body = (
            "Open your app login link:\n"
            f"{link}\n\n"
            "Auto-link test URL:\n"
            "https://google.com\n\n"
            "This link expires in 15 minutes and can be used once."
        )
        data = {
            "recipients[]": str(canvas_user_id),
            "subject": subject,
            "body": body,
            "force_new": "true",
        }
        response = requests.post(url=url, headers=self.headers, data=data, timeout=15)
        if response.status_code >= 400:
            raise CanvasAPIError(f"Canvas message send failed ({response.status_code})")


def resolve_candidate(login_id: str, candidates: list[CanvasStudentCandidate]) -> CanvasStudentCandidate | None:
    target = login_id.strip().lower()
    matches = []

    for c in candidates:
        searchable = [c.login_id, c.email, c.full_name, c.short_name]
        if any(target in (value or "").lower() for value in searchable):
            matches.append(c)

    if len(matches) != 1:
        return None
    return matches[0]


def make_token_hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_magic_link(canvas_user_id: int, course_id: str, requested_login_id: str, request) -> str:
    raw_token = secrets.token_urlsafe(32)
    token_hash = make_token_hash(raw_token)
    expires_at = timezone.now() + timedelta(seconds=settings.MAGIC_LINK_TTL_SECONDS)

    MagicLinkToken.objects.create(
        token_hash=token_hash,
        canvas_user_id=canvas_user_id,
        course_id=course_id,
        requested_login_id=requested_login_id,
        expires_at=expires_at,
        request_ip=get_client_ip(request),
        request_user_agent=request.META.get("HTTP_USER_AGENT", "")[:1000],
        request_metadata={
            "referer": request.META.get("HTTP_REFERER", ""),
        },
    )

    return raw_token


def build_magic_link_url(raw_token: str) -> str:
    path = f"/auth/magic?token={raw_token}"
    return urljoin(settings.APP_BASE_URL.rstrip("/") + "/", path.lstrip("/"))


def get_client_ip(request) -> str | None:
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def consume_magic_token(raw_token: str) -> MagicLinkToken | None:
    token_hash = make_token_hash(raw_token)
    now = timezone.now()

    with transaction.atomic():
        token = (
            MagicLinkToken.objects.select_for_update()
            .filter(token_hash=token_hash)
            .first()
        )
        if token is None:
            return None
        if token.used_at is not None or token.expires_at <= now:
            return None

        token.used_at = now
        token.save(update_fields=["used_at"])
        return token


def upsert_student_identity(candidate: CanvasStudentCandidate) -> StudentIdentity:
    student, _ = StudentIdentity.objects.update_or_create(
        canvas_user_id=candidate.canvas_user_id,
        defaults={
            "full_name": candidate.full_name,
            "short_name": candidate.short_name,
            "sortable_name": candidate.sortable_name,
            "email": candidate.email,
            "last_auth_at": timezone.now(),
        },
    )
    return student
