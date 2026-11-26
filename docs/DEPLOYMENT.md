# Production deployment

This package prepares an x86-64 Linux release. The local reference stack runs Caddy, a standalone Next.js server, one FastAPI process, one worker and PostgreSQL 17 with pgvector. It is separate from the development Compose project. External provider write adapters stay empty. Remote AI is disabled.

## Files and build

| File | Purpose |
| --- | --- |
| [compose.production.yml](../compose.production.yml) | Single-host reference with separate public-edge and private database networks, bounded resources and a one-shot migration gate |
| [frontend/Dockerfile](../frontend/Dockerfile) | Node 24.22.3 multistage build with npm lockfile and standalone output |
| [backend/Dockerfile](../backend/Dockerfile) | Python 3.13.18 image shared by API, worker and migration job |
| [requirements.production.lock](../backend/requirements.production.lock) | Hash-locked Linux x86-64 wheel set, installed with hash verification and followed by pip check |
| [deploy/Caddyfile](../deploy/Caddyfile) | HTTPS redirect, automatic TLS or local CA, HSTS, request cap and same-origin routing |
| [deploy/postgres-init.sql](../deploy/postgres-init.sql) | Reference-only initialization for a fresh database with separate admin, migration and runtime roles |
| [deploy/production.env.example](../deploy/production.env.example) | Non-secret environment and address settings for Compose |

Base images use digests. Tag app images with an immutable release ID, record their published digests and rescan the final images, OS layers and optional dependencies before promotion. Refresh the Python lock inside the pinned Python image on linux/amd64 using pip install --dry-run --ignore-installed --only-binary=:all: --report, then record each resolved wheel's name, version and SHA-256. The optional local embedding model is outside the image and requires a separate audited dependency set, verified offline model artifact and larger resource budget.

## Settings and secrets

Copy the example to a private operator env file. Use one HTTPS public origin for FRONTEND_URL, CORS_ORIGINS and the optional Google callback. Set AURA_HOST to the DNS hostname and keep ingress loopback-only while testing. For a future public host, bind ingress to the intended interface, route 80 and 443, and use a real ACME contact. SMTP host, sender identity and port go in the non-secret settings. Put SMTP credentials in the secret store, and verify transport and delivery separately before launch.

Provision these files through a secret manager or a private host directory. The Compose env file contains only the directory path. On a Linux host, keep the parent directory operator-only and make each file readable by the actual container UID that consumes it. API and worker use UID 10001. Resolve the database UID from the pinned image. Compose file mounts inherit host file permissions, so verify the effective access from the containers.

| Secret file | Scope and provisioning |
| --- | --- |
| db_admin_password | Fresh PostgreSQL bootstrap password. Used by the local reference database only. |
| runtime_db_password, migration_db_password | Different random PostgreSQL role passwords for fresh reference initialization. |
| runtime_database_url | Runtime-role SQLAlchemy URL. API and worker use it. In the reference use postgresql+psycopg://aura_runtime:<encoded-password>@db:5432/aura?connect_timeout=3. |
| migration_database_url | Direct migrator-role connection with bounded connection timeout. Only the migration job mounts it. |
| JWT_SECRET_KEY, OTP_PEPPER | Generate two independent values with Python secrets.token_urlsafe(48). Keep them shared across all API replicas when scaling. Rotate any previously exposed credential before provisioning. |
| INTEGRATION_TOKEN_KEY | Generate a Fernet key and keep an encrypted recovery copy. Coordinate rotation and re-encryption or relink affected accounts. |
| GOOGLE_CLIENT_SECRET | Mount only for the API. Leave empty with AURA_GOOGLE_CLIENT_ID empty to keep the integration unavailable. If authorized later, configure the exact callback URI and read-only scopes. |
| SMTP_PASSWORD | API relay credential only. Keep the worker off the public network. |

