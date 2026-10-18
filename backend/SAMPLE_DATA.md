# Isolated sample data

The sample-data seeder uses authenticated AURA HTTP routes and only permits a
SQLite file beneath `backend/sample_data` whose filename includes `test`. It
does not connect to the normal configured PostgreSQL database, delete records,
or overwrite an existing account. Matching sample goals and tasks are skipped,
so repeat runs add only missing records.

From PowerShell, in `backend`:

```powershell
$env:DATABASE_URL = "sqlite:///sample_data/aura_ui_test.db"
$env:AURA_SEED_DATABASE_URL = $env:DATABASE_URL
$env:AURA_SEED_USER_PASSWORD = Read-Host "Choose a local-only sample account password"
.\.venv\Scripts\python.exe scripts\seed_sample_data.py
.\.venv\Scripts\uvicorn.exe app.main:app --reload
```

Keep that PowerShell session's `DATABASE_URL` set while the backend runs. In a
second PowerShell window, run `cd frontend`, set
`$env:NEXT_PUBLIC_API_URL = "http://localhost:8000"`, and run `npm.cmd run dev`.

The profile uses `aura.sample@example.com`; keep the supplied password local
and do not reuse a real password. The database file is ignored by Git. Its
tables are created with the existing SQLAlchemy metadata without dropping or
resetting anything. The script prints created counts and verifies authenticated
goal/task API reads.

The backend API integration workflow can be tested without PostgreSQL or any
external AI credentials from `backend`:

```powershell
.\.venv\Scripts\python.exe -m pytest unit_tests -q
```

This isolated suite creates temporary SQLite files under pytest's temp folder.
Do not run `backend/tests` against a database containing user data: its shared
fixture truncates tables in the configured `aura_test_db`.

## Existing capabilities checked

- Goals/tasks: authenticated CRUD routes at `/api/goals` and `/api/tasks`.
- Deterministic goal planner: `/api/planner/goals/{goal_id}/plan` and `/save`.
- Daily planner: `/api/planner/schedules/preview`, `/what-if`, `/schedules`,
  and `/schedules/day/{date}`.
- AI plan endpoint: `/api/ai/plan` uses OpenRouter when configured and otherwise
  produces a clearly labeled deterministic template plan. Authenticated
  `/api/ai/status` reports configuration without revealing secrets. This
  workflow never makes an external provider request.
- Voice UI: browser speech recognition/synthesis plus fixed-pattern commands
  call `/api/assistant/tools`; automated tests exercise the authenticated API
  tool registry, but browser speech providers require a browser to test.
- The dashboard reads authenticated goals and tasks and derives its summaries
  client-side; no standalone dashboard statistics endpoint exists.
- SQLite migration verification is currently blocked by the existing
  `f5ac130ca6de` migration: it adds a unique constraint with `ALTER TABLE`,
  which SQLite does not support. PostgreSQL is the configured migration
  target; avoid rewriting this existing revision solely to satisfy SQLite.
