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

For PostgreSQL tests, use the disposable pgvector container `aura-pgvector-test-15432`. Set `AURA_TEST_POSTGRES_URL` to `postgresql+psycopg://aura_test:<URL-encoded-password>@127.0.0.1:15432/aura_workflow_test`. Docker forwards the host port to PostgreSQL on container port 5432. The fixture requires pgvector in `public` and cleans up the per-test schema and public sentinel it creates.

From `backend/`, run `python -m pytest unit_tests tests -q --tb=short -p no:cacheprovider` with a fresh `--basetemp`. For read-only migration verification, set `DATABASE_URL` to the same verified disposable URL and run `python -m alembic current`, `python -m alembic heads`, and `python -m alembic check`.

## Google read-only smoke test

Run only after explicit approval for live Google authentication and requests. Use a dedicated Google test account containing synthetic data, a dedicated local AURA account with Google disconnected, and an isolated local database. Keep provider write adapters empty and use the local console email provider.

1. In the dedicated Google Cloud test project, open **APIs & Services > Library**. Enable **Gmail API** (`gmail.googleapis.com`), **Google Calendar API** (`calendar-json.googleapis.com`) and **Google Drive API** (`drive.googleapis.com`). [Google API setup](https://developers.google.com/identity/protocols/oauth2/web-server)
2. Open **Google Auth Platform > Branding** and configure the app name, support email and developer contact. For an external test project, open **Audience**, keep it in **Testing**, and add the dedicated Google account under **Test users**. [Google consent setup](https://developers.google.com/workspace/guides/configure-oauth-consent)
3. In **Data Access > Add or Remove Scopes**, configure `openid`, `https://www.googleapis.com/auth/userinfo.email`, `https://www.googleapis.com/auth/gmail.readonly`, `https://www.googleapis.com/auth/calendar.freebusy`, and `https://www.googleapis.com/auth/drive.readonly`. Each runner invocation requests only the identity scopes and the selected service scope. [Google OAuth scopes](https://developers.google.com/identity/protocols/oauth2/scopes)
4. In **Clients > Create client**, select **Web application**. Under **Authorized redirect URIs**, add `http://localhost:8000/api/integrations/google/callback` exactly. Save and configure `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and the matching `GOOGLE_REDIRECT_URI` in private local configuration. Set a valid Fernet `INTEGRATION_TOKEN_KEY` and point `DATABASE_URL` at the isolated local database. [Google client setup](https://developers.google.com/workspace/guides/create-credentials)

The local smoke environment lives in gitignored `backend/.env.google-smoke/.env`. It targets `127.0.0.1:15432/aura_workflow_test`, uses its own token encryption and JWT configuration, and leaves `backend/.env` for normal development. From `backend/`, run `.\.venv\Scripts\python.exe .env.google-smoke/launch.py` when the isolated API is stopped. The local launcher validates the disposable target and empty provider adapter registry, then binds one API process to `127.0.0.1:8000` with access logging disabled. Check `GET /` for HTTP 200 and the callback without parameters for HTTP 400 with `Missing OAuth state`. Any proxy or request tracing used with OAuth must also omit callback query strings and credential headers. From `backend/`, run one service at a time.

```powershell
.\.venv\Scripts\python.exe scripts/google_read_smoke.py gmail
.\.venv\Scripts\python.exe scripts/google_read_smoke.py calendar
.\.venv\Scripts\python.exe scripts/google_read_smoke.py drive
```

The runner asks for approval before opening Google consent. It accepts the local AURA bearer token through hidden input. In the browser, select the dedicated Google account and confirm the requested scopes. The runner requests a second confirmation before reading and reports only the outcome. It checks a single page and one continuation if supplied, or a one-day Calendar free/busy window. Use a fresh disconnected AURA test account for each service, or disconnect locally between runs. Provider-side revocation requires separate approval. The runner does not send email, create Calendar events, modify Drive files or request revocation.

## Staging deployment

1. Provision managed PostgreSQL with TLS, backups and a dedicated API role. Use a separate migration role where available.
2. On Render set root to `backend`, build to `pip install -r requirements.txt`, and start to `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Run `alembic upgrade head` once as a release step. Configure the production environment, database URL, strong JWT secret, frontend URL, exact CORS origins and SMTP. Generate a key using `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` before enabling Google. Keep one API worker while OAuth state and limits are process-local. [Render FastAPI deployment](https://render.com/docs/deploy-fastapi)
3. On Vercel set root to `frontend`, use the Next.js preset, install with `npm ci`, and build with `npm run build`. Set `AURA_API_SERVER_URL` to the HTTPS backend origin. [Next.js on Vercel](https://vercel.com/docs/frameworks/full-stack/nextjs)
4. Verify signup, preview, approval, grant exhaustion, verification, undo and backup restore in staging. Use separately authorized test accounts for live provider verification.
