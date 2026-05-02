# Canvas Magic-Link Login

A Django-based non-LTI login workaround for Canvas-embedded applications. Enables secure authentication via magic links sent directly to Canvas Inbox.

## Features

- **Magic Link Authentication**: One-time, time-limited (15 minutes) login links sent to Canvas Inbox
- **Canvas Integration**: Looks up enrolled students in Canvas courses
- **Iframe Compatible**: Works seamlessly when embedded in Canvas as an iframe
- **Cross-Origin Support**: Configured for secure cross-site cookies in Canvas environments
- **Docker Ready**: Full Docker and Docker Compose setup included

## How It Works

1. User visits the embedded app and enters their login ID (e.g., `/? course_id=<canvas_course_id>`)
2. App searches enrolled students in the specified Canvas course
3. If exactly one match is found, a magic link is generated and sent to that user's Canvas Inbox
4. User clicks the link to authenticate and establish a local session
5. Canvas student identity is stored locally for future requests

## Prerequisites

- Docker and Docker Compose
- Canvas instance with API access
- Valid Canvas API credentials

## Environment Setup

1. Copy `.env.example` to `.env` (if it exists, or create one):

```bash
cp .env.example .env
```

2. Configure the following variables in `.env`:

```env
CANVAS_API_URL=https://your-canvas-instance.instructure.com
CANVAS_API_TOKEN=your_canvas_api_token
APP_BASE_URL=http://localhost:8998
DJANGO_SECRET_KEY=your-secret-key-here
CROSS_SITE_COOKIES=True
POSTGRES_DB=canvasmagic
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=admin
```

### Environment Variable Details

| Variable | Purpose |
|----------|---------|
| `CANVAS_API_URL` | Your Canvas instance URL |
| `CANVAS_API_TOKEN` | Canvas API authentication token |
| `APP_BASE_URL` | Base URL where app is deployed |
| `DJANGO_SECRET_KEY` | Django secret key for security |
| `CROSS_SITE_COOKIES` | Enable SameSite=None cookies for iframe mode |
| `POSTGRES_*` | PostgreSQL database credentials |
| `DJANGO_SUPERUSER_*` | Admin account credentials |

## Running the Application

### With Docker Compose (Recommended)

First time setup:

```bash
docker compose up --build
```

Subsequent runs:

```bash
docker compose up
```

The application will be available at `http://localhost:8998`

### Notes

- Code changes are bind-mounted, so updates apply without rebuilding
- Database persists in the `db` volume
- Use `docker compose down` to stop containers

## Django Admin

Access the Django admin interface at `http://localhost:8998/admin/`

- Admin credentials are set from `.env` variables on first run
- To update admin credentials, modify the user directly in the admin panel or rebuild the container

## Project Structure

```
.
├── authapp/                 # Main authentication app
│   ├── views.py             # Request handlers
│   ├── services.py          # Canvas API integration
│   ├── models.py            # Database models
│   ├── forms.py             # Form definitions
│   ├── urls.py              # URL routing
│   ├── migrations/          # Database migrations
│   └── templates/           # HTML templates
├── canvas_magic/            # Django project settings
│   ├── settings.py          # Project configuration
│   ├── urls.py              # Root URL routing
│   ├── wsgi.py              # WSGI entry point
│   ├── asgi.py              # ASGI entry point
│   └── middleware.py        # Custom middleware
├── manage.py                # Django management script
├── docker-compose.yml       # Compose configuration
├── Dockerfile               # Container definition
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

## Development

### Local Setup (without Docker)

1. Create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set environment variables in `.env`

4. Run migrations:

```bash
python manage.py migrate
```

5. Create a superuser:

```bash
python manage.py createsuperuser
```

6. Start the development server:

```bash
python manage.py runserver
```

### Running Tests

```bash
python manage.py test
```

## API Endpoints

- `GET /` - Login form
- `POST /request-magic-link/` - Request authentication link
- `GET /auth/<token>/` - Authenticate via magic link
- `GET /admin/` - Django admin interface

## Security Considerations

- Magic links expire after 15 minutes
- Links are single-use only
- Secure cookies enabled by default
- CSRF protection active
- Canvas API tokens stored securely in environment

## Troubleshooting

### Container won't start
- Check `.env` file exists and has required variables
- Verify Canvas API credentials are correct
- Check Docker logs: `docker compose logs`

### Database errors
- Ensure migrations are run: `docker compose exec web python manage.py migrate`
- Check PostgreSQL is running and accessible

### Canvas API errors
- Verify `CANVAS_API_URL` and `CANVAS_API_TOKEN` are correct
- Check Canvas API is accessible from your network
- Verify user has Canvas API permissions

## License

This project is licensed under the MIT License—see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues or questions, please open an issue on the project repository.

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
