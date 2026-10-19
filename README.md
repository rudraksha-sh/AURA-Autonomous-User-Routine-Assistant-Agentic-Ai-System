# AURA

AURA is an autonomous routine assistant for organizing goals and tasks, planning daily work, and using AI to help users act on their schedules. AI generated changes remain proposals that require user confirmation.

## Architecture

- `frontend/`: Next.js application with the dashboard, goals, tasks, planning, and assistant experiences.
- `backend/`: FastAPI API, SQLAlchemy models and services, and Alembic database migrations.
- PostgreSQL stores user, goal, task, integration, and planning data.
- Google OAuth connects calendar and email services. OpenRouter provides optional AI features.

## Setup

1. Install Python and Node.js, and start PostgreSQL. From `backend/`, copy `.env.example` to `.env` and set database, JWT, Google OAuth, and optional OpenRouter credentials. The example documents each setting; replace every placeholder before use.
2. Install backend packages with `python -m pip install -r requirements-dev.txt` from `backend/`.
3. Install frontend packages with `npm ci` from `frontend/`.
4. Apply database migrations with `alembic upgrade head` from `backend/`.
5. Start the API with `uvicorn app.main:app --reload` from `backend/`, and the web app with `npm run dev` from `frontend/`.

Google OAuth requires an OAuth client configured in Google Cloud Console. Its redirect URI must match `GOOGLE_REDIRECT_URI`; add the local frontend origin to the OAuth consent configuration as appropriate.

## Tests and checks

Run backend tests from `backend/` with `pytest`. Run frontend checks from `frontend/` with `npm run lint` and `npm run build`.

## Implementation plan and status

The implementation is split into these checkpoints. Expected touch points were mapped before work began; the repository's existing code may add files as a phase requires.

| Phase | Expected files / areas | Status |
| --- | --- | --- |
| 0. Cleanup | `.gitignore`, tracked `aura/`, backend requirements, this README | Implemented |
| 1. Token encryption | backend config, crypto and integration services, env example, migration, tests | Planned |
| 2. Shared state | backend state/rate limiter, OAuth callback, compose, tests | Planned |
| 3. Auth hardening | backend auth models/routes/security/migrations/tests; frontend auth and services | Planned |
| 4. Prioritization | scoring service, task schemas/routes/tests, Tasks UI | Planned |
| 5. Calendar planner | planner service/schemas/routes/tests, daily planner UI | Planned |
| 6. Gmail suggestions | Google integration, schemas/routes/tests, task metadata/migration, dashboard UI | Planned |
| 7. Assistant agent | assistant agent, AgentRun/migration/routes/tests, assistant UI | Planned |
| 8. Monitor and re-plan | notification model/service/job/routes/migration/tests, Header UI | Planned |
| 9. Final pass | task ordering, route prefixes, README and full verification | Planned |

## Implemented vs planned

**Implemented:** user authentication, goals and tasks, daily planning, Google OAuth integration, AI planning and assistant tool registry.

**Planned in this roadmap:** encrypted Google tokens, shared Redis state, cookie and refresh-token auth, prioritization scores, calendar-aware planning, Gmail task suggestions, a confirmation-based tool-calling agent, notifications and re-planning, and final route/task-order consistency work.

**Verification:** backend unit tests, frontend lint, TypeScript checks, and frontend production build pass in the current development environment.
