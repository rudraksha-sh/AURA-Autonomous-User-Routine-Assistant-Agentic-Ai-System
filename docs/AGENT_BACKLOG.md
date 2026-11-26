# AURA implementation backlog

Tasks 03–16 are proposed scopes derived from the [agent audit](AGENT_AUDIT.md). Dependencies are prerequisites for the listed scope. Each task should preserve existing API behavior unless a contract change is explicit and tested.

| Task | Priority | Depends on | Scope and completion evidence |
| --- | --- | --- | --- |
| 03 | P0 | — | **Complete.** Verified both PostgreSQL races, fresh-process checkpoint reload, expiry and rejection, tenant denial, duplicate handling, rollback and checkpoint/timeout recovery. PostgreSQL 24 passed. SQLite 146 passed, 2 PostgreSQL-only skips. See the [test report](TEST_REPORT.md). |
| 04 | P0 | 03 | **Partial.** Opt-in context ingestion, scoped semantic retrieval, versioned Planner handoff, stale-write protection and a workflow preview are implemented. Task 04.1 validates legacy and versioned checkpoint handling and a local 384-dimensional encoder fixture. The online migration, pgvector query suite and pretrained-model relevance remain open. See the [test report](TEST_REPORT.md). |
| 05 | P0 | 03, 04 | **Implemented.** Consent-scoped OAuth, encrypted reads, Gmail search/read, Drive discovery/text, Calendar free/busy and explicit revocation. Provider tests use mocks. |
| 06 | P1 | 03, 05 | **Implemented.** Owner-only planning memories, opt-in context references, expiry and write-time purge. Scheduled expiry cleanup remains open. |
| 07 | P1 | 06 | **Implemented.** Local tasks, saved reservations, time zones, deadline constraints and opt-in Calendar availability share a read-only preview. Local booking remains a separate approval. |
| 08 | P1 | 07 | **Implemented.** Read-only capacity, blocked-time and owned deadline scenarios report baseline and scenario feasibility through the shared scheduler. |
| 09 | P1 | 08 | **Implemented in the workflow workspace.** Selected completed runs are checked every 30 seconds while visible. Task drift, overdue deadlines and saved-schedule overlaps prompt a revised preview. Changes require approval. Background detection for unviewed runs remains open. |
| 10 | P1 | 06 | **Partial.** Allowlisted sandbox calendar-hold port, dry run, explicit confirmation, dispatch and outcome reconciliation. Only mock adapters were exercised. The runtime adapter registry is empty by default. |
| 11 | P1 | 09, 10 | **Implemented.** Read-only task verification compares the recorded fingerprint for each task. Provider receipts bind the response identifier and action fingerprint. Rechecks report verified, changed, failed or unknown. |
| 12 | P2 | 10 | **Implemented.** Default-off, single-effect provider/action/goal consent, expiry, pause, revoke, emergency stop and server-side revision and ownership checks. An already-dispatched effect can return late evidence after revocation. |
| 13 | P2 | 06 | **Partial.** Durable outbox claims, stable keys, bounded worker, backoff after proven no-effect failures and lookup-only recovery for ambiguous outcomes. Worker scheduling and provider-specific callback and compensation contracts remain open. |
| 14 | P1 | 04, 05 | **Implemented.** Deterministic workload pressure, scheduled-work feasibility and deadline-risk counts with reasons in the workflow preview. |
| 15 | P2 | 05, 13 | **Partial.** Workflow dashboard, capability labels, confirmation prompts and execution audit history added. Keyboard and screen-reader QA remains. |
| 16 | P2 | 04, 05, 14, 15 | **Partial.** Bounded worker, callback deduplication, compensation interface and release gates added. Provider-specific verification and pgvector remain blocked. |

Task 03 used synthetic fixtures, an isolated PostgreSQL database and disabled or mocked providers.
