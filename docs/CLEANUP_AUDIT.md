# Task 01 cleanup audit

Baseline: `refactor/aura-clean-architecture` at `08eb9b9`, with a clean working tree and 274 tracked paths. Reviewed the tracked inventory, untracked and ignored paths, Git history for the starter files, production and test references, and the backend and frontend dependency manifests. The ignored inventory used Git's directory listing so inaccessible test-cache contents did not need to be opened.

## Repository structure

```text
backend/
  app/
    agents/
      context/ execution/ intelligence/ memory/ planner/
      replanning/ scheduler/ simulation/ supervisor/ verification/
    workflows/       Graph, node adapters, state, registry and checkpoint journal
    integrations/    Shared Google adapters and credentials
    tools/           Shared local task writes and recovery
    api/routes/      HTTP contract and entry points
    services/       Shared domain logic
    models/ schemas/ db/ core/
  alembic/versions/  All 15 migrations
  scripts/           Three documented maintenance and development entry points
  tests/ unit_tests/
frontend/
  app/ components/ lib/ services/ types/
docs/
```

No restructuring is needed. Each of the ten agent packages already has an implementation and a schema module. The Scheduler calls Memory and the scheduling workflow node calls Intelligence for its capacity result. Shared Google code lives under `app/integrations/google`, and Execution and the workflow registry call shared write and recovery tools under `app/tools`. The voice assistant registry exposes its own interactive commands. Existing architecture and catalog descriptions remain accurate.

The final diff review covered each source edit. The Python edits only remove unused names, while the ESLint edit excludes generated cache directories. A repository-wide filename search found no required references to the six deleted paths. The new cleanup documents record those names for traceability.

## Candidate decisions

| Candidate | Classification | Evidence and decision |
| --- | --- | --- |
| `test.py` | SAFE TO REMOVE | Initial clone-check commit added a script that only printed `clone working`. No tracked caller. The backend suite collects from `backend/tests` and `backend/unit_tests`. |
| Five SVG files in `frontend/public/` | SAFE TO REMOVE | Added with the frontend scaffold. No tracked references to their filenames in application code, configuration, tests or docs. The App Router favicon is independent. |
| Unused imports in planner and profile routes, daily planner schemas, planner and what-if services, and the sample seed script | SAFE TO REMOVE | Pyflakes flagged the imports and the unused seed-script `user_id` local. Source review found no reads. The seed script already imports the app before building metadata. |
| SQLAlchemy imports in `app/main.py` and `app/models/__init__.py` | KEEP | App startup, metadata creation, Alembic and model imports rely on registration and package exports. These explain the remaining Pyflakes findings. |
| Three scripts in `backend/scripts/` | KEEP | `SAMPLE_DATA.md` documents `seed_sample_data.py`, and a unit test imports its SQLite path guard. `PROFILE_SETTINGS.md` documents the guarded SQLite profile updater and role-management command. |
| Legacy planner API, deterministic planner service and provider adapter | KEEP | All have active callers. The legacy preview maps provider offsets into its response while the graph path calls the rule planner with its own deadline handling. Consolidation requires a behavior decision. |
| Agent schemas that re-export public types | KEEP | Planner, Memory, Scheduler and Simulation reuse existing contracts through imports. These modules contain no duplicate schema definitions. |
| LangChain, LangGraph and LangSmith pins | KEEP | Planner imports `langchain_core.messages`; workflows import LangGraph graph and checkpoint APIs and use LangSmith's tracing context. Installed LangGraph metadata requires the SDK and prebuilt packages. Preserve their explicit reproducibility pins. |
| Remaining backend requirements, frontend manifest and lockfile | KEEP | Dependencies support runtime imports, framework entry points, middleware, build tooling or test commands. No package removal was verified. |
| Migrations, fixtures, local configuration, virtual environments and `frontend/node_modules/` | KEEP | Schema history, test setup and local runtime inputs. Protected paths include `backend/.env`, `.venv/` and `backend/.venv/`. Local configuration contents were outside the audit. |
| `frontend/README.md` | NEEDS REVIEW | Includes generic scaffold guidance but also documents startup. Its replacement would be a separate documentation change. |
| Ignored backup copies listed below | NEEDS REVIEW | Filenames indicate historical work. They may contain material outside Git history and their disposability is unverified. Retain pending owner review and approval. |
| Generated paths listed below | SAFE TO REMOVE with approval | Python, pytest, Next.js and TypeScript regenerate these outputs. They were retained pending explicit cleanup approval. ESLint now excludes pytest cache directories through its global ignore configuration. |

## Ignored backup paths retained

```text
README.md.bak
backend/app/agents/planner/service.py.before_ai_integration.bak
backend/app/agents/planner/service.py.before_ai_integration.bakcle
backend/app/agents/planner/service.py.before_parse_fix.bak
backend/app/api/routes/planner.py.before_ai_integration.bak
backend/app/services/goal_service.py.before_ordering_fix.bak
backend/app/services/planner_service.py.before_ai_integration.bak
backend/tests/conftest.py.bak
backend/tests/conftest.py.before_otp_fix.bak
backend/tests/conftest.py.before_rate_limit_fix.bak
backend/tests/test_ai.py.before_otp_fix.bak
backend/tests/test_auth.py.before_rate_limit_fix.bak
backend/tests/test_goals.py.before_otp_fix.bak
backend/tests/test_google_oauth.py.bak2
backend/tests/test_google_oauth.py.before_rate_limit_fix.bak
backend/tests/test_tasks.py.before_otp_fix.bak
backend/unit_tests/auth_helpers.py.bak
backend/unit_tests/auth_helpers.py.bak2
backend/unit_tests/test_sqlite_model_defaults.py.bak
```

## Generated paths retained

```text
.pytest_cache/
backend/.pytest_cache/
backend/__pycache__/
backend/alembic/__pycache__/
backend/alembic/versions/__pycache__/
backend/app/__pycache__/
backend/app/agents/__pycache__/
backend/app/agents/context/__pycache__/
backend/app/agents/execution/__pycache__/
backend/app/agents/intelligence/__pycache__/
backend/app/agents/memory/__pycache__/
backend/app/agents/planner/__pycache__/
backend/app/agents/replanning/__pycache__/
backend/app/agents/scheduler/__pycache__/
backend/app/agents/simulation/__pycache__/
backend/app/agents/supervisor/__pycache__/
backend/app/agents/verification/__pycache__/
backend/app/api/__pycache__/
backend/app/api/routes/__pycache__/
backend/app/core/__pycache__/
backend/app/db/__pycache__/
backend/app/integrations/__pycache__/
backend/app/integrations/google/__pycache__/
backend/app/models/__pycache__/
backend/app/schemas/__pycache__/
backend/app/services/__pycache__/
backend/app/tools/__pycache__/
backend/app/workflows/__pycache__/
backend/scripts/__pycache__/
backend/tests/__pycache__/
backend/tests/agents/__pycache__/
backend/tests/workflows/__pycache__/
backend/unit_tests/__pycache__/
frontend/.next/
frontend/.pytest_cache/
frontend/next-env.d.ts
frontend/tsconfig.tsbuildinfo
```

The root, backend and frontend pytest cache directories were visible by path. Windows permissions prevented directory enumeration. Existing Git ignore patterns already cover the identified artifact types.
