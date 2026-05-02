from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from authapp.models import IframeEmbedCode, MagicLinkToken, StudentIdentity
from authapp.services import (
    CanvasAPIError,
    CanvasClient,
    CanvasStudentCandidate,
    build_magic_link_url,
    consume_magic_token,
    create_magic_link,
    make_token_hash,
    resolve_candidate,
)


@override_settings(
    CANVAS_API_URL="https://canvas.example.com",
    CANVAS_API_TOKEN="test-token",
    APP_BASE_URL="https://app.example.com",
)
class ServiceTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_token_hash_is_deterministic(self):
        self.assertEqual(make_token_hash("abc"), make_token_hash("abc"))
        self.assertNotEqual(make_token_hash("abc"), make_token_hash("abd"))

    def test_create_and_consume_token_once(self):
        request = self.factory.post("/auth/request-link", HTTP_USER_AGENT="pytest")
        token = create_magic_link(42, "123", "student@example.com", request)

        consumed = consume_magic_token(token)
        self.assertIsNotNone(consumed)
        self.assertEqual(consumed.canvas_user_id, 42)

        consumed_again = consume_magic_token(token)
        self.assertIsNone(consumed_again)

    def test_expired_token_rejected(self):
        raw = "expired-token"
        MagicLinkToken.objects.create(
            token_hash=make_token_hash(raw),
            canvas_user_id=99,
            course_id="123",
            requested_login_id="a@b.com",
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        self.assertIsNone(consume_magic_token(raw))

    def test_build_magic_link_url(self):
        link = build_magic_link_url("abc123")
        self.assertEqual(link, "https://app.example.com/auth/magic?token=abc123")

    def test_candidate_resolution_none_single_multiple(self):
        c1 = CanvasStudentCandidate(
            canvas_user_id=1,
            full_name="Alice Example",
            short_name="Alice",
            sortable_name="Example, Alice",
            email="alice@example.com",
            login_id="alice@example.com",
        )
        c2 = CanvasStudentCandidate(
            canvas_user_id=2,
            full_name="Bob Example",
            short_name="Bob",
            sortable_name="Example, Bob",
            email="bob@example.com",
            login_id="bob@example.com",
        )

        self.assertIsNone(resolve_candidate("nobody", [c1, c2]))
        self.assertEqual(resolve_candidate("alice", [c1, c2]).canvas_user_id, 1)
        self.assertIsNone(resolve_candidate("example", [c1, c2]))

    @patch("authapp.services.requests.get")
    def test_canvas_search_error_maps_to_exception(self, mock_get):
        mock_get.return_value.status_code = 500
        mock_get.return_value.json.return_value = []

        client = CanvasClient()
        with self.assertRaises(CanvasAPIError):
            client.search_course_students("12", "alice")

    @patch("authapp.services.requests.post")
    def test_canvas_message_payload(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = []

        client = CanvasClient()
        client.send_magic_link_message(777, "https://app.example.com/auth/magic?token=x")

        kwargs = mock_post.call_args.kwargs
        self.assertIn("/api/v1/conversations", kwargs["url"])
        self.assertEqual(kwargs["data"]["recipients[]"], "777")
        self.assertIn("token=x", kwargs["data"]["body"])


@override_settings(
    CANVAS_API_URL="https://canvas.example.com",
    CANVAS_API_TOKEN="test-token",
    APP_BASE_URL="https://app.example.com",
)
class ViewFlowTests(TestCase):
    def _candidate(self, canvas_user_id=123, login_id="treharne@liverpool.ac.uk"):
        return CanvasStudentCandidate(
            canvas_user_id=canvas_user_id,
            full_name="Tom Reharne",
            short_name="Tom",
            sortable_name="Reharne, Tom",
            email=login_id,
            login_id=login_id,
        )

    def test_missing_course_id_blocks_landing(self):
        response = self.client.get(reverse("landing"))
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Missing or invalid course context", status_code=400)

    def test_frame_ancestors_header_present(self):
        response = self.client.get(reverse("landing") + "?course_id=999")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Security-Policy"],
            "frame-ancestors 'self' https://canvas.example.com",
        )

    @patch("authapp.views.CanvasClient")
    def test_request_link_success_creates_token_and_sends_message(self, client_cls):
        client = MagicMock()
        client.search_course_students.return_value = [self._candidate()]
        client_cls.return_value = client

        response = self.client.post(
            reverse("request-link"),
            data={"course_id": "123", "login_id": "treharne"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "check your Canvas inbox")
        self.assertEqual(MagicLinkToken.objects.count(), 1)
        client.send_magic_link_message.assert_called_once()

    @patch("authapp.views.CanvasClient")
    def test_request_link_no_unique_match_still_generic(self, client_cls):
        client = MagicMock()
        client.search_course_students.return_value = [self._candidate(1), self._candidate(2)]
        client_cls.return_value = client

        response = self.client.post(
            reverse("request-link"),
            data={"course_id": "123", "login_id": "example"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "check your Canvas inbox")
        self.assertEqual(MagicLinkToken.objects.count(), 0)

    @patch("authapp.views.CanvasClient")
    def test_magic_link_login_creates_session_and_student_record(self, client_cls):
        client = MagicMock()
        client.search_course_students.return_value = [self._candidate(canvas_user_id=99, login_id="treharne")]
        client_cls.return_value = client

        request = RequestFactory().post("/auth/request-link", HTTP_USER_AGENT="pytest")
        raw_token = create_magic_link(99, "321", "treharne", request)

        response = self.client.get(reverse("magic-login") + f"?token={raw_token}")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("app-home"))

        follow = self.client.get(reverse("app-home"))
        self.assertEqual(follow.status_code, 200)
        self.assertEqual(StudentIdentity.objects.count(), 1)
        self.assertContains(follow, "Signed In")

    @patch("authapp.views.CanvasClient")
    def test_magic_link_replay_is_rejected(self, client_cls):
        client = MagicMock()
        client.search_course_students.return_value = [self._candidate(canvas_user_id=99)]
        client_cls.return_value = client

        request = RequestFactory().post("/auth/request-link", HTTP_USER_AGENT="pytest")
        raw_token = create_magic_link(99, "321", "treharne", request)

        first = self.client.get(reverse("magic-login") + f"?token={raw_token}")
        self.assertEqual(first.status_code, 302)

        second = self.client.get(reverse("magic-login") + f"?token={raw_token}")
        self.assertEqual(second.status_code, 400)
        self.assertContains(second, "invalid or expired", status_code=400)


@override_settings(APP_BASE_URL="https://app.example.com")
class EmbedCodeTests(TestCase):
    def test_embed_code_launch_url_and_iframe(self):
        embed = IframeEmbedCode.objects.create(
            name="BIO101 Launcher",
            course_id="12345",
            width="100%",
            height=900,
        )
        self.assertEqual(embed.launch_url(), "https://app.example.com/?course_id=12345")
        self.assertIn("<iframe", embed.iframe_html())
        self.assertIn('src="https://app.example.com/?course_id=12345"', embed.iframe_html())
