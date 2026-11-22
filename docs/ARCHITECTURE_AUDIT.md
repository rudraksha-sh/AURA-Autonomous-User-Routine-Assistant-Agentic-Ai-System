# Architecture audit

The project is the nested Git checkout on `feature/aura-langgraph-multi-agent-system` at `83e2fe4`. Its initial tracked worktree was clean. The outer `D:/AURA` checkout is on `main` and already reported the nested checkout as modified. Existing branches, local configuration, database files and ignored backups were left in place.

| Area | Implementation observed | Gap or verification boundary |
| --- | --- | --- |
| Web | Next.js App Router with protected dashboard, goal, task, planner, daily planning and settings screens. Theme provider and shared components are already present. | No workflow-specific activity or approval interface at baseline. |
| API and identity | FastAPI contracts for goals, tasks, AI, planning, profile, Google and notifications. JWT, Argon2, OTP, authorization dependencies, CORS and rate limiting exist. | Rate limits and Google OAuth state are process-local. Review multi-worker behavior before deploying. |
| Database | SQLAlchemy models and Alembic history for users, goals, tasks, planner runs, integration records, preferences and schedule entries. PostgreSQL is the production dialect. Development supports SQLite. | Existing `AgentRun` records represent planner saves, not graph checkpoints. No migration against existing user databases was attempted. |
| Planning | OpenRouter planner and deterministic fallback exist. Goal plan preview and idempotent task creation already have API and UI entry points. A separate deterministic template planner also exists. The legacy goal-creation checkbox can generate tasks and attempt a daily schedule within the submit request. | Milestone and dependency graphs are outside existing plan contracts. |
| Scheduling | Daily preferences, schedule previews, user approval, calendar busy-block lookup and deterministic what-if scenarios exist. | Goal-plan proposals lack task IDs until approval. Scheduling proposed tasks requires the existing what-if path or an explicit transient representation. |
| Integration | Google OAuth, credential loading and Gmail, Calendar and Drive service builders exist. Calendar busy blocks have a functional consumer. | OAuth tokens are stored directly in integration records. Gmail/Drive builders do not by themselves establish authorized retrieval workflows. No GitHub runtime adapter identified. |
| Privacy | Account export/deletion, profile preferences and Google disconnect exist. | Export is goal/task-oriented. Disconnect removes the local integration. New persisted workflow data needs explicit deletion and retention handling. |
| Assistant | Voice assistant and allowlisted tool registry exist. | The planner package is the only agent implementation at baseline. No LangGraph dependency, orchestration or checkpointing found. |
| Tests | Existing SQLite unit tests and a PostgreSQL API suite cover major features. | PostgreSQL fixture truncates a fixed database and sets global environment during collection. The README reports combined-suite registration conflicts. Docker Desktop engine was unavailable during initial inspection. |
| Cleanup | Ignore rules already cover environments, secrets, caches and build directories. | No file was conclusively established as safe to remove during initial audit. |

## Implementation order

1. Isolate the API test harness and establish a safe, reproducible baseline.
2. Add the Supervisor and typed graph around existing deterministic planning and scheduling. Persist a bounded approval state and keep existing endpoints stable.
3. Extend tenant-bound context and explicit preference controls, then add simulation and replanning.
4. Add execution, verification and recovery for confirmed local writes. External effects need a separate outbox, scoped consent and reconciliation layer.
5. Integrate visible workflow state into the existing UI and verify accessibility, migrations and failure recovery.

See [the test report](TEST_REPORT.md) for subsequent SQLite and isolated PostgreSQL verification.
