# AURA — Autonomous User Routine Assistant

AURA is an AI-assisted goal-planning application that transforms user goals into actionable tasks, supports progress tracking, and integrates with external services to make routine planning more useful.

## Project Status

AURA is under active development. The project includes a Next.js frontend, a FastAPI backend, authentication and email verification, goal and task workflows, AI-assisted planning, and Google OAuth integration.

AI planning uses OpenRouter when configured, with a deterministic, rule-based fallback.

**Current testing status (25 October 2026):**
- The backend integration suite passes independently: 79 tests passed.
- The combined `unit_tests/` and `tests/` run still has an outstanding failure in `test_ai_plan_success`, where registration returns `409 Email is already registered`.
- The combined test suite is not yet fully green. Investigate test database initialization and isolation before treating the branch as release-ready.

## Live Deployment

- **Frontend:** https://aura-autonomous-user-routine-assist.vercel.app
- **Backend API:** https://aura-backend-cz7k.onrender.com

The backend may take time to wake up when hosted on an idle instance. Use the configured health endpoint or API documentation to verify availability.

## Main Capabilities

- **Authentication:** Registration, email verification, login, and token-based API authentication.
- **Goal management:** Create and manage goals with titles, descriptions, priorities, deadlines, and the `continue_without_asking` preference.
- **Task planning:** Generate a proposed plan for a goal, preview it, and save tasks.
- **AI planning:** Use OpenRouter for AI-generated plans when configured.
- **Rule-based fallback:** Generate a deterministic plan when the AI provider is unavailable or returns an error.
- **Task persistence:** Store task status, priority, estimated duration, position, and optional deadlines.
- **Idempotent plan saving:** Support idempotency keys to reduce duplicate writes when save requests are retried.
- **Google integration:** OAuth connection flow and persisted integration status and credentials. Available Google scopes depend on the configured consent screen and the permissions granted by the user.
- **API documentation:** FastAPI-generated OpenAPI documentation when enabled by the deployment configuration.

Feature availability can differ between local and deployed versions while development continues.

## Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | Next.js, React, TypeScript |
| Backend | Python, FastAPI, Pydantic |
| Persistence | SQLAlchemy, Alembic, PostgreSQL |
| Testing | Pytest, SQLite-backed unit tests, PostgreSQL-backed integration tests |
| AI planning | OpenRouter with a rule-based fallback |
| Authentication | JWT-based API authentication and email verification |
| Google integration | Google OAuth |
| Hosting | Vercel, Render, Neon PostgreSQL |

## Architecture Overview

```text
Browser
   |
   v
Next.js frontend (Vercel)
   |
   | HTTPS / JSON API
   v
FastAPI backend (Render)
   |
   +--------------------+
   |                    |
   v                    v
PostgreSQL           OpenRouter
(Neon)               (AI planning)
   |
   v
Users, goals, tasks, integrations, agent runs

Google OAuth
   |
   v
Google authorization
   |
   v
Backend callback
   |
   v
Persisted integration
```

## Repository Layout

```text
backend/
  app/
    agents/          # Agent and planner service logic
    api/routes/      # FastAPI route handlers
    core/            # Configuration, security, dependencies
    integrations/    # External provider integrations
    models/          # SQLAlchemy models
    schemas/         # Pydantic request/response schemas
    services/        # Business logic
  alembic/           # Database migrations
  scripts/           # Development and data utilities
  tests/             # Backend/API integration tests
  unit_tests/        # Unit and SQLite-backed tests
  docker-compose.yml # Local PostgreSQL service

frontend/
  app/               # Next.js routes and pages
  services/          # API service clients
```

Exact filenames and directories may evolve as the project changes.

## Local Development Setup

### Prerequisites

- Git
- Python compatible with the backend dependencies
- Node.js and npm compatible with the frontend
- Docker Desktop with Docker Compose, or a separately configured PostgreSQL instance
- An OpenRouter API key to test live AI planning
- Google OAuth credentials to test Google integration

### 1. Clone the repository

```powershell
git clone https://github.com/rudraksha-sh/AURA-Autonomous-User-Routine-Assistant-Agentic-Ai-System.git
cd AURA-Autonomous-User-Routine-Assistant-Agentic-Ai-System
```

