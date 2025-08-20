
## FastAPI Boilerplate

Production-ready structure with auth, users, settings, logging, and Docker. Targets Python 3.12 and FastAPI 0.115+.

### Quickstart

1) Create and fill `.env` (see `.env.example`):
```
SECRET_KEY=please-change-me-to-a-32char-min-secret-key-012345
DATABASE_URL=sqlite:///./app.db
BACKEND_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
ROOT_PATH=
LOG_LEVEL=INFO
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

2) Install and run:
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --proxy-headers
```

3) Open docs: `http://127.0.0.1:8000/docs`

### API
- Base path: `settings.API_V1_PREFIX` (default `/api/v1`)
- Health: `GET /healthz` (public)
- Auth: `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me`
- Managers: CRUD under `/api/v1/managers` with role-based access

### Configuration
Edit `settings.py` or set env vars in `.env`:
- `SECRET_KEY` (required, min 32 chars)
- `DATABASE_URL` (default sqlite)
- `BACKEND_CORS_ORIGINS` (comma-separated)
- `ALLOWED_HOSTS` (comma-separated; default `*`)
- `ROOT_PATH` (behind proxy / gateway)
- `ENABLE_GZIP` (default true)
- `USE_PROXY_HEADERS` (default false)
- `ENABLE_HTTPS_REDIRECT` (default false)
- `DB_POOL_SIZE`, `DB_MAX_OVERFLOW` (for non-sqlite)

### Lint & Format
```bash
ruff check
ruff format
```

### Docker
```bash
docker build -t fastapi-boilerplate .
docker run -p 8000:8000 --env-file .env fastapi-boilerplate
```

### Project Layout
```
app/
  main.py          # FastAPI app and middleware
  settings.py      # Settings via pydantic-settings
  logger.py        # Loguru configuration
  dependencies.py  # Auth and role dependencies
  utils/
    db.py          # SQLModel engine and session
    responses.py   # Standardized response helpers
  auth/
    routes.py
    service.py
    models.py
  user/
    routes.py
    service.py
    models.py
```
