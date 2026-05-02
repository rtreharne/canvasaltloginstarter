from django.contrib import admin
from django.utils.html import format_html

from .models import IframeEmbedCode, MagicLinkToken, StudentIdentity


@admin.register(StudentIdentity)
class StudentIdentityAdmin(admin.ModelAdmin):
    list_display = ("canvas_user_id", "full_name", "email", "last_auth_at")
    search_fields = ("canvas_user_id", "full_name", "email")


@admin.register(MagicLinkToken)
class MagicLinkTokenAdmin(admin.ModelAdmin):
    list_display = ("id", "canvas_user_id", "course_id", "expires_at", "used_at", "created_at")
    search_fields = ("canvas_user_id", "course_id", "requested_login_id")


@admin.register(IframeEmbedCode)
class IframeEmbedCodeAdmin(admin.ModelAdmin):
    list_display = ("name", "course_id", "active", "updated_at")
    list_filter = ("active",)
    search_fields = ("name", "course_id")
    readonly_fields = ("launch_url_display", "iframe_embed_code")
    fields = (
        "name",
        "course_id",
        "width",
        "height",
        "active",
        "notes",
        "launch_url_display",
        "iframe_embed_code",
    )

    @admin.display(description="Launch URL")
    def launch_url_display(self, obj: IframeEmbedCode) -> str:
        if not obj.pk:
            return "Save first to generate URL."
        url = obj.launch_url()
        return format_html('<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>', url, url)

    @admin.display(description="Iframe Embed Code")
    def iframe_embed_code(self, obj: IframeEmbedCode) -> str:
        if not obj.pk:
            return "Save first to generate embed code."
        code = obj.iframe_html()
        return format_html(
            '<textarea rows="5" style="width:100%;font-family:monospace;" readonly>{}</textarea>',
            code,
        )
