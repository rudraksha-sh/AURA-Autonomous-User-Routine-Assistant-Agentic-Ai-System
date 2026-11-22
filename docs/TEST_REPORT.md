# Test report

Executed on November 22, 2026, with Python 3.13, Node.js 24, Next.js 16.3.1, PostgreSQL 18 and the pinned LangGraph dependencies.

| Check | Result |
| --- | --- |
| `python -m pytest unit_tests tests -q --tb=short` with SQLite | 139 passed, 2 skipped. Both skips require independent PostgreSQL connections. |
| `python -m pytest tests -q --tb=short` with `AURA_TEST_POSTGRES_URL` targeting a disposable instance | 96 passed, including approval races and concurrent consumption of a single-use grant. |
| `alembic heads` and PostgreSQL offline SQL generation | One head, `b84c52e91a30`. SQL emitted both new tables. |
| PostgreSQL `alembic upgrade head` and `alembic check` | Passed on fresh and prior-head databases. A synthetic user and goal created at the prior revision survived the upgrade. No pending schema operations. |
| Frontend lint, TypeScript and production build | Passed. Next.js included `/planner/workflows`. |
| Local Chrome smoke test | Passed desktop preview, pause, resume, approval and verification. Passed mobile at 390 px in dark and light themes, with no horizontal overflow. Passed mobile consent, grant execution and budget exhaustion. |
| `git diff --check` | Passed. |

Workflow tests cover invalid intent, tenant isolation, stale approvals, pause, resume and cancellation, checkpoint restoration across requests, interrupted approval, duplicate requests, optimistic revisions, SQL rollback after injected verification failure, grant expiry, pause and emergency stop, simulation, replanning, preference controls, guarded undo and token encryption. Existing suites cover auth, tasks, AI fallback, daily planning and Google adapters.

The PostgreSQL suite used a random schema per run. The browser used synthetic accounts and localhost services. Provider calls were mocked or disabled. There was no live OAuth, OpenRouter, SMTP or production database access. Full keyboard and screen-reader testing, external execution and deployment were outside the checks. The Python test environment reused installed base dependencies and added the pinned graph packages locally.