Production startup rejects a blank, malformed, low-diversity or JWT-reused OTP pepper and requires a valid Fernet key, HTTPS CORS origins and SMTP settings. The Task 25 OTP sample finding was a false positive caused by a pattern crossing the newline after an empty assignment. A line-scoped review found two historical assignments and both were empty. The runtime cannot determine whether a valid-looking secret was exposed outside Git, so generate fresh values and never carry forward any known exposed value.

## Local validation and future release sequence

For a disposable drill, create a unique project name and fresh secret files. Use localhost, ports 18080 and 18443, AURA_PUBLIC_ORIGIN=https://localhost:18443, AURA_TLS_ISSUER=internal and an unused SMTP hostname. Use matching random fixture passwords in the URL and role files. Keep the local CA in the test client trust context only.

Run from the repository root with the intended project and private env file every time.

```sh
docker compose -p aura-prodcheck --env-file /path/to/local.env -f compose.production.yml config -q
docker compose -p aura-prodcheck --env-file /path/to/local.env -f compose.production.yml build api frontend ingress
docker compose -p aura-prodcheck --env-file /path/to/local.env -f compose.production.yml up -d --no-build --wait --wait-timeout 90
docker compose -p aura-prodcheck --env-file /path/to/local.env -f compose.production.yml run --rm --no-deps migrate python ops/migrate.py current
docker compose -p aura-prodcheck --env-file /path/to/local.env -f compose.production.yml run --rm --no-deps migrate python ops/migrate.py check
```

Confirm HTTP 308 to the chosen HTTPS origin, TLS verification using the local CA, HSTS, a frontend 200, a protected API 401, separate worker live and ready, and no published database, API or worker ports. Confirm the database major version, pgvector extension version, the context embedding column type and the migration head. For the local release, expect PostgreSQL 17, pgvector 0.8.7, vector(384) and revision e781ac36d940. Validate runtime grants with has_schema_privilege and role flags.

For a future authorized release, provision PostgreSQL and preinstall vector through an admin workflow. Use a direct migrator URL for a single migration job before routing traffic or starting the worker. Give the application role data privileges only. Verify the database independently before accepting traffic, and rehearse each upgrade from a restored copy. For remote databases, keep private VPC routing and require verified TLS using the provider trust bundle. Keep one API replica until hosted shared-state capacity and ingress trust are verified.

## Ingress, scaling and monitoring

Only Caddy publishes ports. It routes /api and /auth subpaths directly to FastAPI, keeps application probes out of public routing, and limits incoming bodies to 6 MiB. Uvicorn trusts forwarded metadata only from Caddy's fixed edge address. The dynamic address pool excludes Caddy's reserved address. If the subnet changes, update the reservation, pool and Uvicorn allowlist together. When adding a managed edge or CDN, restrict the origin firewall, validate which proxy supplies the client address and strip untrusted forwarding headers. HSTS is set on HTTPS responses. Add includeSubDomains only after verifying all subdomains support HTTPS.

Production requires the shared PostgreSQL limiter and OAuth state store described in the Task 26.2 staging runbook. The in-memory stores serve local development and SQLite tests.

Docker supervises process exits. API and worker stop with SIGTERM and bounded drain periods. Worker liveness is on loopback port 8091. The monitor should check API readiness and worker liveness and readiness every 10 seconds from a private namespace and route three consecutive failures to application or worker on-call. Route worker database failures and backup misses to database on-call. Route unknown external outcomes to the integration owner for lookup-only review. Route ingress errors, stalled polling and certificate expiry to operations. Docker health status alone does not restart a stalled process. Configure a bounded host watchdog and test real alert delivery before public exposure. Keep probe responses and the Docker socket outside public ingress. [Worker monitoring](WORKER_MONITORING.md)

## Backup, restore and rollback

