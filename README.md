# Canvas Magic-Link Login (Django + Docker)

A non-LTI login workaround for Canvas-embedded apps.

## What it does

- Renders a simple login form in an iframe at `/?course_id=<canvas_course_id>`.
- Accepts `login_id` and looks up enrolled students in the given Canvas course.
- If exactly one candidate matches, sends a one-time 15-minute magic link to Canvas Inbox.
- Magic link authenticates in a new tab and stores the Canvas student identity locally.

## Environment

1. Copy `.env.example` to `.env`.
2. Set:
- `CANVAS_API_URL`
- `CANVAS_API_TOKEN`
- `APP_BASE_URL`
- `DJANGO_SECRET_KEY`
- `POSTGRES_*`
- `CROSS_SITE_COOKIES` (set `True` for Canvas iframe mode)

For iframe POSTs inside Canvas, use cross-site cookie settings (`SameSite=None; Secure`), enabled by default via `CROSS_SITE_COOKIES=True`.

## Run with Docker

```bash
docker compose up --build
```

App will be available at `http://localhost:8998`.

After the first build, use:

```bash
docker compose up
```

Code changes are bind-mounted (`.:/app`) so they apply without rebuilding.

## Django admin

- Admin URL: `http://localhost:8998/admin/`
- Admin user can be auto-created from `.env`:
  - `DJANGO_SUPERUSER_USERNAME`
  - `DJANGO_SUPERUSER_EMAIL`
  - `DJANGO_SUPERUSER_PASSWORD`

If you change credentials after first boot, restart containers and update the user manually if needed.

## Managing iframe embed codes

In Django admin, open `Iframe Embed Codes` and create a record with `course_id`.

- `Launch URL` is generated as: `APP_BASE_URL/?course_id=<course_id>`
- `Iframe Embed Code` is generated for copy/paste into Canvas pages/modules.

## Run tests locally

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
USE_SQLITE=true python manage.py test
```

## Main routes

- `GET /?course_id=<id>`
- `POST /auth/request-link`
- `GET /auth/magic?token=<opaque_token>`
- `GET /app/home`
