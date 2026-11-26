# Release manifest

Snapshot of `git status --porcelain --untracked-files=all`: 147 changed paths total; 146 proposed release paths; one excluded unrelated deletion. Nothing is staged. Point-in-time inventory.

## Backend, agents and migrations

- `backend/.env.example` - modified
- `backend/alembic/env.py` - modified
- `backend/app/agents/context/agent.py` - modified
- `backend/app/agents/context/schemas.py` - modified
- `backend/app/agents/execution/agent.py` - modified
- `backend/app/agents/intelligence/agent.py` - modified
- `backend/app/agents/intelligence/schemas.py` - modified
- `backend/app/agents/memory/agent.py` - modified
- `backend/app/agents/planner/agent.py` - modified
- `backend/app/agents/replanning/agent.py` - modified
- `backend/app/agents/replanning/schemas.py` - modified
- `backend/app/agents/scheduler/agent.py` - modified
- `backend/app/agents/verification/agent.py` - modified
- `backend/app/agents/verification/schemas.py` - modified
- `backend/app/api/routes/auth.py` - modified
- `backend/app/api/routes/autonomy.py` - modified
- `backend/app/api/routes/daily_planner.py` - modified
- `backend/app/api/routes/integrations.py` - modified
- `backend/app/api/routes/planner.py` - modified
- `backend/app/api/routes/profile.py` - modified
- `backend/app/api/routes/workflows.py` - modified
- `backend/app/core/config.py` - modified
- `backend/app/core/exceptions.py` - modified
- `backend/app/core/logging.py` - modified
- `backend/app/core/rate_limit.py` - modified
- `backend/app/core/rate_limit_dependencies.py` - modified
- `backend/app/core/security.py` - modified
- `backend/app/core/security_headers.py` - modified
- `backend/app/db/session.py` - modified
- `backend/app/integrations/google/client.py` - modified
- `backend/app/integrations/google/credentials.py` - modified
- `backend/app/integrations/google/oauth.py` - modified
- `backend/app/main.py` - modified
- `backend/app/models/__init__.py` - modified
- `backend/app/schemas/daily_planner.py` - modified
- `backend/app/schemas/workflow.py` - modified
- `backend/app/services/account_service.py` - modified
- `backend/app/services/calendar_service.py` - modified
- `backend/app/services/daily_planner_service.py` - modified
- `backend/app/services/planner_service.py` - modified
- `backend/app/services/what_if_service.py` - modified
- `backend/app/tools/database.py` - modified
- `backend/app/workflows/nodes.py` - modified
- `backend/app/workflows/registry.py` - modified
- `backend/app/workflows/state.py` - modified
- `backend/conftest.py` - modified
- `backend/requirements-dev.txt` - modified
- `backend/requirements.txt` - modified
- `backend/scripts/seed_sample_data.py` - modified
- `backend/tests/agents/test_scheduler_capacity.py` - modified
- `backend/tests/conftest.py` - modified
- `backend/tests/test_ai.py` - modified
- `backend/tests/test_cors.py` - modified
- `backend/tests/test_google_client.py` - modified
- `backend/tests/test_google_credentials.py` - modified
- `backend/tests/test_google_oauth.py` - modified
- `backend/tests/workflows/test_autonomy_recovery.py` - modified
- `backend/unit_tests/test_calendar_events_api.py` - modified
- `backend/unit_tests/test_production_jwt_config.py` - modified
- `backend/.dockerignore` - added
- `backend/Dockerfile` - added
- `backend/alembic/versions/53c42be41d70_add_context_index.py` - added
- `backend/alembic/versions/67d102ab49c5_add_planning_memory.py` - added
- `backend/alembic/versions/e781ac36d940_add_external_action_outbox.py` - added
- `backend/alembic/versions/f6b14d802c31_add_shared_security_state.py` - added
- `backend/app/agents/context/embeddings.py` - added
- `backend/app/agents/context/retrieval.py` - added
- `backend/app/agents/execution/adapters.py` - added
- `backend/app/agents/execution/outbox.py` - added
- `backend/app/agents/execution/worker.py` - added
- `backend/app/api/routes/context.py` - added
- `backend/app/api/routes/external_actions.py` - added
- `backend/app/api/routes/memory.py` - added
- `backend/app/core/ingress.py` - added
- `backend/app/core/request_size.py` - added
- `backend/app/core/shared_security.py` - added
- `backend/app/integrations/google/reads.py` - added
- `backend/app/models/context.py` - added
- `backend/app/models/external_action.py` - added
- `backend/app/models/memory.py` - added
- `backend/app/models/security_state.py` - added
- `backend/ops/bootstrap_database.py` - added
- `backend/ops/migrate.py` - added
- `backend/ops/worker.supervisord.conf` - added
- `backend/requirements.production.lock` - added
- `backend/scripts/google_read_smoke.py` - added
- `backend/tests/agents/test_worker_supervision.py` - added
- `backend/tests/test_google_reads.py` - added
- `backend/tests/test_health.py` - added
- `backend/tests/test_shared_security.py` - added
- `backend/tests/workflows/test_context_checkpoints.py` - added
- `backend/tests/workflows/test_context_retrieval.py` - added
- `backend/tests/workflows/test_reliability.py` - added
- `backend/tests/workflows/test_secure_execution.py` - added
- `backend/tests/workflows/test_sprint.py` - added
- `backend/unit_tests/test_security_boundaries.py` - added

