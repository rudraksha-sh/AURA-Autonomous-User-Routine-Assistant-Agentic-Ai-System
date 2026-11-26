# AURA release readiness

Status: **BLOCKED for production.** No live providers or production databases were accessed.

Task 26.1 production deployment readiness is **PARTIAL**. The local production stack passed image builds, non-root and resource checks, private networking, TLS/HSTS, migrations, a logical restore, and API and worker outage recovery. PostgreSQL 17.12 restored revision e781ac36d940, pgvector 0.8.7, vector(384) and the synthetic canary. Cloud ingress, alerts, managed restore objectives, hosted replica capacity and accessibility coverage remain launch gates. The recommended architecture is one Render region with public Next.js, private FastAPI, a worker and managed PostgreSQL. [Deployment runbook](DEPLOYMENT.md)

Task 25 local security audit **passed**. The known dependency findings were remediated and both rescans reported zero known vulnerabilities. Full disposable PostgreSQL passed 208 tests and SQLite passed 205 with three PostgreSQL-only skips. Four browser journeys passed. Production ingress, hosted shared-state and throttling behavior, TLS/HSTS and operational secret verification remain release gates. [Security audit](SECURITY_AUDIT.md) and [test report](TEST_REPORT.md#task-25-security-audit-and-hardening).

Task 24 frontend E2E **passed**. Four Chromium journeys exercised authentication, tenant protection, goal and workflow planning, scheduling, bounded autonomy, and mocked Google connect and disconnect on isolated FastAPI and SQLite. The integration UI explains project-wide revocation, and the covered layouts, keyboard checks and automated integration-panel accessibility scans passed. ESLint, TypeScript and the production build passed. [Test report](TEST_REPORT.md#task-24-frontend-e2e-ux-and-accessibility)

Task 23.4 live Google token revocation **passed**. One authorized Gmail revoke invalidated the dedicated account's Gmail, Calendar and Drive access and refresh tokens under this project. The first provider probe returned HTTP 401 for each access token and HTTP 400 `invalid_grant` for each refresh token. All local grants were removed and disconnected reads returned HTTP 403. Pagination boundary tests passed and side-effect counts remained zero. [Test report](TEST_REPORT.md#task-234-live-google-token-revocation)

Task 23.3 live read-only validation **passed** on the dedicated Google account. Gmail and Drive listing and pagination, Calendar free/busy, exact OAuth scopes, encrypted persistence and Gmail refresh were verified. Drive passed after the continuation limit was corrected. Final counts were zero for tasks, autonomy grants and external actions. Provider writes remain disabled. Task 23.4 subsequently verified revocation and post-revocation denial under separate approval. [Test report](TEST_REPORT.md#task-233-live-google-read-only-validation)

Task 23.2 local preflight **passed**. The isolated API is configured for the disposable PostgreSQL target, and offline encryption, health, callback and runner checks passed. The operator reported dedicated-account setup complete. Task 23.3 has explicit approval for live sign-in, reads and refresh. Revocation requires separate approval. [Test report](TEST_REPORT.md#task-231-live-google-read-only-validation)

Task 23 is **PARTIAL**. Mocked Google integration and affected workflow regression passed 73 tests with three PostgreSQL-only skips. Service-specific read scopes, encrypted credentials, account ownership, pagination, failure handling and approval boundaries passed. The dedicated-account smoke runner requires explicit approval before any live verification. Provider writes remain disabled. [Test report](TEST_REPORT.md) and [smoke test setup](SETUP.md#google-read-only-smoke-test)

Tasks 22.1 and 22.2 passed on the recovered disposable PostgreSQL endpoint at `127.0.0.1:15432`. The full backend regression passed 177 tests, including all three PostgreSQL-only concurrency cases. The before and after public schema dumps and fixture schema inventories matched. Alembic current and head matched, and the migration drift check passed. The original test container and volume were preserved for rollback. Task 22 also recorded 174 SQLite passes and three PostgreSQL-only skips and completed the local worker outage and recovery drill. Provider writes remain disabled. [Test report](TEST_REPORT.md) · [Worker monitoring](WORKER_MONITORING.md)

Task 21 adds private worker probes, aggregate backlog and retry metrics, structured warnings and tested lookup-only recovery. Production still needs a supervisor, private probe and log collection, alert routing and operational thresholds validated against workload. Provider writes remain disabled pending provider-specific verification and callback authentication. See [worker monitoring](WORKER_MONITORING.md) and [test evidence](TEST_REPORT.md).

Task 20 added a supervised polling entrypoint, graceful SIGINT/SIGTERM shutdown, structured status logs and stale-lease recovery to an uncertain state requiring lookup. Worker/outbox SQLite checks passed 9 tests (1 PostgreSQL-only skip), PostgreSQL outbox/security passed 9, and full SQLite passed 171 (3 PostgreSQL-only skips). Production still requires provider-specific callback/reconciliation, worker service monitoring and alerting, and other previously listed release gates. See [test report](TEST_REPORT.md).

Task 19.22 closed the SQLite regression failures: focused checkpoint and AI persistence tests passed, and the full SQLite suite passed 169 tests with 3 PostgreSQL-only skips. PostgreSQL concurrency/reliability passed 16 tests, RAG passed 7, and Alembic check passed. The fixture fix preserves SQLite behavior and recognizes the actual pgvector(384) type. Existing external-provider, operations, security, accessibility and retention gates remain. See [test report](TEST_REPORT.md).

Task 19.18 restored the verified-empty disposable PostgreSQL public application schema by executing the full Alembic chain from base to `e781ac36d940`. The schema now contains all 19 application tables, constraints/indexes and a `vector(384)` column. Current/head match. `alembic check` still reports two preserved legacy sentinel tables and cannot decode the pgvector type. The RAG run had six passing tests and a Windows basetemp teardown error, although a read-only post-run inspection confirmed public tables survived. SQLite regression remains pending. See [test report](TEST_REPORT.md).

Task 19.17 isolated PostgreSQL validation passed 27 tests across RAG retrieval, checkpoint reliability, approval recovery and outbox execution. Public schema inventory matched before and after. Two older fixture sentinel tables and their schemas were already present at baseline. Alembic remains at `e781ac36d940`; schema rebuild and `alembic check` remain pending. See [test report](TEST_REPORT.md).

Task 18.5 PostgreSQL validation passed the RAG API suite (6), checkpoint/recovery (7), concurrent approval (1), outbox/tenant isolation (8), and offline embedding integration (1) against PostgreSQL 17.12 with pgvector 0.8.7. Alembic current and head match at `e781ac36d940`, while `alembic check` fails with metadata-wide missing-table drift. See the [test report](TEST_REPORT.md). PostgreSQL schema consistency remains a release blocker.

Task 18 PostgreSQL plus pgvector validation is **BLOCKED**. PostgreSQL 17.4 client tooling is present, but the configured paths have no pgvector files, server, or initdb. Docker's Linux engine is inaccessible with a named-pipe permission error. No database tests ran. See the [test report](TEST_REPORT.md) for exact paths and error. Recommended next step is to make Docker Desktop's Linux engine available and run the tests against an isolated pgvector container.

Task 17.3 local verification on November 23, 2026 passed the fresh-process checkpoint (1 passed), full SQLite regression (169 passed, 3 PostgreSQL-only skips), frontend ESLint and TypeScript, the production build, mocked provider contracts (47 passed, 1 PostgreSQL-only skip), and `git diff --check`. The checkpoint and build passed after Windows sandbox workarounds. See the commands, errors, and retries in the [test report](TEST_REPORT.md).

## Gates

| Gate | Status | Evidence or requirement |
| --- | --- | --- |
| SQLite regression | PASS | Task 22 full suite yielded 174 passes and 3 PostgreSQL-only skips. |
| Frontend | PASS | Task 24 ESLint, TypeScript, production build and four browser E2E journeys passed. |
| Workflow security and recovery | PARTIAL | Mocked tenant, consent, expiry, stale scope, idempotency, stop during dispatch, retry, uncertain response, duplicate reconciliation and rollback tests pass. Complete deployment-like multi-process race and callback-authentication tests. |
| PostgreSQL migrations | PASS locally | Current and head match `e781ac36d940`. Alembic found no pending upgrade operations. Before and after public schema dumps match. |
| pgvector RAG | PASS locally | PostgreSQL 17.12 with pgvector 0.8.7 passed the full regression. The catalog reports `public.context_chunks.embedding` as `vector(384)`. |
| External writes | BLOCKED | The application adapter registry is empty. Each provider requires reviewed scope, idempotency, authenticated and deduplicated callbacks, timeout recovery and tested compensation before enablement. |
| Worker operations | PARTIAL | Local production containers passed PostgreSQL outage and recovery, private probes and SIGTERM. Verify the hosted watchdog and alert delivery before release. |
| Google reads | PARTIAL | Dedicated-account live consent, exact scopes, Gmail, Calendar, Drive, refresh and encrypted persistence passed. Project-wide revocation and denial after revocation passed on the dedicated account. Live quota behavior remains open. |
| Security operations | PARTIAL | Local Task 25 controls and scans passed. Verify deployment ingress limits, proxy trust, hosted shared-state capacity and throttling, TLS/HSTS and key rotation. |
| Accessibility | PARTIAL | Task 24 keyboard and focus checks, three responsive widths and scoped automated WCAG checks passed in Chromium. Complete manual assistive-technology and other-browser verification. |
| Privacy and retention | PARTIAL | Memory expiry and deletion behavior exist. Schedule retention cleanup and confirm export/deletion coverage. |

## Exact pre-release sequence

1. Provision disposable production-version PostgreSQL with pgvector.
2. Apply Alembic to an empty database. Run PostgreSQL workflow, RAG and independent-connection race suites.
3. Run CI checks for dependencies, secrets, CORS/CSRF, authentication, authorization and rate limits. Verify token encryption and key rotation.
4. Complete keyboard and screen-reader checks at mobile and desktop widths.
5. Supervise the outbox worker. Test crash recovery, lease expiry, duplicate callbacks, dead letters and compensation.
6. Review each provider's authorization and idempotency contract. Use a dedicated test account for consent, revoke, quota, timeout and reconciliation. Keep adapters disabled until these checks pass.
7. Verify retention, export, account deletion, monitoring, backup and recovery against the release environment.
8. Record release-specific test results before deployment authorization.
## Task 26.2 staging readiness

**PARTIAL.** Production images, PostgreSQL-backed rate limiting, durable single-use OAuth state and the local HTTPS Next.js-to-FastAPI callback path were validated. The prepared Render Blueprint targets an estimated $27/month minimum compute for a low-traffic rehearsal. The $58/month architecture retains more database and API capacity. Before opening hosted staging, verify edge client-IP provenance, TLS/HSTS, managed database recovery and capacity, and the delivery and acknowledgement of staging alerts. Shared profile storage, Firefox/Safari and manual assistive-technology coverage remain open. [Deployment runbook](DEPLOYMENT.md#task-262-render-staging-runbook)
## Task 26.3B.2 database provisioning

The Render Blueprint now wires API/worker to the managed PostgreSQL service, with the API URL set to an explicitly provisioned runtime role and worker sharing that runtime URL. TLS is required by SQLAlchemy and Alembic settings. A separate bootstrap utility enables pgvector and creates non-superuser runtime and migrator roles with default runtime DML grants. Migrations remain a private one-time action using the migrator URL. A fresh disposable PostgreSQL initialization reached Alembic head `f6b14d802c31`; runtime URL verification passed, vector 0.8.7 was present, and the runtime role lacked schema creation and superuser privileges. Hosted private networking, server certificate validation behavior, Render secret setup, and managed-database migration execution remain unverified.
## Task 26.3B.2e database security evidence

The focused PostgreSQL/configuration selection passed 41 tests with zero failures or skips. This run used the disposable `aura_test` role and `aura_workflow_test` database at 127.0.0.1:15432 with pgvector 0.8.7. Separate bootstrap database checks confirmed runtime CRUD, sequence usage and goal persistence. Runtime is not superuser and lacks CREATEDB and CREATEROLE; table DDL and role creation were denied. Production configuration requires `verify-full` and a CA path. Hosted CA file provisioning and managed endpoint SAN compatibility remain deployment gates.
## Task 26.3B.3 release hygiene

Current status remains **PARTIAL**. The worktree contains 85 modified tracked paths and 4,514 untracked candidate paths before generated artifacts are excluded. A path-only heuristic scan found two candidate matches in local cache and credential implementation files, plus nine generic historical matches. These are not confirmed secret disclosures, and a focused sanitized review is required before creating release commits. Disposable directories are now ignored. Confirm every manifest path and review changed behavior before staging.


## Task 26.3B.3a release integrity

**PARTIAL.** All 11 prior heuristic matches were reviewed and classified as false-positive source/vendor/cache patterns; no confirmed credential or required rotation was identified. The deleted root `test.py` is unrelated and excluded from proposed release groups pending owner approval. The regenerated `RELEASE_MANIFEST.md` lists all release candidates except that deletion. Current worktree remains unstaged; no history changes were made. Verify the manifest against the final worktree immediately before staging because subsequent edits change the snapshot.


Manifest snapshot: 147 changed worktree paths (80 modified, 6 deleted, 61 untracked); 146 proposed release candidates in `RELEASE_MANIFEST.md` and one excluded deletion (`test.py`). Verification compared manifest entries to current status: 146 expected, 146 listed, no missing or extra paths. Non-overlapping proposed commit groups are the five manifest sections: Backend, agents and migrations (96 paths); Frontend and E2E tests (29); Security and infrastructure (8); Deployment configuration (1); Documentation (12). Treat the manifest itself as part of Documentation. No paths are staged.


## Task 26.3B.4 final reconciliation

**PARTIAL ? local functional gates passed; staging capacity/readiness gates remain.**

- Backend: PostgreSQL 217 passed, 0 failures/skips; SQLite 212 passed, 0 failures, 5 PostgreSQL-only skips.
- Frontend: ESLint passed; TypeScript passed; production build passed in the Playwright webServer; Playwright 4/4 passed.
- Schema: disposable Alembic current/head `f6b14d802c31`; no new operations; pgvector `0.8.7`. Runtime role `aura_runtime` passed API registration, verification, login, goal, plan, approval/execution and listing against disposable `aura_fresh`.
- Blueprint: YAML parse and runtime wiring assertions passed; previous published JSON Schema validation evidence remains valid for the unchanged Blueprint.
- Load: historical 41,024 requests / zero errors, 20 users and 600 seconds sustained; final sampled 10-user load 1,408 requests / zero errors.
- Profiling: idle 31 samples / 60 s at exactly 2 s; successful load 16 samples / 30 s at exactly 2 s. cgroup memory high-water frontend/API/worker/DB 118.5/273.6/73.8/202.8 MiB; OOM deltas zero. PostgreSQL has 20.8% memory headroom and 90.8% throttled periods at its 0.1 CPU allocation, below release resource targets. The $27/month plan is not capacity-approved; increase PostgreSQL RAM to at least 271 MiB and CPU, then reprofile.
- Cold start: API application startup completion was 4.356 s from container start, but first cold `/readyz` success was not retained. Do not claim cold readiness passed.
- External actions stayed disabled or mocked; no live Google calls, provider writes, or email delivery occurred.

Remaining blockers: PostgreSQL memory/CPU headroom, measured first cold readiness, and hosted evidence for TLS/HSTS, trusted edge identity, alert delivery, restore, secret rotation and private networking. No deployment, provisioning, staging, or Git changes were performed.


## Task 26.3B.4a capacity closure

**PARTIAL ? database tier validated locally; sustained end-to-end approval is provisional.** The local Blueprint now targets Render Postgres `0.5c-1g` based on measured capacity. Current official price is $19/month for 0.5 CPU / 1 GB / 100 connections; with the existing three $7 service plans and minimum 1 GB storage, estimated service compute plus storage is $40.30/month, excluding workspace fees and additional storage.

The 60-second idle and 10/20-user phases used reliable approximately two-second samples and had zero errors/OOMs. The valid 600-second phase sampled 299 times across 600.04 seconds, with maximum interval 2.06 seconds, zero OOMs, DB high-water 210.3 MiB, 0.45% DB CPU-throttled periods, 14 max DB connections, and p95 DB transaction RTT 2.70 ms. It had one planning transport error among 38,804 requests. The subsequent retry was invalid after a 5,832-second sampling gap and expired JWTs; the final retry was interrupted per owner instruction. All raw evidence is retained and no benchmark is active.

API first external readiness across three starts: 5.229 s, 3.800 s, 3.782 s. Defer clean sustained zero-error approval and further capacity tuning to hosted staging. No staging was provisioned.
