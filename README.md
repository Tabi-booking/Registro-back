# Tabi Formulario Backend

Production-ready FastAPI backend for the Tabi restaurant onboarding wizard. It runs as an independent microservice alongside the existing `bytte-backend`, connecting to the same Supabase/PostgreSQL database but managing its own set of tables.

---

## Architecture Overview

```
formulario-backend/
├── app/
│   ├── api/           # FastAPI routers + dependency injection
│   ├── core/          # Config, security helpers, custom exceptions
│   ├── database/      # SQLAlchemy async engine + Redis client
│   ├── models/        # SQLAlchemy ORM models (new tables only)
│   ├── schemas/       # Pydantic V2 request/response schemas
│   ├── services/      # Business logic layer
│   ├── repositories/  # Data access layer (repository pattern)
│   ├── middleware/     # Logging, rate limiting, security headers
│   └── utils/         # Validators, sanitizers
├── alembic/           # Database migrations (new tables only)
├── tests/             # Async tests with httpx + in-memory SQLite
└── docker/            # Dockerfile + docker-compose
```

**Key design decisions:**
- Clean Architecture: API → Service → Repository → DB
- All endpoints return `{"success": bool, "data": ..., "message": "..."}` envelopes
- Redis caches onboarding status for 60 s; invalidated on every write
- Every write is logged to `audit_logs`
- Rate limiting: 5 req/min on auth, 60 req/min on onboarding
- JWT: 15-min access token + 7-day refresh token (hashed in DB)

---

## Local Setup

### Prerequisites
- Python 3.13+
- Redis (local or Docker)
- Access to Tabi Supabase instance

### Steps

```bash
cd formulario-backend

# 1. Create virtual environment
python -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements/dev.txt

# 3. Configure environment
cp .env.example .env
# Edit .env and set DB_PASSWORD, SECRET_KEY, etc.

# 4. Run database migrations
alembic upgrade head

# 5. Start the server
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

The API will be available at `http://localhost:8001`.

Interactive docs: `http://localhost:8001/docs`

---

## Docker Setup

```bash
cd formulario-backend

# Build and start all services
docker compose -f docker/docker-compose.yml up --build

# Or run in background
docker compose -f docker/docker-compose.yml up -d --build
```

Services:
| Service | Port | Description |
|---------|------|-------------|
| `api` | 8001 | FastAPI application |
| `redis` | 6380 | Redis cache + rate limiter |
| `worker` | — | Background worker placeholder |

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DB_HOST` | Yes | — | PostgreSQL host (Supabase) |
| `DB_PORT` | No | 5432 | PostgreSQL port |
| `DB_USER` | Yes | — | PostgreSQL user |
| `DB_PASSWORD` | Yes | — | PostgreSQL password |
| `DB_NAME` | No | postgres | Database name |
| `DB_SSLMODE` | No | require | SSL mode |
| `REDIS_HOST` | No | localhost | Redis host |
| `REDIS_PORT` | No | 6379 | Redis port |
| `SECRET_KEY` | Yes | — | JWT signing key (min 32 chars) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | 15 | JWT access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | 7 | Refresh token lifetime |
| `CORS_ORIGINS` | No | localhost:3000 | Comma-separated CORS origins |
| `MAX_FILE_SIZE_MB` | No | 10 | Max upload size in MB |
| `STORAGE_URL` | No | — | Supabase storage base URL |
| `SUPABASE_URL` | No | — | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | No | — | Supabase service role key |
| `ENVIRONMENT` | No | development | development/staging/production |

---

## API Endpoints Reference

### Authentication

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/auth/register` | No | Register restaurant owner |
| POST | `/api/v1/auth/login` | No | Login → access + refresh tokens |
| POST | `/api/v1/auth/refresh` | No | Refresh access token |
| POST | `/api/v1/auth/logout` | No | Revoke refresh token |
| GET | `/api/v1/auth/me` | JWT | Get current user |

### Onboarding

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/onboarding/start` | JWT | Start onboarding session |
| POST | `/api/v1/onboarding/step/{1-7}` | JWT | Save a wizard step |
| PATCH | `/api/v1/onboarding/step/{1-7}` | JWT | Update a saved step |
| GET | `/api/v1/onboarding/status` | JWT | Get progress + percentage |
| POST | `/api/v1/onboarding/submit` | JWT | Final submit |
| GET | `/api/v1/onboarding/{restaurant_id}` | Admin | Full data (admin only) |

### Uploads

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/uploads/presigned` | JWT | Get presigned upload URL |
| POST | `/api/v1/uploads/confirm` | JWT | Confirm upload completed |

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Service health + Redis status |

---

## Running Migrations

```bash
# Apply all migrations
alembic upgrade head

# Check current revision
alembic current

# Create a new migration (auto-detect from models)
alembic revision --autogenerate -m "description"

# Rollback one step
alembic downgrade -1
```

**Important:** The Alembic env.py is configured with an `include_name` filter so it only touches the 9 new tables (`restaurant_users`, `restaurant_onboarding_progress`, etc.) and will never modify existing Tabi/bytte tables.

---

## Running Tests

```bash
# All tests with coverage
pytest

# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# With verbose output
pytest -v --tb=long

# Specific test
pytest tests/integration/test_auth.py::TestLogin::test_login_success
```

Tests use an in-memory SQLite database so no real Postgres/Redis connections are needed. Redis is mocked via `AsyncMock`.

---

## How the Onboarding Flow Works

```
1. User registers → POST /auth/register
2. User logs in   → POST /auth/login → receives JWT + refresh token
3. Start wizard   → POST /onboarding/start → creates restaurant stub + progress record
4. Fill step 1    → POST /onboarding/step/1 → validated, persisted, progress updated
   ... repeat for steps 2–7 (steps 4–7 are optional)
5. Check progress → GET /onboarding/status → {current_step, percentage, steps_completed}
6. Submit         → POST /onboarding/submit → validates steps 1+2+3 done → status=submitted
7. Admin reviews  → GET /onboarding/{restaurant_id} → full data view
```

**Completion percentage logic:**
- Steps 1, 2, 3 are **required** → 20% each = 60% total when all done
- Steps 4, 5, 6, 7 are **optional** → 10% each = 40% total when all done
- Minimum to submit: steps 1+2+3 = 60%

---

## How It Connects to bytte-backend

Both services share the same Supabase PostgreSQL database. This service:

- **Only reads** existing `bytte` tables (e.g., `restaurante`) for foreign key context
- **Writes** exclusively to the 9 new `formulario` tables
- Runs on **port 8001** (bytte-backend uses 8000/8030)
- Uses the same DB credentials but a different connection pool

In production, a reverse proxy (nginx/Caddy) routes:
- `/api/` → bytte-backend (port 8000)
- `/formulario/` or a subdomain → this service (port 8001)

---

## Security Notes

- Passwords hashed with bcrypt (passlib)
- Refresh tokens are SHA-256 hashed before storage — raw token never persisted
- All text inputs sanitized with `bleach` to strip HTML
- Phone numbers validated and normalized to E.164 via `phonenumbers`
- Security headers applied to all responses (HSTS, X-Frame-Options, CSP, etc.)
- Rate limiting via Redis sliding window
- CORS restricted to configured origins
- Docs (`/docs`, `/redoc`) disabled in `production` environment
