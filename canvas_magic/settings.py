import os
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-secret-key")
DEBUG = env_bool("DEBUG", False)

ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "authapp",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "canvas_magic.middleware.CanvasFrameAncestorsMiddleware",
]

ROOT_URLCONF = "canvas_magic.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "canvas_magic.wsgi.application"
ASGI_APPLICATION = "canvas_magic.asgi.application"

if env_bool("USE_SQLITE", False):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "canvas_magic"),
            "USER": os.getenv("POSTGRES_USER", "canvas_magic"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", "canvas_magic"),
            "HOST": os.getenv("POSTGRES_HOST", "db"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
        }
    }

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8000")
CANVAS_API_URL = os.getenv("CANVAS_API_URL", "")
CANVAS_API_TOKEN = os.getenv("CANVAS_API_TOKEN", "")
MAGIC_LINK_TTL_SECONDS = 15 * 60

CROSS_SITE_COOKIES = env_bool("CROSS_SITE_COOKIES", True)

if CROSS_SITE_COOKIES:
    # Required for iframe usage on a different site (Canvas).
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "None"
    CSRF_COOKIE_SAMESITE = "None"
else:
    SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", False)
    CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", False)
    SESSION_COOKIE_SAMESITE = "None" if SESSION_COOKIE_SECURE else "Lax"
    CSRF_COOKIE_SAMESITE = "None" if CSRF_COOKIE_SECURE else "Lax"

# Optional explicit trusted origins for reverse-proxy / custom host setups.
csrf_trusted_origins_env = [
    value.strip()
    for value in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
    if value.strip()
]
if csrf_trusted_origins_env:
    CSRF_TRUSTED_ORIGINS = csrf_trusted_origins_env
else:
    parsed_app = urlparse(APP_BASE_URL)
    CSRF_TRUSTED_ORIGINS = [f"{parsed_app.scheme}://{parsed_app.netloc}"] if parsed_app.scheme and parsed_app.netloc else []

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