Before every migration, capture a managed PITR point or a fresh encrypted logical export. Schedule regular encrypted off-host backups of PostgreSQL and the profile volume; protect the corresponding secret recovery material separately. Start with nightly encrypted exports retained for 30 days and seven days of PITR where available. Use a provisional 15-minute RPO and 60-minute RTO for the managed architecture and measure both during a staging restore. Keep backup ages and restore drill results in the launch checklist.

Restore into a separately named database or replacement service. Verify the revision, extension, representative row counts, tenant boundaries and profile-file references. Test the previous image against a compatible schema before promotion. Roll back images by immutable digest if the schema remains compatible. For an incompatible migration, freeze writes, keep the affected database available for reconciliation, restore into a clean target, verify it and arrange a deliberate cutover. Avoid unattended destructive downgrades. Reconcile uncertain work without replaying provider effects.

## Hosting tradeoffs

Illustrative USD/month estimates checked against public pricing on November 26, 2026. Estimates exclude taxes, domain, SMTP and workload-dependent charges.

| Option | Estimate | Operational tradeoff |
| --- | --- | --- |
| **Recommended** Render Docker frontend, private FastAPI, worker and managed PostgreSQL in one region | **$58** compute baseline for $7 frontend, $25 API, $7 worker and $19 PostgreSQL. Workspace, disks, storage and bandwidth can add charges. PostgreSQL provides shared security state. | Separate failure domains and managed database recovery. Verify platform TLS/HSTS, trusted client IP propagation, private API health and durable profile uploads in staging. Build the frontend with the private API URL and use a one-off migrator with a separate role. [Render pricing](https://render.com/pricing) and [Render private networking](https://render.com/articles/how-render-handles-private-networking) |
| Single DigitalOcean VM with the reference stack | **$24** for a 4 GiB Basic VM before backups and storage. | Direct match for the tested Caddy configuration. The operator owns patching, off-host backups, VM recovery and the single-host failure domain. [DigitalOcean VM pricing](https://www.digitalocean.com/pricing/droplets) |
| DigitalOcean VM with a private managed PostgreSQL endpoint | **$39.15** starting estimate for the same VM and the $15.15 database plan. | Retain Caddy and container control while handing off database operations. Replace the reference database service with an approved private endpoint and verify extension version, TLS, and role provisioning in staging. [DigitalOcean VM pricing](https://www.digitalocean.com/pricing/droplets) and [managed database pricing](https://www.digitalocean.com/pricing/managed-databases) |

## Local rehearsal evidence

| Check | Result |
| --- | --- |
| Builds and runtime | Docker Engine 29.7.2 and Compose 5.3.1 built the ingress, standalone Next.js and shared backend image. All 83 backend wheels installed with SHA-256 verification. pip check and the production Python lock scan passed. Runtime UIDs were 10001 for ingress, API, worker and migrator, 1000 for Next.js and 999 for PostgreSQL. CPU, memory and PID limits were present for every container. |
| Ingress and network | Only loopback ports 18080 and 18443 were published. HTTP redirected with 308. The HTTPS client trusted only the exported test CA and observed HSTS, frontend 200, protected API 401 and public readiness 404. The database network was internal and Uvicorn's trusted ingress address matched the reserved Caddy address. |
| Database and restore | A fresh PostgreSQL 17.12 database migrated to e781ac36d940. pgvector 0.8.7 and vector(384) were present. Alembic check reported no new upgrade operations and emitted its existing vector reflection warning. The runtime role could insert the synthetic canary and lacked schema CREATE. The migrator could create schema objects and lacked superuser, CREATE DATABASE and CREATE ROLE. A custom-format dump restored into aura26_restore with one canary row, the same revision and the same vector type. |
| Failure recovery | An unreachable database initially caused API readiness to exceed the client timeout. The final probe uses a bounded shared check and returned HTTP 503 in 3.03 seconds during a real container outage, then returned 200. Worker liveness and readiness were 200/503 during outage and readiness recovered to 200. SIGTERM produced exit 0 and worker_stopped under a 45-second container grace period. A restarted worker returned live/ready 200/200. |
| Scope | 38 focused tests passed in 2.51 seconds. git diff --check passed. Provider writes stayed disabled. Production fixture settings and secret files were ignored by Git. No hosted infrastructure or live provider endpoints were used. |

## Release gates

Chromium desktop, tablet and mobile journeys passed previously. Firefox, Safari, real-device checks and manual assistive-technology verification remain open. Managed-host networking, public certificate issuance and renewal, SMTP, hosted shared-state capacity, off-host backup retention, recovery objectives and on-call alert delivery still require staging evidence. Validation scope was local and used fixture secrets and disabled external providers.
## Task 26.2 Render staging runbook

[render.yaml](../render.yaml) defines the public Next.js service, a private FastAPI service, a background worker and private PostgreSQL 17 in Oregon. Previews and auto-deploys are off. Next.js rewrites same-origin `/api/*` requests to the private API. Its public callback is `https://STAGING_PUBLIC_HOST/api/integrations/google/callback`. Use that exact URI in the application and any future approved staging OAuth client. The shipped staging template leaves Google credentials blank and provider writes disabled. [Render Blueprint specification](https://render.com/docs/blueprint-spec)

After separate authorization to provision staging:

1. Use an isolated workspace or environment and register the staging domain. Set `FRONTEND_URL` and `CORS_ORIGINS` to the exact HTTPS origin. Confirm certificate verification, HTTP redirect and HSTS on the final hostname. Verify Render supplies an authenticated client address and overwrites or strips caller-supplied `CF-Connecting-IP`. Confirm the public proxy rejects missing or malformed values, private API ingress requires its shared credential, and OAuth callback query strings and internal headers are excluded from all request logs. Keep staging access restricted until these checks pass.
2. Bootstrap the managed database from the private network. The Render database resource is provisioned by the Blueprint with generated administrator credentials. In an ephemeral private operator environment, run `python ops/bootstrap_database.py` with `DATABASE_ADMIN_URL`, `AURA_RUNTIME_DB_PASSWORD`, and `AURA_MIGRATOR_DB_PASSWORD`. Generate independent passwords and discard the administrator URL after setup. The bootstrap enables `vector`, creates non-superuser `aura_runtime` and `aura_migrator` roles, gives schema creation only to the migrator, and sets migrator-owned default table and sequence grants for runtime DML. Set API and worker `DATABASE_URL` to the runtime `postgresql+psycopg` URL. Set `DATABASE_SSL_MODE=verify-full` and `DATABASE_SSL_ROOT_CERT` to the path of the managed PostgreSQL CA certificate provisioned as a secret file to both services. Do not use `require` or `verify-ca` in production because they do not both verify the server name. Supply the migrator URL only to the one-time private migration operator. Never add it to API or worker environment variables.
3. Supply independent freshly generated `JWT_SECRET_KEY`, `OTP_PEPPER` and Fernet `INTEGRATION_TOKEN_KEY` as runtime secrets. Populate SMTP using a staging-only relay and recipient restrictions. Use the Blueprint's generated `AURA_PROXY_SHARED_SECRET` across API and frontend. Only `AURA_API_HOSTPORT` is declared as a Docker build argument. Configure exact CORS and callback values before starting either backend service.
4. Take a managed restore point and check recovery on a disposable clone. From a private one-time migration operator, obtain the managed database owner URL temporarily and run `python ops/bootstrap_database.py` with independently generated runtime and migrator passwords. Store only the resulting runtime URL in the API's `DATABASE_URL` secret and share it with the worker through the Blueprint. Keep the migrator URL in the operator session only. Run `python ops/migrate.py upgrade` with that URL, then verify with the runtime URL using `python ops/migrate.py verify`. Do not place owner or migrator credentials in API or worker settings. API and worker pre-deploy commands require the exact Alembic head before each deployment. On a first release, bootstrap roles and pgvector, run the initial upgrade, confirm runtime verification, then deploy services. Psycopg and Alembic use `verify-full` and the supplied CA certificate. Confirm the certificate SAN matches the private database hostname. For rollout from process-local state, drain the old API, let its consent window expire or ask affected users to restart consent, and switch all replicas together.
5. Map the [monitor policy](../deploy/staging-monitoring.yml) to real destinations and issue a synthetic alert for each route. Render checks the public frontend over HTTP and the private API over TCP. Use an in-network observer for `/readyz` and a worker-local collector for its loopback health endpoints. Alert on API/worker readiness, shared-state 503s, worker queue age and terminal failures, and failed or overdue backups. Record delivery and acknowledgement. [Render health checks](https://render.com/docs/health-checks)
6. For rollback, pause intake and the worker, preserve the additive tables and restore compatible images together after checking the revision gate. An older image that uses process-local controls must stay behind closed authentication and OAuth ingress until a shared-state build is restored. Restore into a separate database if data recovery is necessary, verify revision and application data, and switch URLs only after recovery validation.

### Shared security state and staging cost

PostgreSQL uses one transaction per limiter key and an atomic conditional delete for state consumption. The database provides the clock for TTLs. Rate policies use short advisory locks, 16,384 active keys per policy, HMAC-derived principals, and 60-second or 300-second rolling windows. OAuth stores digests for up to ten minutes and caps live grants at 4,096. Expired rows are purged on writes to the respective store. Each API process uses up to four security connections, with a two-second checkout timeout, three-second connect timeout, two-second statement timeout and one-second lock timeout. Budget these in addition to ordinary API and worker connections. A security-store failure returns a sanitized 503 and carries no in-memory fallback in production. Valkey could isolate traffic from transactional workloads and offer atomic scripts and native expiry. A future design would need private authenticated transport, persistence and failover testing, plus explicit handling of lost or evicted keys. The PostgreSQL implementation avoids a second service at staging traffic levels. Load-test advisory-lock contention, connection headroom and expiry cleanup on the chosen plan before scaling. Shared durable profile uploads remain a separate scaling gate.

| Render staging option | Monthly compute estimate | Use |
| --- | ---: | --- |
| Three $7 services and $6 PostgreSQL | $27 | Minimum low-traffic staging with 256 MB PostgreSQL. Verify memory, connection headroom and restore support before relying on it. |
| Three $7 services and $19 PostgreSQL | $40 | Staging with 1 GB PostgreSQL when rehearsal shows the minimum tier is too small. |
| $7 frontend, $25 API, $7 worker and $19 PostgreSQL | $58 | Prior production-oriented baseline with more API headroom. |
| Optional paid Key Value | $10+ additional | Revisit only if staging load shows PostgreSQL contention that warrants a separate store. |

Estimates exclude workspace charges, storage, bandwidth, SMTP and external alerting. The Blueprint chooses $27 compute as the starting point for an authorized staging rehearsal. [Render pricing](https://render.com/pricing)
### Task 26.3B.1e measured local capacity

The disposable production images were exercised through the frontend proxy with deterministic local planning and synthetic users. The 10-minute, 10-user run completed 32,508 requests at 53.61 requests/second, with p50 158.40 ms, p95 492.05 ms, p99 790.21 ms, and zero errors. The 1, 5, 10 and 20-user phases also reported zero errors. Observed sampled memory maxima were about 160 MiB API, 85 MiB frontend, 72 MiB worker and 85 MiB PostgreSQL. Current Render allocations are 512 MiB for each app service and 256 MiB for PostgreSQL, which leaves at least 68% observed memory space in this limited run.

This profile supports using the $27/month compute configuration for a low-traffic staging trial, with embeddings disabled and deterministic planning. It does not establish production sizing. Docker CLI sampling yielded only 53 samples over the sustained 600 seconds, and did not capture cgroup memory.peak or CPU throttling counters. PostgreSQL transaction latency and full connection-pool peak were not measured. Reassess with a cgroup-aware collector and hosted metrics before enabling model inference or increasing load.


## Task 26.3B.4 capacity and release evidence

The local disposable production-profile stack remains at frontend/API/worker 0.5 CPU and 512 MiB each, PostgreSQL 0.1 CPU and 256 MiB. The cgroup high-water profile measured 118.5/273.6/73.8/202.8 MiB respectively, with no OOM kills. PostgreSQL retained only 20.8% memory headroom, below the 25% target; its 0.1 CPU was throttled in 287 of 316 periods (90.8%) during the successful 10-user profile. Do not retain the $27/month configuration as capacity-approved. Select a PostgreSQL plan with at least 271 MiB capacity (next available tier likely 512 MiB) and more CPU, then repeat the sampled workload before staging approval. No current price or plan availability was re-queried.

The successful final sampled load was 1,408 requests in 32.5 s at 10 users, 0 unexpected errors, p50/p95/p99 182.29/514.28/1,093.31 ms. PostgreSQL max connections was 16, direct `SELECT 1` RTT p50/p95 1.03/81.47 ms, with 3,561 transaction-counter increments. The earlier completed benchmark remains 41,024 requests with zero unexpected errors, including 600 seconds sustained.

The API container log shows application startup completion 4.356 s after its recorded start; readiness returned HTTP 200 when sampled. The first cold readiness response timestamp was not retained, and the existing stack was not restarted to recreate it. Treat exact cold readiness as pending measurement. Full suite and build evidence is recorded in `TEST_REPORT.md`.


## Task 26.3B.4a capacity gate

The disposable profiling database was raised in place from 0.1 CPU / 256 MiB to 0.5 CPU / 1 GiB. Its named data volume remained `aura263b1a_profile_db`; API, worker and frontend limits were unchanged. The measured 0.5 CPU / 1 GiB database tier passed the local memory and database-contention checks, so `render.yaml` now selects Render Postgres plan `0.5c-1g`. This is a staging plan recommendation only; no hosted resource was provisioned.

Render's current catalog lists the prior `0.1c-256mb` tier at $6/month (0.1 CPU, 256 MB, 100 connections) and `0.5c-1g` at $19/month (0.5 CPU, 1 GB, 100 connections). Existing frontend/API/worker compute is 3 ? $7/month. Estimated compute becomes **$40/month** (3 ? $7 + $19), versus $27/month before. With minimum 1 GB database storage at $0.30/GB/month, the minimum service-plus-storage estimate is **$40.30/month**; workspace-plan fees and any additional storage are excluded. [Render compute plans](https://render.com/docs/compute-plans.md) and [Render pricing](https://render.com/pricing.md#compute).

The old 256 MiB/0.1 CPU profile peaked at 202.8 MiB (20.8% memory headroom) and throttled 287/316 CPU periods (90.8%) during its short 10-user sample. On the new tier, the valid 600-second sample peaked at 210.3 MiB/1 GiB (79.5% headroom), throttled 27/6,009 periods (0.45%), had 14 maximum connections, p95 transaction RTT 2.70 ms, and zero OOM kills. The 10- and 20-user short phases also had zero request errors, p95 latency 293.54 ms and 508.28 ms, max 13 and 17 connections, and zero OOMs.

Overall sustained approval is **provisional**: the valid 600-second phase had one planning transport `URLError` among 38,804 requests (all other requests successful, no rate limits). A later retry was invalid due a 5,832-second sampling gap and expired test JWTs; its raw artifacts are retained. A final retry was interrupted by owner instruction and is incomplete. Remaining sustained reliability validation is deferred to hosted staging. The three measured API cold starts reached first external `/readyz` HTTP 200 in 5.229 s, 3.800 s, and 3.782 s (median 3.800 s).
