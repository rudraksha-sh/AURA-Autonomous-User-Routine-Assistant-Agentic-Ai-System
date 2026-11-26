# Test report

## Task 25 security audit and hardening

**PASS for the local audit.** No known critical or high finding remains in the scanned dependency sets or reviewed local paths. Deployment security checks remain open. [Security audit](SECURITY_AUDIT.md)

| Check | Result |
| --- | --- |
| Full backend regression | Disposable PostgreSQL **208 passed, 0 failed, 0 skipped in 101.70 s**. SQLite **205 passed, 0 failed, 3 PostgreSQL-only skips in 68.01 s**. Both emitted four dependency or API deprecation warnings. |
| Focused security checks | **37 passed in 5.31 s.** Includes required JWT expiry, rate-limit capacity and expiry, declared and streamed request size, production CORS, profile cache policy, and access-log redaction. |
| Frontend | **4 Playwright journeys passed in 32.7 s** against isolated FastAPI and SQLite. ESLint, TypeScript and Next.js production build passed. |
| Dependencies | npm audit and pip-audit on the separately resolved Python target reported **zero known vulnerabilities** after targeted remediation. |
| Secrets | Scanned 274 tracked paths and 5,800 unique reachable blobs across 46 commits without emitting secret values. Task 26.1 rechecked the sole OTP candidate and found two empty historical assignments. The initial result was a false positive. Production now requires a fresh independent pepper. |
| Production-shaped checks | Debug disabled, API docs returned 404, CORS allowed only the configured HTTPS origin, OAuth callbacks used no-referrer and no-store, and frontend frame and MIME policies appeared in the build. |
| Whitespace and isolation | git diff --check passed with existing line-ending warnings. The main development dotenv hash matched its baseline and main PostgreSQL remained healthy. Providers were mocked or disabled. |

## Task 24 frontend E2E, UX and accessibility

**PASS.** Four Playwright journeys passed in 30.7 s in Chrome against the production Next.js build and real FastAPI routes. The E2E server used a fresh disposable SQLite database, intercepted local email verification codes, and mocked Google consent, reads and revocation. The main development dotenv hash matched its baseline. No live Google requests or provider writes occurred.

| Check | Result |
| --- | --- |
| Authentication | Registration, code verification and keyboard focus advance, login with protected return path, logout and anonymous route denial passed. Expired sessions redirected to login and cleared the browser token. |
| Workflow | Goal creation, plan and activity timeline, pause and resume, approval and task receipt, daily schedule save, replanning and rejection, and bounded local autonomous task creation passed. A second tenant saw empty history and received 404 for the first tenant's goal and workflow. |
| Google settings | Mocked consent returned to the Integrations tab and showed the granted read-only scope. Local disconnect and project-wide revoke used distinct requests. Keyboard confirmation stated the cross-service effect. Dismissing it kept focus on Revoke, and successful removal moved focus to the Integrations heading. |
| Recovery | A stalled session check showed a loading state, timed out in ten seconds and recovered on retry. An injected 503 showed the backend's goal error and recovered to the empty state. |
| Layout and accessibility | Workflow and integration layouts had no page horizontal overflow at 1440, 820 and 390 px. The integration panel passed axe WCAG 2.0 and 2.1 A/AA checks at all three widths, including dark mode at 390 px. Settings arrow keys, accessible labels and focus transitions passed in Chromium. Manual assistive-technology and other-browser coverage remain open. |
| Browser diagnostics | No unexpected console errors, hydration errors or failed network requests in covered journeys. Expected responses were missing optional profile photos, injected timeout and 503, expired-session 401s and explicit cross-tenant 404s. |
| Build and static checks | Next.js production build, ESLint, TypeScript and git diff --check passed. |

From frontend, install dependencies with npm ci and install the Playwright browser with npx playwright install chromium. Use a Python environment with backend dependencies installed, then run npm run test:e2e. On Windows with the repo's backend virtual environment, set AURA_E2E_PYTHON_COMMAND to ..\backend\.venv\Scripts\python.exe e2e/backend.py. Set PLAYWRIGHT_CHROMIUM_CHANNEL=chrome to use installed Chrome. The harness starts frontend port 3100 and backend port 8100 on loopback and builds into .next-e2e.

## Task 23.4 live Google token revocation

**PASS.** Verified the isolated API on port 8000, disposable PostgreSQL cluster `7711079881448910886` on port 15432, and exactly three encrypted read-only grants for the same dedicated Google account. The provider-write registry was empty.