### 2. Configure and start PostgreSQL

Open Docker Desktop and wait for the Docker Engine to start.

From the backend directory:

```powershell
cd backend
docker compose up -d postgres
docker ps
```

The current Compose configuration maps host port `5433` to PostgreSQL port `5432` inside the container.

The Compose service defines the `aura_db` database. The integration test configuration expects a separate `aura_test_db` database. Verify that the dedicated test database exists before running the integration tests.

Do not point test cleanup fixtures at a development or production database.

### 3. Set up the backend

From the `backend` directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create a local `.env` file using the repository's environment example, if available. Configure the exact variables required by `backend/app/core/config.py`.

Important configuration categories include:

- `DATABASE_URL` — PostgreSQL or other supported database connection URL.
- `JWT_SECRET_KEY` — secret used to sign authentication tokens.
- `OPENROUTER_API_KEY` — AI provider API key.
- `AI_PROVIDER` — AI provider selection.
- `CORS_ORIGINS` — permitted frontend origins.
- Email and OTP provider settings.
- Google OAuth client ID, client secret, and redirect URI.

Never commit `.env` files or share secret values.

Apply database migrations from the backend directory:

```powershell
alembic upgrade head
```

Start the API:

```powershell
uvicorn app.main:app --reload
```

The local API is typically available at `http://127.0.0.1:8000`. If Swagger UI is enabled, open `http://127.0.0.1:8000/docs`.

### 4. Set up the frontend

Open a second terminal at the repository root:

```powershell
cd frontend
npm install
```

Configure the frontend's backend API base URL using the environment variable expected by the frontend configuration. For local development, the backend is typically available at `http://127.0.0.1:8000`.

Start the frontend:

```powershell
npm run dev
```

Open `http://localhost:3000`.

## Testing

Run commands from the `backend` directory with the project's intended Python environment activated.

### Run unit tests

```powershell
python -m pytest unit_tests/ -q
```

### Run integration tests

```powershell
python -m pytest tests/ -x -q --tb=short
```

### Run both suites

```powershell
python -m pytest unit_tests/ tests/ -x -q --tb=short
```

The integration suite has passed independently with 79 tests. The combined run has an outstanding `test_ai_plan_success` failure caused by a duplicate-email response during registration. The database initialization and test isolation issue remains unresolved.

SQLite-backed tests do not, by themselves, verify PostgreSQL connectivity, live OpenRouter requests, Google OAuth, or deployed service availability.

Before merging or deploying, review the complete test output and verify relevant workflows in the browser.

## Google OAuth Configuration

For a deployed backend, the Google OAuth redirect URI must exactly match the URI configured in Google Cloud Console and the backend environment.

Current deployed callback URI:

```text
https://aura-backend-cz7k.onrender.com/api/integrations/google/callback
```

Also verify that:

- The OAuth consent screen is configured for the intended users.
- Required scopes are configured and consented to.
- The backend's Google client ID and client secret are set in the hosting environment.
- The frontend origin is included in backend CORS configuration where required.
- Access tokens, refresh tokens, and client secrets are never committed to Git.

## Deployment Notes

- **Frontend:** Vercel.
- **Backend:** Render.
- **Database:** Neon PostgreSQL.
- Configure environment variables in hosting dashboards rather than committing production secrets.
- Apply Alembic migrations as part of a controlled backend release.
- After deployment, verify registration, email verification, login, goal creation, plan preview and save, task persistence, and Google connection status.

## Security Notes

- Never commit `.env` files, access tokens, refresh tokens, API keys, database passwords, or OAuth client secrets.
- Use a strong, unique production JWT secret.
- Restrict CORS to trusted frontend origins.
- Use HTTPS for deployed frontend and backend traffic.
- Grant only the Google scopes the application requires.
- Rotate credentials immediately if they are accidentally exposed.

## Development Workflow

1. Pull the latest changes before starting work.
2. Create a feature branch for significant changes.
3. Make focused changes and run relevant tests.
4. Inspect `git status` and review the diff before committing.
5. Keep local backups and Python cache files out of commits unless intentionally required.
6. Push the branch and review changes before merging or deployment.

## License

No license information is currently specified. Add a `LICENSE` file and update this section if the project is released under a particular license.
