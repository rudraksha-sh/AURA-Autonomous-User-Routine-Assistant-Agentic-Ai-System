AURA — Autonomous User Routine Assistant
AURA is an AI-assisted goal-planning application that turns a user's goals into actionable tasks, supports progress tracking, and provides integrations intended to make routine planning more useful.
Project Status
AURA is under active development. The current implementation includes a web frontend, a FastAPI backend, authentication, goal/task workflows, planner endpoints, and Google OAuth integration. AI planning uses OpenRouter when configured and includes a deterministic rule-based fallback.
Status note: Recent backend test runs exposed outstanding issues in OTP test fixtures, planner deadline validation, and an OAuth test assertion. Run the backend test suite before treating the current branch as release-ready.

Live Deployment
- Frontend: https://aura-autonomous-user-routine-assist.vercel.app
- Backend API: https://aura-backend-cz7k.onrender.com
The backend may take time to wake up on an idle hosting instance. Use the API's configured health/docs endpoints to verify availability.
Main Capabilities
- Account access: registration, email verification, login, and token-based authentication.
- Goal management: create and manage goals, including title, description, priority, deadline, and the continue_without_asking preference.
- Task planning: generate a proposed task plan for a goal, preview the plan, and save tasks.
- Deterministic fallback: provide a rule-based plan when the AI provider is unavailable or returns an error.
- Task persistence: save task status, priority, estimated duration, position, and optional deadline.
- Idempotent plan saving: planner save requests support an idempotency key to reduce duplicate writes on retries.
- Google integration: OAuth connection flow and persisted integration status/credentials. Available scopes include Google account identity and read access to Gmail, Calendar, and Drive, subject to the configured consent screen and granted scopes.
- API documentation: FastAPI-generated OpenAPI documentation when enabled by the deployment configuration.
Feature availability may differ between local and deployed versions as development continues.
Technology Stack
Layer	Technologies
Frontend	Next.js, React, TypeScript
Backend	Python, FastAPI, Pydantic
Persistence	SQLAlchemy, Alembic, PostgreSQL
Local/test database	SQLite is used by selected tests
AI planning	OpenRouter with a rule-based fallback
Authentication	JWT-based API authentication and email verification
Google integration	Google OAuth
Hosting	Vercel (frontend), Render (backend), Neon PostgreSQL (database)


Architecture Overview
Browser
  |
  v
Next.js frontend (Vercel)
  |
  | HTTPS / JSON API
  v
FastAPI backend (Render)
  |--------------------|
  v                    v
PostgreSQL          OpenRouter
(Neon)              (AI planning)
  |
  v
Goals, tasks, users, integrations, agent runs

Google OAuth
  |
  v
Google authorization -> backend callback -> persisted integration
Repository Layout
backend/
  app/
    agents/          # Agent/planner service logic
    api/routes/      # FastAPI route handlers
    core/             # Configuration, security, dependencies
    integrations/    # External provider integrations
    models/          # SQLAlchemy models
    schemas/         # Pydantic request/response schemas
    services/        # Business logic
  alembic/            # Database migrations
  tests/              # Backend/API tests
  unit_tests/         # Unit and SQLite-backed tests

frontend/
  app/                # Next.js routes and pages
  services/           # API service clients
Exact filenames may evolve as the project changes.
Local Development Setup
Prerequisites
- Git
- Python compatible with backend dependencies
- Node.js and npm compatible with frontend dependencies
- PostgreSQL for a local full-stack environment, or a suitable development database URL
- OpenRouter API key to test live AI planning
- Google OAuth credentials to test Google integration
1. Clone the repository
git clone https://github.com/rudraksha-sh/AURA-Autonomous-User-Routine-Assistant-Agentic-Ai-System.git
cd AURA-Autonomous-User-Routine-Assistant-Agentic-Ai-System
2. Backend setup
In PowerShell:
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Create the backend environment file using the repository's example file if one exists. Do not commit .env files or share secrets.

Common configuration categories include:
- DATABASE_URL — database connection URL
- JWT_SECRET_KEY — secret used to sign authentication tokens
- OPENROUTER_API_KEY — AI provider key
- AI_PROVIDER — provider selection, if configured
- CORS_ORIGINS — allowed frontend origins
- Email/OTP provider settings
- Google OAuth client ID, client secret, and redirect URI
Use the exact variable names and defaults defined in backend/app/core/config.py and any environment example file.

Run database migrations:
alembic upgrade head
Start the backend from the backend directory:
uvicorn app.main:app --reload
The local API is typically available at http://127.0.0.1:8000. If Swagger UI is enabled, open http://127.0.0.1:8000/docs.
3. Frontend setup
Open a second terminal at the repository root:
cd frontend
npm install
Configure the frontend's backend API base URL using the variable expected by the frontend code or its environment example. For a local backend, configure it to point to http://127.0.0.1:8000; verify the exact variable name in frontend configuration.

Start the frontend:
npm run dev
Open http://localhost:3000.
Testing
Run backend tests from the backend directory:
python -m pytest
Run a specific test file:
python -m pytest .\unit_tests\test_sqlite_model_defaults.py -q
Use the project's intended virtual environment so pytest and application dependencies resolve consistently. SQLite tests do not verify connectivity to PostgreSQL, OpenRouter, Google OAuth, or deployed services.

Before merging or deploying, review the complete test output and verify relevant workflows in the browser.
Google OAuth Configuration
For a deployed backend, the Google OAuth redirect URI must exactly match the URI configured in Google Cloud Console and the backend environment.

Current deployed callback URI:
https://aura-backend-cz7k.onrender.com/api/integrations/google/callback
Also verify that:
- The OAuth consent screen is configured for the intended users.
- Required scopes are configured and consented to.
- The backend's Google client ID and client secret are set in the hosting environment.
- The frontend origin is included in backend CORS configuration where required.
- Tokens and client secrets are never committed to Git.
Deployment Notes
- Frontend: Vercel.
- Backend: Render.
- Database: PostgreSQL hosted on Neon.
- Configure environment variables in hosting dashboards rather than committing production secrets.
- Apply Alembic migrations as part of a controlled backend release.
- After deployment, verify registration/email verification, login, goal creation, plan preview/save, task persistence, and Google connection status.
Security Notes
- Never commit .env, access tokens, refresh tokens, API keys, database passwords, or OAuth client secrets.
- Use a strong, unique production JWT secret.
- Restrict CORS to trusted frontend origins.
- Use HTTPS for deployed frontend/backend traffic.
- Grant only the Google scopes the application needs.
- Rotate credentials immediately if they are accidentally exposed.
Development Workflow
1. Pull the latest changes before starting work.
2. Create a feature branch for significant changes.
3. Make focused changes and run relevant tests.
4. Inspect git status and review the diff before committing.
5. Keep local backups (for example, .bak files) out of commits unless intentionally part of the project.
6. Push the branch and review the changes before deployment.
License
No license information is specified here. Add a LICENSE file and update this section if the project is released under a particular license.