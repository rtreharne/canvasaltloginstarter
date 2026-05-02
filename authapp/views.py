from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST
from urllib.parse import urlparse
from django.conf import settings

from .forms import LoginRequestForm
from .services import (
    CanvasAPIError,
    CanvasClient,
    CanvasStudentCandidate,
    build_magic_link_url,
    consume_magic_token,
    create_magic_link,
    resolve_candidate,
    upsert_student_identity,
)

GENERIC_REQUEST_MESSAGE = "If your details match a course enrollment, check your Canvas inbox for a login link."
GENERIC_MAGIC_ERROR = "This login link is invalid or expired."


def _canvas_inbox_url() -> str | None:
    if not settings.CANVAS_API_URL:
        return None
    parsed = urlparse(settings.CANVAS_API_URL)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}/conversations"


@require_GET
@ensure_csrf_cookie
def landing(request: HttpRequest) -> HttpResponse:
    course_id = request.GET.get("course_id", "").strip()
    if not course_id or not course_id.isdigit():
        return render(
            request,
            "authapp/generic_error.html",
            {"message": "Missing or invalid course context."},
            status=400,
        )

    form = LoginRequestForm(initial={"course_id": course_id})
    return render(request, "authapp/landing.html", {"form": form, "course_id": course_id})


@require_POST
def request_link(request: HttpRequest) -> HttpResponse:
    form = LoginRequestForm(request.POST)
    if not form.is_valid():
        return render(
            request,
            "authapp/request_result.html",
            {
                "message": GENERIC_REQUEST_MESSAGE,
                "canvas_inbox_url": _canvas_inbox_url(),
            },
            status=200,
        )

    course_id = form.cleaned_data["course_id"]
    login_id = form.cleaned_data["login_id"]

    try:
        client = CanvasClient()
        candidates = client.search_course_students(course_id=course_id, search_term=login_id)
        selected = resolve_candidate(login_id, candidates)
        if selected is None:
            return render(
                request,
                "authapp/request_result.html",
                {
                    "message": GENERIC_REQUEST_MESSAGE,
                    "canvas_inbox_url": _canvas_inbox_url(),
                },
                status=200,
            )

        _send_magic_link(request, client, selected, course_id, login_id)
    except CanvasAPIError:
        return render(
            request,
            "authapp/request_result.html",
            {
                "message": GENERIC_REQUEST_MESSAGE,
                "canvas_inbox_url": _canvas_inbox_url(),
            },
            status=200,
        )

    return render(
        request,
        "authapp/request_result.html",
        {
            "message": GENERIC_REQUEST_MESSAGE,
            "canvas_inbox_url": _canvas_inbox_url(),
        },
        status=200,
    )


def _send_magic_link(
    request: HttpRequest,
    client: CanvasClient,
    selected: CanvasStudentCandidate,
    course_id: str,
    login_id: str,
) -> None:
    raw_token = create_magic_link(
        canvas_user_id=selected.canvas_user_id,
        course_id=course_id,
        requested_login_id=login_id,
        request=request,
    )
    link = build_magic_link_url(raw_token)
    client.send_magic_link_message(selected.canvas_user_id, link)


@require_GET
def magic_login(request: HttpRequest) -> HttpResponse:
    raw_token = request.GET.get("token", "").strip()
    if not raw_token:
        return render(
            request,
            "authapp/generic_error.html",
            {"message": GENERIC_MAGIC_ERROR},
            status=400,
        )

    token = consume_magic_token(raw_token)
    if token is None:
        return render(
            request,
            "authapp/generic_error.html",
            {"message": GENERIC_MAGIC_ERROR},
            status=400,
        )

    candidate = CanvasStudentCandidate(
        canvas_user_id=token.canvas_user_id,
        full_name="",
        short_name="",
        sortable_name="",
        email="",
        login_id=token.requested_login_id,
    )

    try:
        client = CanvasClient()
        search_results = client.search_course_students(token.course_id, token.requested_login_id)
        resolved = next((c for c in search_results if c.canvas_user_id == token.canvas_user_id), None)
        if resolved is not None:
            candidate = resolved
    except CanvasAPIError:
        pass

    student = upsert_student_identity(candidate)
    request.session["student_identity_id"] = student.id
    request.session["canvas_user_id"] = student.canvas_user_id
    request.session["course_id"] = token.course_id

    return redirect("app-home")


@require_GET
def app_home(request: HttpRequest) -> HttpResponse:
    student_id = request.session.get("student_identity_id")
    if not student_id:
        course_id = request.session.get("course_id")
        if course_id:
            return redirect(f"{reverse('landing')}?course_id={course_id}")
        return render(
            request,
            "authapp/generic_error.html",
            {"message": "No active session. Open the app from Canvas to sign in."},
            status=401,
        )

    from .models import StudentIdentity

    student = StudentIdentity.objects.filter(id=student_id).first()
    if student is None:
        request.session.flush()
        return render(
            request,
            "authapp/generic_error.html",
            {"message": "No active session. Open the app from Canvas to sign in."},
            status=401,
        )

    return render(request, "authapp/app_home.html", {"student": student})
