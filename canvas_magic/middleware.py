from urllib.parse import urlparse

from django.conf import settings


class CanvasFrameAncestorsMiddleware:
    """Restrict iframe embedding to self and the configured Canvas origin."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        canvas_origin = ""
        if settings.CANVAS_API_URL:
            parsed = urlparse(settings.CANVAS_API_URL)
            if parsed.scheme and parsed.netloc:
                canvas_origin = f"{parsed.scheme}://{parsed.netloc}"

        policy = "frame-ancestors 'self'"
        if canvas_origin:
            policy = f"{policy} {canvas_origin}"

        response["Content-Security-Policy"] = policy
        return response