| Check | Result |
| --- | --- |
| Provider revocation | AURA's existing Gmail revoke and disconnect endpoint returned HTTP 204 after Google's revoke request succeeded. The Gmail integration disappeared immediately from local status. Calendar and Drive still appeared connected locally before cleanup. |
| Project-wide effect | The first provider probe was complete 1.6 s after polling began. The existing Gmail, Calendar and Drive access tokens each received HTTP 401 from their respective API. All three refresh tokens received HTTP 400 with `invalid_grant`. Calendar and Drive needed no separate provider revoke. [Google revocation documentation](https://developers.google.com/identity/protocols/oauth2/web-server#tokenrevoke) |
| Local invalidation | Calendar and Drive local disconnects each returned HTTP 204 after provider invalidation was confirmed. No integration rows remained for the dedicated account. All three disconnected reads returned HTTP 403 at AURA's grant check. |
| Side effects | Global counts remained zero for tasks, autonomy grants and external actions. No provider content writes or unrelated-account operations occurred. |
| Boundaries and logging | A 4096-character opaque Drive continuation round-tripped exactly. A 4097-character token returned by the provider produced HTTP 502. A 4097-character client input produced HTTP 422 before any provider call. Neither token appeared in logs. |
| Focused checks | 3 passed, 19 deselected in 0.77 s. `git diff --check` passed with existing line-ending warnings. |

## Task 23.3 live Google read-only validation

**PASS.** Live validation used the existing smoke runner and isolated API at `127.0.0.1:8000`. The disposable database on port 15432 reported cluster ID `7711079881448910886`. After the local OAuth client credentials were replaced, consent and callbacks succeeded for all three services. The three grants belonged to their initiating AURA users and had the same dedicated Google account identifier. Each grant had the exact requested identity and service scopes, and both tokens passed Fernet decryption checks without disclosure.

| Check | Result |
| --- | --- |
| Gmail | Listing and one continuation succeeded. |
| Calendar | A live one-day free/busy request succeeded. |
| Drive | The initial AURA request returned HTTP 502 because a valid 592-character continuation exceeded the 512-character limit. After raising the shared bounded input/output limit to 4096, a retry through AURA returned HTTP 200 for both pages, with 20 items each. |
| Token refresh | Forcing the disposable Gmail grant's stored expiry caused a real refresh on the next read. AURA persisted a new encrypted access token and future expiry. |
| Side effects | The provider-write registry was empty. Global counts immediately before and after the final Drive verification were zero tasks, zero autonomy grants and zero external actions. |
| Focused tests | 18 OAuth tests passed in 1.65 s after sanitized callback diagnostics were added. All 20 Google read tests passed in 2.78 s after the pagination fix. `git diff --check` passed with existing line-ending warnings. |

Google initially returned `invalid_client` at token exchange. Updating the isolated credential pair resolved it. Revocation was outside the authorization. No provider writes, token revocations, private content or credentials were recorded.

## Task 23.2 local Google integration preflight

**PASS.** Cloud-side setup and dedicated test-user registration were reported complete by the operator. Local OAuth client fields and the exact callback were checked without logging credentials. A compatible Fernet key was generated in the isolated, Git-ignored settings and passed a synthetic round trip through AURA's token storage. The main `backend/.env` matched its baseline SHA-256, and main PostgreSQL remained healthy on 5433.

- Read-only database preflight authenticated at `127.0.0.1:15432` as `aura_test` on `aura_workflow_test`. PostgreSQL 17.12 reported cluster `7711079881448910886` and internal port 5432. pgvector 0.8.7 in `public`, `vector(384)` and Alembic revision `e781ac36d940` matched.
- FastAPI bound to `127.0.0.1:8000` only. The root health probe returned 200, the configured localhost callback without state returned 400, and unauthenticated connect returned 401. The smoke runner returned 2 when approval was declined. Provider write adapter registry was empty.
- Four focused configuration tests passed in 0.11 s. `git diff --check` passed with existing line-ending warnings. The development dotenv file, smoke dotenv file and local launcher are ignored and untracked.

No live authentication, consent, provider API requests, revocation or provider writes occurred. [Local setup](SETUP.md#google-read-only-smoke-test)

## Task 23.1 live Google read-only validation

**BLOCKED before live authentication.** The local client ID and client secret are populated and the redirect URI matches the documented loopback callback. The token encryption key is missing or invalid. The current database setting points to the main development database, and no local API was listening on port 8000 at preflight. Cloud client registration, enabled APIs and dedicated test-user membership remain unconfirmed. Explicit approval for live authentication, reads and refresh was requested. Revocation requires separate approval.

No Google account authentication or Google OAuth/provider API call was attempted. No provider writes, tasks or autonomy grants were created during preflight. Consent, callback, encrypted persistence, live reads, refresh, revocation and denial after revocation remain unverified. Mocked validation was not rerun. [Cloud and local setup](SETUP.md#google-read-only-smoke-test)

## Task 23 Google read-only validation

**PARTIAL.** Mocked validation passed. Live Google authentication, reads and revocation await explicit approval for a dedicated account.

| Check | Result |
| --- | --- |
| Affected SQLite regression | **73 passed, 0 failed, 3 PostgreSQL-only skips in 12.48 s.** Included Google OAuth, clients, credentials, read adapters, integration settings, Calendar fallback, workflow approval, autonomy and secure execution. No PostgreSQL preflight or schema rerun. |
| OAuth and tenant ownership | Single-use state, expiry, denial and replay covered. A callback completed using another tenant's session still bound only to the initiating account. Unexpected writable scopes were rejected before account lookup. Encrypted credential persistence, encrypted refresh, scope escalation during refresh, account switch and old refresh-token removal passed. |
| Read adapters and provider failures | Gmail and Drive verified explicit opaque continuation, page size, and tenant isolation. Calendar free/busy accepted only structured intervals. Covered oversized and malformed responses, redirect refusal, 401/403/429/503, five-second read and refresh timeouts, local 429 with Retry-After, and failed provider revocation preserving the stored grant until confirmed. |
| Approval and autonomy | Hostile Gmail and Drive content stayed in explicit read responses. Calendar ignored the injected text. The workflow remained awaiting approval and created no tasks, autonomy grants or external actions. |
| Live smoke runner | Mocked the consent handoff, confirmation gate, loopback reads and one continuation. A real process supplied with DENY exited 2 before opening consent or making requests. Callback access-log redaction passed. Actual Google consent, quotas, provider refresh behavior and revocation remain unverified. |
| Whitespace | `git diff --check` passed. Git reported existing line-ending warnings. |

No live Google requests or provider writes were made. [Opt-in test setup](SETUP.md#google-read-only-smoke-test)

## Tasks 22.1 and 22.2 PostgreSQL port recovery and regression

**PASS.** Windows allowed a loopback bind on TCP 15432 and the port was outside all excluded ranges. TCP 55432 remained inside 55391–55490.

| Check | Result |
| --- | --- |
| Storage and rollback | The stopped original `aura-pgvector-test` kept its original volume. A read-only source mount was copied into `aura-pgvector-test-15432-data`. Recursive comparison and normalized archive SHA-256 matched before startup. After startup the original volume still hashed to `79ef70199bc3a5a404ee70121d5b437ca7b696565f3b272a2f32fd120e64e137`. |
| Replacement | `aura-pgvector-test-15432` uses the same image ID and runtime configuration values, with a separate volume and `127.0.0.1:15432 → 5432/tcp`. PostgreSQL completed crash recovery from the copy. The main container stayed healthy on 5433. |
| Identity and pgvector | The published endpoint authenticated as `aura_test` on `aura_workflow_test`. PostgreSQL 17.12 reported server port 5432 and the original system identifier `7711079881448910886`. pgvector `0.8.7` was in `public`, and the catalog reported `public.context_chunks.embedding` as `vector(384)`. |
| Full PostgreSQL regression | `python -m pytest unit_tests tests -q --tb=short -p no:cacheprovider` with a fresh basetemp returned **177 passed, 0 failed, 0 skipped in 82.60 s**. All three PostgreSQL-only concurrency cases ran. One existing Sentence Transformers deprecation warning. |
| Schema preservation | Before and after public schema-only dumps matched after removing per-invocation restrict markers. Both SHA-256 hashes were `4a836397b870b80291fd55b1f18c2a319aa23513fb8bae9bf208f259944be8aa`. Identity, extension, column type, revision and fixture schema inventories also matched. Both legacy fixture schemas and their public sentinels remained. No new fixture objects remained. |
| Alembic | `current` and `heads` returned `e781ac36d940 (head)`. `check` exited 0 with “No new upgrade operations detected.” SQLAlchemy warned that it could not reflect the vector type, which was verified separately through the PostgreSQL catalog. |

The fixture requires the disposable role, database and published endpoint and verifies server port 5432 before creating objects. Provider writes stayed disabled. [Test setup](SETUP.md)

## Task 22 initial PostgreSQL attempt and worker readiness

November 25, 2026. **PARTIAL.** Task 21 used a temporary reduced-metadata runner because PostgreSQL 18.4 lacked pgvector. The standard fixture already called `Base.metadata.create_all`. It now validates database, role, port and the prerequisite `public` pgvector extension before creating any fixture objects. The unique schema, namespace translation, public sentinel and full metadata creation remain in place.

| Check | Result |
| --- | --- |
| Disposable PostgreSQL preflight | BLOCKED. `pg_isready` returned `127.0.0.1:55432 - no response`. Docker Desktop startup failed at its `dockerInference` Unix socket, and the `dockerDesktopLinuxEngine` named pipe remained unavailable. The listener on port 5432 was left alone. |
| PostgreSQL identity, extension, vector(384), current revision and schema inventory | BLOCKED. No database connection to the documented disposable endpoint. No before/after comparison or leakage claim. |
| Full PostgreSQL regression and independent-connection concurrency cases | BLOCKED by the unavailable endpoint. No reduced-metadata run was used. |
| Full SQLite regression | PASS. `pytest unit_tests tests -q --tb=short -p no:cacheprovider` with fresh basetemp returned 174 passed, 3 PostgreSQL-only skips, 1 Sentence Transformers deprecation warning in 55.91 s. Tenant isolation, stale leases, lookup-only reconciliation and checkpoint recovery ran in SQLite. |
| Worker subprocess drill | PASS on local SQLite. Outage live/ready 200/503, recovery 200/200, exclusive lock 503/503, then recovery 200/200. SIGTERM raised inside the subprocess ran the graceful handler, logged `worker_stopped` and exited 0. A fresh PID reached 200/200. |
| Alembic | `alembic heads` reported `e781ac36d940`. `alembic check` exited 1 with `psycopg.errors.ConnectionTimeout` on port 55432 before comparing metadata. |
| Git whitespace check | PASS. `git diff --check` returned 0 with existing LF-to-CRLF warnings. |

The initial run stopped before PostgreSQL testing. Tasks 22.1 and 22.2 resumed verification on the recovered endpoint and recorded the results above.

## Task 21 worker monitoring and reconciliation

Executed November 25, 2026. Worker probes distinguish a stalled loop from a failed poll. The SQL aggregate uses the immutable preview audit timestamp for age and counts only additional claims as retries. Structured alerts and probes contain operational counts and timestamps. [Worker monitoring](WORKER_MONITORING.md)

| Check | Result |
| --- | --- |
| Focused SQLite worker supervision and outbox/security | 12 passed, 1 PostgreSQL-only skip in 3.04 s |
| Focused PostgreSQL 18.4 worker supervision and outbox/security | 13 passed in 7.66 s, including the concurrent claim test |
| Full SQLite regression | 174 passed, 3 PostgreSQL-only skips, 1 existing deprecation warning in 49.57 s |
| Git whitespace check | Passed |

The standard PostgreSQL fixture was blocked on the unrelated `context_chunks` table because the disposable PostgreSQL instance had no pgvector extension. The successful focused rerun used the same isolated schema fixture with a temporary test runner omitting only that table. Actual PostgreSQL queries and claims were exercised. Full PostgreSQL and pgvector integration were outside this rerun.

An injected failure after a mocked provider effect and before its durable receipt left a dispatch lease. The next worker poll after expiry moved the action to unknown. A different tenant could not reconcile it. A lookup without a receipt left it unknown. A matching receipt verified it, duplicate reconciliation reused the stored result, and the mock recorded only one effect. Other checks exercised liveness and readiness HTTP codes, warning thresholds, polling failure/recovery, stall detection and retry counts. No live providers, existing databases or deployments were used.

## Task 20 worker supervision

Added a polling supervisor with bounded environment configuration (`AURA_WORKER_POLL_SECONDS`, `AURA_WORKER_BATCH_SIZE`), SIGINT/SIGTERM shutdown, session-per-poll lifecycle and structured event logs. Expired dispatch leases transition to `unknown` for lookup-only reconciliation. The worker does not retry an ambiguous provider effect. Existing compare-and-swap claims, tenant ownership, consent checks, 60-second lease and three-attempt bounded retry remain in force.

| Check | Result |
| --- | --- |
| Worker supervision and outbox SQLite tests | 9 passed, 1 PostgreSQL-only skip |
| PostgreSQL outbox/security module | 9 passed |
| Full SQLite regression | 171 passed, 3 PostgreSQL-only skips, 1 existing Sentence Transformers deprecation warning, 39.01 s |
| `git diff --check` | Passed with existing LF-to-CRLF warnings |

Covered worker startup/poll/shutdown, expired lease recovery without a provider call, and concurrent dispatch admission. Real provider adapters remain disabled by default. No frontend changes.

## Task 19.22 SQLite regression follow-up

Fixed the function-scoped `test_schema` helper to return no schema for SQLite instead of executing PostgreSQL-only `current_schema()`. Restored the missing API request inside `test_ai_plan_creates_agent_run`; the earlier fixture migration had left its database assertion without creating the agent run.

| Check | Result |
| --- | --- |
| Focused SQLite checkpoint and AI persistence | 2 passed |
| Full SQLite regression, `unit_tests tests` | 169 passed, 3 PostgreSQL-only skips, 1 existing Sentence Transformers deprecation warning, 49.97 s |
| PostgreSQL concurrency/reliability follow-up | 16 passed |
| PostgreSQL RAG | 7 passed, 1 deprecation warning |
| Alembic check | Passed after narrowly excluding the two verified legacy sentinel tables and recognizing reflected `vector(384)` |
| `git diff --check` | Passed with existing LF-to-CRLF warnings |

All pytest runs used fresh workspace-local basetemp directories and disabled pytest cache. The SQLite regression log is under `.aura-test-temp/task1922full-*.log`. PostgreSQL public inventory was recorded before the current test follow-up. The PostgreSQL suites passed without application or model changes; no public inventory delta is claimed for this turn.

## Task 19.18 disposable schema repair

Target verified before repair as `aura_workflow_test`, user `aura_test`, PostgreSQL 17.12 on localhost:55432. The public schema had only `alembic_version` and two legacy fixture sentinel tables. No application tables or data were present. pgvector 0.8.7 and both legacy test schemas were preserved.

Removed only the stale `e781ac36d940` row from this disposable target's Alembic version table after confirming application tables were absent, then executed `alembic upgrade head` from base. The complete chain ran through `e781ac36d940`. Public now contains the 19 application tables plus Alembic metadata and the two legacy sentinels. External actions have one unique constraint, two foreign keys and two indexes. PostgreSQL catalog reports `context_chunks.embedding` as `vector(384)`.

`alembic current` and `heads` both report `e781ac36d940`. `alembic check` remains nonzero and reports only the two preserved sentinel tables as unexpected removals. It also warns SQLAlchemy cannot decode the pgvector type during comparison. The six successful RAG tests were followed by a pytest session cleanup `PermissionError: [WinError 5]` on the workspace basetemp. A read-only post-run check confirmed migrated public tables, vector(384), sentinels and both legacy schemas remain present. SQLite regression was not run.

## Task 19.17 PostgreSQL module isolation

Read-only baseline and post-run identity matched `aura_workflow_test` as role `aura_test` on PostgreSQL 17.12. Alembic revision remained `e781ac36d940`. Public inventory was unchanged: `alembic_version` and two pre-existing `aura_fixture_sentinel_*` tables, with their primary-key indexes. Two pre-existing `aura_test_*` schemas also remained. No new public objects or fixture schemas remained after these runs.

Each module used a fresh workspace-local basetemp and a persistent log outside basetemp with `-x --tb=long`. Completed results:

| PostgreSQL module | Result |
| --- | --- |
| RAG retrieval | 7 passed, 1 warning |
| Checkpoint reliability | 7 passed |
| Approval/autonomy recovery | 5 passed |
| Outbox secure execution | 8 passed |

Total: 27 passed, 0 failed, 0 skipped. The previous two errors were not reproduced. The run did not encounter a pytest teardown failure. Focused suites verified sentinel preservation and per-test generated schema cleanup. No migrations or SQLite tests were run.

## Task 18.5 PostgreSQL isolation rerun

Verified before tests: database `aura_workflow_test`, role `aura_test`, PostgreSQL 17.12, pgvector 0.8.7, 384-dimension cast successful, current revision `e781ac36d940`. All pytest invocations used fresh `.aura-test-temp` paths, set TMP/TEMP/TMPDIR, and disabled cache. Logs were written before process exit.

| Suite | Result |
| --- | --- |
| PostgreSQL RAG excluding offline model | 6 passed, 1 deselected |
| PostgreSQL checkpoint and recovery | 7 passed |
| PostgreSQL concurrent approval race | 1 passed |
| PostgreSQL outbox and tenant isolation | 8 passed |
| Offline Sentence Transformers and pgvector integration | 1 passed, 1 deprecation warning |
| Alembic current/head | Both `e781ac36d940` |
| Alembic consistency check | Failed, reports all metadata tables as missing |
| `git diff --check` | Passed with existing line-ending warnings |

RAG cases validated ranking, tenant isolation, source replacement, stale-source rejection, deletion/revocation, 384-dimensional embeddings and cosine scoring through real PostgreSQL/pgvector. Synthetic local embeddings were used in six API tests. The separate offline BoW model exercised actual 384-dimensional embeddings and verified cosine ranking, replacement, deletion and cross-user denial.

The previously suspected RAG test issue was pytest's Windows basetemp permissions. A focused six-test run and separate offline model test both passed. A temporary local pytest runner applied inherited Windows directory permissions only to pytest temp creation. No application defect was confirmed. `alembic check` reports metadata-wide missing-table drift despite current/head matching. This remains unresolved and requires migration/model metadata reconciliation. No SQLite rerun was needed.

## Task 18 PostgreSQL and pgvector validation

**BLOCKED before database creation or tests.** PostgreSQL tooling reports version 17.4 through `C:\Users\rudra\anaconda3\Library\bin\pg_config.exe`. Its `--sharedir` is `C:/Users/rudra/ANACON~2/Library/share`, and `--pkglibdir` is `C:/Users/rudra/ANACON~2/Library/lib`. Neither `share/extension/vector.control` nor `lib/vector.dll` exists. The configured bindir has no `postgres.exe` or `initdb.exe`. No `psql`, native server, Podman, or PostgreSQL installation under Program Files was found.

Docker CLI exists, but `docker info --format '{{.ServerVersion}}'` failed with the exact error `permission denied while trying to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine`. No cluster, role, service, or global configuration was changed. Alembic, vector dimension/cosine retrieval, PostgreSQL RAG, tenant isolation, approval race, and outbox concurrency checks did not run. PostgreSQL test configuration requires a loopback `postgresql+psycopg` database named `aura_workflow_test`; its tests create a per-run schema and require the `vector` extension.

Recommended path: install and start Docker Desktop with an accessible Linux engine, then use an isolated pgvector PostgreSQL container and disposable database. Retry Task 18 only after the engine is available. No repeated Docker attempts were made.

## Task 17.3 workspace-local validation

Executed November 23, 2026. `Get-Command python` resolved to `C:/Users/rudra/anaconda3/python.exe`. `py -0p` listed Python 3.14 and 3.11 under AppData. `Test-Path backend/.venv/Scripts/python.exe` returned true, and the tests used that executable (Python 3.13.5). The run used no AppData interpreter or AppData temp storage.

The test interpreter created, wrote, and read a temporary file under repository-local `.aura-test-temp` with `TMP`, `TEMP`, and `TMPDIR` set there. Each pytest invocation used a new `--basetemp` in that directory and disabled the pytest cache.

| Check | Actual result |
| --- | --- |
| Fresh-process SQLite checkpoint | **PASS** on retry. `tests/workflows/test_reliability.py::test_fresh_process_reloads_and_approves_checkpoint` passed in 2.19 s. |
| Full SQLite suite | **PASS.** `unit_tests tests` yielded 169 passed, 3 PostgreSQL-only skips, and one Sentence Transformers import deprecation warning in 36.65 s. |
| Frontend lint and typecheck | **PASS.** `npm.cmd run lint` and `node node_modules/typescript/bin/tsc --noEmit` exited 0. |
| Frontend production build | **PASS** on retry, including TypeScript and static page generation. |
| Mocked provider contracts | **PASS.** 47 passed and one PostgreSQL-only concurrency skip in 3.99 s. Covered Google client, credentials, OAuth and Calendar, external action adapters, AI and SMTP. |
| `git diff --check` | **PASS.** Exit 0 with LF-to-CRLF warnings. |

The combined discovery and temp probe was initially rejected with `CreateProcess ... rejected: blocked by policy`. Separate discovery and the interpreter write probe succeeded. Broad file discovery reported `Access is denied. (os error 5)` for pre-existing test directories. Scoped discovery under the source and test directories succeeded.

The first checkpoint run exited 1 with `PermissionError: [WinError 5] Access is denied` while pytest enumerated `.aura-test-temp/task173-898a7c64f59946258b447a2b864967c2`. The retry used a temporary pytest launcher that changed owner-only directory creation to the inherited Windows permissions under `.aura-test-temp` only. The SQLite and mocked suites used the same launcher.

The initial `npm.cmd run build` exited 1 with `spawn EPERM` at `Running TypeScript ...`. The retry used temporary Next.js settings `workerThreads: true`, `cpus: 1`, and `useTypeScriptCli: false`. The original config was restored byte-for-byte.

The tests used isolated SQLite and mocked or disabled providers. No existing database, live provider, commit, push, or deployment was involved.

## Tasks 15?16 release hardening

| Check | Result |
| --- | --- |
| Full SQLite regression | 169 passed, 0 failed, 3 PostgreSQL-only skips in 42.10 seconds. One Sentence Transformers import deprecation warning. |
| Frontend | ESLint, TypeScript and production build passed. |
| Outbox | Isolated PostgreSQL migration and concurrent dispatch/stop passed. SQLite API checks cover callback deduplication, bounded worker selection and execution audit state. |
| Release gates | See [release readiness](RELEASE_READINESS.md). Production remains blocked on pgvector and provider verification. |

## Secure execution sprint 10?14

| Check | Result |
| --- | --- |
| Full SQLite regression | 169 passed, 0 failed, 3 PostgreSQL-only skips in 40.57 seconds. One existing Sentence Transformers import deprecation warning. |
| Final focused run | 8 passed, 1 PostgreSQL-only skip. Covered consent and tenant isolation, stale and expired scope, pause/stop, backoff, timeouts, duplicate reconciliation, ambiguous local commits, receipt drift, scheduling signals and stale worker item retirement. |
| Isolated PostgreSQL 18.4 | Outbox migration applied on a disposable minimal schema. A real concurrent dispatch/stop check admitted one mocked provider call and retained late evidence after revocation. The full workflow suite still requires pgvector. |
| Frontend | Lint, typecheck and production build passed. Temporary sandbox worker settings were restored. |

The outbox worker is a bounded one-shot entry point at `python -m app.agents.execution.worker` from `backend/`. The runtime adapter registry is empty by default. Retries require evidence that no effect occurred. Ambiguous outcomes use lookup only. Duplicate reconciliation was tested through the authenticated API. Provider callback transport, compensation adapters and worker scheduling remain open. No live provider or existing database was used.

## Tasks 05?09 integrated sprint

| Check | Result |
| --- | --- |
| Full SQLite regression | 162 passed, 0 failed, 2 PostgreSQL-only skips in 36.16 seconds. The existing optional Sentence Transformers fixture emitted one deprecation warning. |
| Focused Google and cross-agent tests | 27 passed. Mocked Google reads covered consent, scope selection, encrypted tenant credentials, Calendar fallback and revoke. Cross-agent cases covered zoned Calendar conflicts, memory revocation, deterministic simulation, task-ID reconciliation, sibling conflicts and rollback after verification failure. |
| PostgreSQL | Offline Alembic SQL for memory revision `67d102ab49c5` generated successfully. Runtime tests require pgvector. The installed PostgreSQL tree lacks `vector.control` and `vector.dll`; Docker Desktop denied its Linux engine pipe. |
| Frontend | ESLint, `tsc --noEmit`, and Next.js production build passed. Temporary worker settings were used for the sandbox build and restored afterward. |

Integrated debugging found a regression when strict deadlines were made the default for the legacy daily booking flow. Deadline constraints now apply to graph and simulation previews, and the legacy preview and save APIs accept an explicit `respect_deadlines` option. All Google traffic in tests used mocks. Existing databases and live providers were untouched. Replanning detects drift on request. Expired memories are excluded from retrieval and purged on the owner's next memory save.

## Task 04.1 RAG validation

**PARTIAL.** SQLite regression passed with 158 passed and 2 PostgreSQL-only skips. Five checkpoint cases passed on LangGraph 1.2.24. Legacy goal-only and versioned journals resumed. Unknown versions and missing context fields now return 409 before execution, preserve the pending run and allow cancellation. Cross-version LangGraph upgrades remain unverified.

A locally saved, 384-dimensional Sentence Transformers bag-of-words fixture ran through the production encoder loader and API. It verified normalization, cosine ranking, tenant isolation, document replacement and revocation. It provides lexical vectors and leaves pretrained-model relevance open.

Online pgvector validation remains blocked. The installed PostgreSQL 18 tree lacks both `share/extension/vector.control` and `lib/vector.dll`, no local extension bundle was found, and Docker Desktop denied access to its Linux engine pipe. The Task 04 disposable migration stopped at `CREATE EXTENSION vector`. Task 04.1 used isolated SQLite and made no changes to existing databases or live providers.

## Task 04 context retrieval

| Check | Result |
| --- | --- |
| Full SQLite regression, `pytest unit_tests tests` | 152 passed, 2 PostgreSQL-only skips in 28.35 seconds. The 6 new cases exercised bounded relevance, tenant denial, idempotency, local reindex and deletion, stale approval, prompt-injection containment and unavailable embeddings. |
| Disposable PostgreSQL 18.4 | Goal/task invalidation trigger creation, stale marking, chunk purge and teardown passed with temporary tables. Offline Alembic SQL generated the vector schema. Online migration and vector tests were blocked because the local installation lacks the `vector` extension. |
| Frontend lint, TypeScript and Next.js build | Passed. The build used temporary worker threads, one worker and the internal TypeScript runner to work around sandbox `spawn EPERM`. The Next.js config was restored. |

Retrieval tests used deterministic synthetic vectors. The missing-model case exercised the real unavailable-encoder path. A real model relevance run and pgvector query execution remain open. No real user database or live provider was accessed.

## Task 03 workflow reliability

| Check | Actual result |
| --- | --- |
| Existing PostgreSQL concurrency tests before changes | 2 passed. The revision compare-and-swap and conditional grant decrement already admitted exactly one execution in each race. |
| PostgreSQL `tests/workflows tests/agents` after changes | 24 passed in 12.23 seconds, including both races, a fresh-process approval from persisted state and a real row-lock timeout. |
| SQLite `unit_tests tests` after changes | 146 passed, 2 skipped in 23.40 seconds. The skips require independent PostgreSQL connections and passed in the PostgreSQL run. |

Both suites used a unique Windows pytest `--basetemp` with the pytest cache disabled. PostgreSQL 18 ran in a fresh loopback-only cluster with a disposable `aura_workflow_test` database and a randomly named test schema. SQLite restart coverage copied the synthetic in-memory database to a test file and resumed it in a fresh Python process. Providers were disabled or mocked. Frontend checks were outside this run because no frontend source or successful response contracts changed.

The new tests cover manual approval expiry and rejection, cross-user transition and grant denial, duplicate execution, rollback after a database error following task flush, and missing or corrupt checkpoint recovery. An unavailable checkpoint produces a safe conflict and allows owner cancellation. A transient PostgreSQL failure rolls back and returns a retryable 503. The server does not replay write requests automatically. Checkpoint compatibility across LangGraph upgrades and recovery after an ambiguous commit outcome remain outside this evidence.

## Checkpoint baseline

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
## Task 26.2 staging preparation and distributed security

**PARTIAL.** Local validation passed. Hosted staging and alert delivery remain pending.

| Check | Result |
| --- | --- |
| Affected PostgreSQL regressions | 67 passed, zero failures or skips. Included auth rate limits, Google OAuth and reads, CORS, health, production settings, and security boundaries. The four shared-security tests also passed after adding the sanitized outage log. |
| Concurrent controls | Twelve requests competing for five admissions produced exactly five successes. Twelve OAuth consumers received one owner-and-scope-bound grant. Forced PostgreSQL expiry, replay rejection, bounded storage and fail-closed behavior passed. |
| Two production API containers | Alternating login requests returned 401, 401, 401, 401, 401, then 429. OAuth state issued by the first API survived its restart and the second API consumed it. Through the HTTPS Next.js callback, replay returned 400. The route returned 503 when the simulated edge identity was absent and applied a no-referrer policy. The generated authorization URL carried the exact HTTPS callback and Gmail read-only scope with identity scopes. The probe stopped before token exchange. |
| Deployment configuration | Production Next.js and shared FastAPI/worker images built. Frontend ESLint and TypeScript passed. The Blueprint passed Render's published JSON Schema. Disposable migration reached `f6b14d802c31` and Alembic reported no new upgrade operations, with the existing vector reflection warning. |
| Hosted checks | Edge client-IP provenance and query redaction, hosted certificates/HSTS, managed restore and capacity, and alert delivery need staging evidence. |
## Task 26.3B.1e load profile

The corrected host-side benchmark ran against the disposable PostgreSQL stack through the authenticated frontend proxy. AI used the deterministic local planner. Twenty synthetic identities and unique goal records were used. The first 30-second smoke phase passed with 358 successful end-to-end workflows and zero errors.

| Phase | Requests | Throughput | p50 | p95 | p99 | Unexpected errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 user, 30 s | 1,412 | 46.75/s | 11.80 ms | 72.42 ms | 101.72 ms | 0 |
| 5 users, 30 s | 2,020 | 63.93/s | 78.22 ms | 193.14 ms | 295.28 ms | 0 |
| 10 users, 30 s | 1,604 | 47.61/s | 124.44 ms | 502.97 ms | 783.76 ms | 0 |
| 20 users, 30 s | 2,048 | 66.51/s | 283.54 ms | 575.72 ms | 697.47 ms | 0 |
| 10 users, 600 s | 32,508 | 53.61/s | 158.40 ms | 492.05 ms | 790.21 ms | 0 |

Every recorded request was successful. No rate-limit responses occurred. A 60-second idle baseline was collected. Raw request JSON, resource samples, and phase summaries are in the ignored local profiling directory `backend/.env.production-smoke-secrets/benchmark-results-corrected`.

Resource sampling was slower than the requested two-second interval because each sample invokes Docker CLI statistics and a PostgreSQL query. The sustained run produced 53 resource samples over 600 seconds. Samples show peak observed memory approximately 160 MiB API, 85 MiB PostgreSQL, 72 MiB worker, and 85 MiB frontend against configured 512/256/512/512 MiB limits. OOM flags remained false. This collector did not expose cgroup CPU throttling counters or memory.peak, and its PostgreSQL query measured connection counts rather than transaction latency. These values are observed sample maxima, not cgroup peaks. CPU readings were instantaneous Docker statistics. Treat limits as provisionally adequate for this deterministic synthetic workload, pending a higher fidelity profile and real workload mix.
## Task 26.3B.2e PostgreSQL regression recovery

The earlier regression failures used an invalid placeholder password. The ignored Docker configuration supplied the test container password without exposing it. Verified the disposable server identity as `aura_test` / `aura_workflow_test` on host port 15432, server port 5432, with pgvector 0.8.7. The regression command then passed **41 tests, zero failures, zero skips** in 6.72 seconds. Production TLS settings accepted only `verify-full` and rejected a missing CA path. The separate bootstrap database runtime role passed CRUD, sequence and goal persistence checks. Its superuser, createdb and createrole flags were false; DDL and role creation were denied. No main database was used.


## Task 26.3B.4 final release verification

| Check | Outcome | Evidence |
| --- | --- | --- |
| Full PostgreSQL regression | **217 passed, 0 failed, 0 skipped** | `backend/.venv/Scripts/python -m pytest -q`; disposable `aura-pgvector-test-15432`, guarded URL (`aura_test` / `aura_workflow_test`, loopback 15432). One offline sentence-transformers deprecation warning. |
| Full SQLite regression | **212 passed, 0 failed, 5 skipped** | Same full suite without PostgreSQL URL; skips are PostgreSQL-only tests. |
| ESLint | **Passed** | `npm run lint`. |
| TypeScript | **Passed** | `npm exec tsc -- --noEmit`. |
| Production frontend build and E2E | **4 passed** | `npm run test:e2e`; Playwright webServer built production frontend. Mocked Google consent/read path, console email, disabled AI, temporary SQLite. Initial run found missing Playwright Chromium and default Python lacked `langgraph`; installed the browser and pointed the harness to backend venv, then all four journeys passed. |
| Migration head and drift | **Passed** | Disposable profiling PostgreSQL: current/head `f6b14d802c31`; `alembic check`: no new upgrade operations. SQLAlchemy emitted the known vector reflection warning; pgvector `0.8.7`. |
| Render Blueprint | **Passed locally** | YAML parser and structural wiring assertions: 1 DB, web, private API and worker; runtime URL secret is manually provisioned, worker consumes API runtime URL, API/worker use `verify-full`, migration verifier is configured. Published schema validation remains recorded in Task 26.3B.2 evidence. |
| Runtime-role API workflow | **Passed** | Disposable `aura_fresh` at 127.0.0.1:25433, role `aura_runtime`, head `f6b14d802c31`, vector `0.8.7`: register, email verification via captured console fixture, login, goal creation, deterministic plan, approval/execution and list passed. AI disabled; no provider request or email delivery. |
| Existing benchmark | **Passed** | 41,024 synthetic requests total including 30-second smoke, 1/5/10/20-user phases and 600-second sustained run; zero unexpected errors, zero rate limits. |
| Final sampled workload | **Passed** | 10 users / 30 seconds through frontend proxy: 1,408 requests, 43.32/s, p50 182.29 ms, p95 514.28 ms, p99 1,093.31 ms, zero unexpected errors/rate limits; all auth 200, goal 201, planning 200 and scheduling 200. |

### Resource evidence and remaining capacity issue

The 60-second idle sampler collected 31 cgroup/DB samples at exactly two-second intervals. The corrected 30-second workload sampler collected 16 samples at exactly two-second intervals (15 intervals). Raw data and summaries are retained under the ignored local path `backend/.env.production-smoke-secrets/`; no profile artifacts are release files. Limits were frontend/API/worker 512 MiB and 0.5 CPU each; PostgreSQL 256 MiB and 0.1 CPU. cgroup high-water memory was frontend 118.5 MiB, API 273.6 MiB, worker 73.8 MiB, PostgreSQL 202.8 MiB. OOM-kill deltas were zero. This leaves PostgreSQL **20.8%** memory headroom, below the 25% target (the 256 MiB plan would need measured peak <=192 MiB).

During the successful sampled workload, `nr_throttled / nr_periods` deltas were frontend 35/301 (11.6%), API 151/316 (47.8%), worker 31/100 (31.0%), PostgreSQL 287/316 (90.8%). Throttled-time counter deltas were 3.02 s, 19.08 s, 1.59 s and 155.06 s respectively. PostgreSQL peaked at 16 connections; the `SELECT 1` client round trip was p50 1.03 ms and p95 81.47 ms; transaction counter delta was 3,561. The throttled-time counter is aggregated cgroup time and can exceed wall-clock duration.

API container start to logged application startup completion was **4.356 seconds**. `/readyz` returned 200 during the run. Docker retained only recent health-check records, so exact first cold `/readyz` success time could not be recovered without restarting the existing stack; cold readiness remains unverified. A probe missing the trusted proxy identity received 503 as designed; the corrected synthetic benchmark used reserved test address `192.0.2.88` and ingress controls stayed enabled.


## Task 26.3B.4a Render Postgres capacity gate

No regression suites were rerun. Render's current next Postgres tier is `0.5c-1g`: 0.5 CPU, 1 GB RAM, 100 connections, $19/month; the former `0.1c-256mb` is 0.1 CPU, 256 MB, 100 connections, $6/month. The disposable PostgreSQL container alone was updated in place to matching 0.5 CPU / 1 GiB; its existing named volume was preserved, and API/worker/frontend limits remained 0.5 CPU / 512 MiB. Render's Postgres plan is updated to `0.5c-1g` in the local Blueprint only.

| Phase | Requests | p50 / p95 / p99 | Unexpected errors | DB max connections | DB memory high-water | DB throttling |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| Idle 60 s | 0 | n/a | 0 | 7 | 202.8 MiB | 0/173 periods |
| 10 users, 30 s | 1,968 | 121.85 / 293.54 / 386.18 ms | 0 | 13 | 202.8 MiB | 2/314 (0.64%) |
| 20 users, 30 s | 2,068 | 282.51 / 508.28 / 618.62 ms | 0 | 17 | 209.3 MiB | 0/311 |
| 10 users, 600 s | 38,804 | 123.68 / 295.35 / 390.14 ms | **1** | 14 | 210.3 MiB | 27/6,009 (0.45%) |

All four phases sampled through Docker statistics and a live PostgreSQL connection. The idle run recorded 30 samples over 60.94 s; short load phases recorded 16 samples each with approximately two-second cadence; the valid sustained run recorded 299 samples over 600.04 s between first and last UTC samples, maximum observed interval 2.06 s. PostgreSQL transaction RTT during sustained load was p50/p95 1.85/2.70 ms. OOM-kill deltas were zero in every valid phase. The single sustained request error was a planning transport `URLError`; there were zero 429 responses.

Three API restarts were externally polled from the separate frontend container; first `/readyz` HTTP 200 occurred in 5.229 s, 3.800 s, and 3.782 s.

The sustained-only retry with default synthetic token expiry is **invalid**: a 5,832-second sample gap preceded 14 requests receiving 401 after test token expiry. The retry artifacts remain preserved. A later 24-hour-token retry was interrupted and is incomplete; its partial raw resource file remains preserved. Neither is used as passing evidence. Sustained capacity/reliability approval remains **provisional** and is deferred to hosted staging. Raw results remain ignored at `backend/.env.production-smoke-secrets/benchmark-results-tier-0.5c-1g`; no raw data was removed.

## Task 26.3D.2b compatibility validation

The owner reported a passing database preflight and **2 passed, 0 failed, 0 skipped in 0.39s** in standalone PowerShell. The target was the disposable `aura_bootstrap_test` database on `127.0.0.1:15432`, running PostgreSQL 17.12 with pgvector installed and an authenticated non-superuser admin with `CREATEROLE`. The owner reported that `git diff --check` passed and the temporary credential environment variable was removed.

- `test_migration_database_url.py` verifies that the migration CLI preserves the original URL and that Alembic receives the synthetic password, connection timeout, `verify-full`, and CA path. This is a mocked URL regression test.
- `test_bootstrap_database.py` verifies bootstrap with the non-superuser admin, authenticated migrator creation of a table and sequence, runtime insert/update/delete, and denial of runtime schema `CREATE` as reported by PostgreSQL's privilege check.

The earlier writable-snapshot run reported **8 passed, 0 failed, 1 skipped**. It included the migration URL test and seven production configuration cases. The bootstrap case skipped because the disposable admin URL was absent. The final run selected only the two compatibility files and ran both cases.
