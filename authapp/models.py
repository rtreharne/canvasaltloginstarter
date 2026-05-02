from django.db import models
from django.conf import settings
from urllib.parse import quote_plus


class StudentIdentity(models.Model):
    canvas_user_id = models.BigIntegerField(unique=True)
    full_name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=255, blank=True)
    sortable_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    last_auth_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.full_name} ({self.canvas_user_id})"


class MagicLinkToken(models.Model):
    token_hash = models.CharField(max_length=64, unique=True)
    canvas_user_id = models.BigIntegerField()
    course_id = models.CharField(max_length=64)
    requested_login_id = models.CharField(max_length=255)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    request_ip = models.GenericIPAddressField(null=True, blank=True)
    request_user_agent = models.TextField(blank=True)
    request_metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["canvas_user_id", "course_id"]),
            models.Index(fields=["expires_at", "used_at"]),
        ]

    def __str__(self) -> str:
        return f"token:{self.id} user:{self.canvas_user_id}"


class IframeEmbedCode(models.Model):
    name = models.CharField(max_length=120, unique=True)
    course_id = models.CharField(max_length=64)
    width = models.CharField(max_length=32, default="100%")
    height = models.PositiveIntegerField(default=720)
    active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.course_id})"

    def launch_url(self) -> str:
        base = settings.APP_BASE_URL.rstrip("/")
        return f"{base}/?course_id={quote_plus(self.course_id)}"

    def iframe_html(self) -> str:
        src = self.launch_url()
        return (
            f'<iframe src="{src}" width="{self.width}" height="{self.height}" '
            'style="border:0;" loading="lazy" '
            'referrerpolicy="strict-origin-when-cross-origin"></iframe>'
        )