## Frontend and E2E tests

- `frontend/.gitignore` - modified
- `frontend/app/(private)/planner/workflows/page.tsx` - modified
- `frontend/app/(private)/settings/page.tsx` - modified
- `frontend/components/auth/AuthGate.tsx` - modified
- `frontend/components/workflows/AutonomyControls.tsx` - modified
- `frontend/eslint.config.mjs` - modified
- `frontend/next.config.ts` - modified
- `frontend/package-lock.json` - modified
- `frontend/package.json` - modified
- `frontend/public/file.svg` - deleted
- `frontend/public/globe.svg` - deleted
- `frontend/public/next.svg` - deleted
- `frontend/public/vercel.svg` - deleted
- `frontend/public/window.svg` - deleted
- `frontend/services/auth.ts` - modified
- `frontend/services/goals.ts` - modified
- `frontend/services/integrations.ts` - modified
- `frontend/services/planner.ts` - modified
- `frontend/tsconfig.json` - modified
- `frontend/types/planner.ts` - modified
- `frontend/types/workflow.ts` - modified
- `frontend/.dockerignore` - added
- `frontend/Dockerfile` - added
- `frontend/components/workflows/ExternalActions.tsx` - added
- `frontend/components/workflows/PlanningMemory.tsx` - added
- `frontend/e2e/backend.py` - added
- `frontend/e2e/journeys.spec.ts` - added
- `frontend/playwright.config.ts` - added
- `frontend/proxy.ts` - added

## Security and infrastructure

- `.gitignore` - modified
- `compose.production.yml` - added
- `deploy/.dockerignore` - added
- `deploy/Caddyfile` - added
- `deploy/Dockerfile.caddy` - added
- `deploy/postgres-init.sql` - added
- `deploy/production.env.example` - added
- `deploy/staging-monitoring.yml` - added

## Deployment configuration

- `render.yaml` - added

## Documentation

- `docs/ARCHITECTURE.md` - modified
- `docs/CLEANUP_REPORT.md` - modified
- `docs/SETUP.md` - modified
- `docs/TEST_REPORT.md` - modified
- `docs/AGENT_AUDIT.md` - added
- `docs/AGENT_BACKLOG.md` - added
- `docs/CLEANUP_AUDIT.md` - added
- `docs/DEPLOYMENT.md` - added
- `docs/RELEASE_MANIFEST.md` - added
- `docs/RELEASE_READINESS.md` - added
- `docs/SECURITY_AUDIT.md` - added
- `docs/WORKER_MONITORING.md` - added

## Excluded from proposed release

- `test.py` - deleted clone-check file; no references found; deletion remains pending owner decision.

## Task 26.3D.2b corrective release manifest

Candidate paths for a follow-up commit against `fe9ee1484f56d209c9ebaaee4cb47e066bb77e79`. The original 146-path snapshot remains historical.

- `backend/alembic/env.py` - modified
- `backend/ops/bootstrap_database.py` - modified
- `backend/ops/migrate.py` - modified
- `backend/unit_tests/test_bootstrap_database.py` - added
- `backend/unit_tests/test_migration_database_url.py` - added
- `docs/RELEASE_MANIFEST.md` - modified
- `docs/RELEASE_READINESS.md` - modified
- `docs/TEST_REPORT.md` - modified

Owner-run verification on disposable PostgreSQL 17.12 with pgvector and a non-superuser `CREATEROLE` admin reported **2 passed, 0 failed, 0 skipped in 0.39s** and a passing `git diff --check`. `render.yaml` and the unrelated root `test.py` deletion are outside this corrective manifest. [Test evidence](TEST_REPORT.md#task-263d2b-compatibility-validation)
