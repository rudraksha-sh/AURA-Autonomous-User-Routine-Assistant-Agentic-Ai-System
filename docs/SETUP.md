# Setup and deployment

Run commands from the project checkout containing `backend/` and `frontend/`. Verification used Python 3.13 and Node.js 24.

## Backend

Use PowerShell in the repository root only to enter the right folder. Run Python, Alembic and Docker Compose from `backend/`. Run npm from `frontend/` in a separate terminal. The Codex CLI is optional.


```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
if (!(Test-Path .env)) { Copy-Item .env.example .env }
docker compose up -d postgres
```

If Docker reports that `aura-postgres` already exists, inspect its published port with `docker port aura-postgres 5432`. If it is your existing AURA development database on `127.0.0.1:5433`, keep it and use `docker start aura-postgres` only if stopped. Keep its data volume. Back up an existing development database before applying migrations.

Set `DATABASE_URL=postgresql+psycopg://aura_user:aura_password@127.0.0.1:5433/aura_db` in `backend/.env` for the provided Compose service. Generate a local JWT secret using `python -c "import secrets; print(secrets.token_urlsafe(48))"`. The console email provider emits development OTPs locally. Keep `AI_PROVIDER=disabled` for offline planning. The new graph requires no Google or OpenRouter credentials.

```powershell
.\.venv\Scripts\python -m alembic upgrade head
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

## Frontend

From the repository root in a second terminal:

```powershell
cd frontend
npm ci
if (!(Test-Path .env.local)) { Copy-Item .env.example .env.local }
npm run dev
```

Open `http://localhost:3000`, sign in and select **Planner → Agent workflows**. The default rewrite forwards API requests to `http://127.0.0.1:8000`. Swagger is at `http://127.0.0.1:8000/docs`.

## Verification

```powershell
# From backend
.\.venv\Scripts\python -m pytest unit_tests tests -q
.\.venv\Scripts\python -m alembic heads

# From frontend
npm run lint
npx tsc --noEmit
npm run build
```

For PostgreSQL tests, provision a disposable loopback instance and database named `aura_workflow_test`. Set `AURA_TEST_POSTGRES_URL` to its `postgresql+psycopg` URL with an explicit loopback port and run `python -m pytest tests -q` in the backend environment. The test harness creates and drops only its own unique schema. For migrations, set `DATABASE_URL` to a disposable target and run `python -m alembic upgrade head` followed by `python -m alembic check`.

## Staging deployment

1. Provision managed PostgreSQL with TLS, backups and a dedicated API role. Use a separate migration role where available.
2. On Render set root to `backend`, build to `pip install -r requirements.txt`, and start to `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Run `alembic upgrade head` once as a release step. Configure the production environment, database URL, strong JWT secret, frontend URL, exact CORS origins and SMTP. Generate a key using `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` before enabling Google. Keep one API worker while OAuth state and limits are process-local. [Render FastAPI deployment](https://render.com/docs/deploy-fastapi)
3. On Vercel set root to `frontend`, use the Next.js preset, install with `npm ci`, and build with `npm run build`. Set `AURA_API_SERVER_URL` to the HTTPS backend origin. [Next.js on Vercel](https://vercel.com/docs/frameworks/full-stack/nextjs)
4. Verify signup, preview, approval, grant exhaustion, verification, undo and backup restore in staging. Use separately authorized test accounts for live provider verification.
