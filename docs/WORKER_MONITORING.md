# Worker monitoring and recovery

Run the supervised worker from `backend/` with `python -m app.agents.execution.worker`. Set these variables in the worker process environment. PostgreSQL and existing app configuration must be available. The shipped adapter registry is empty.

| Variable | Default | Meaning |
| --- | --- | --- |
| `AURA_WORKER_HEALTH_PORT` | `0` | Enable HTTP probes on the selected port, bound to IPv4 loopback. Zero disables the listener. |
| `AURA_WORKER_POLL_SECONDS` | `2` | Delay after each poll, clamped to 0.1–60 seconds. |
| `AURA_WORKER_BATCH_SIZE` | `10` | Maximum actions selected per poll, clamped to 1–20. |
| `AURA_WORKER_STALE_SECONDS` | `90` | Mark the worker stalled after this long without a completed poll. Kept longer than the configured poll delay. |
| `AURA_WORKER_ALERT_PENDING` | `100` | Warn at this many pending records. |
| `AURA_WORKER_ALERT_UNKNOWN` | `1` | Warn at this many unknown outcomes. |
| `AURA_WORKER_ALERT_FAILED` | `1` | Warn at this many failed records. |
| `AURA_WORKER_ALERT_OLDEST_SECONDS` | `300` | Warn at this oldest-pending age in seconds. |

A threshold of zero disables its warning. `GET /livez` returns 503 for a stalled or stopped loop, while `GET /readyz` also returns 503 before the first successful poll or after a failed poll. A database outage can leave the loop live and unready. An unreachable probe can mean the process has exited. The readiness check includes the DB probe, outbox processing and aggregate query. Readiness does not imply an adapter is configured or a provider accepted any action.

The probes report the last completed and last successful poll timestamps, completed poll and processed counts since process start, the last DB connectivity probe result, a safe error code, and aggregates from the last successful poll. Pending counts all queued and dispatching records, including paused records or records waiting on retry backoff. Age is wall-clock seconds since the oldest pending record was previewed. Failed and unknown counts are current states. Retry count sums additional claimed attempts beyond the first across retained records. These are snapshots, so use the success timestamp to detect stale data and do not sum them across worker replicas.

## Supervision and private collection

Use the [Supervisor configuration](../backend/ops/worker.supervisord.conf) on a POSIX host or map its settings to your process manager. Install the backend requirements into a virtual environment, pass the existing application settings through the supervisor's environment, and set `AURA_BACKEND_DIR` and `AURA_WORKER_PYTHON` to the absolute backend directory and Python executable. Include the file in the supervisor's configuration, then review the effective command, environment and loopback port before starting it. The example restarts exits, allows five startup retries, and sends SIGTERM with a 45-second drain period before force termination. Choose a distinct probe port for each worker sharing a network namespace.

Collect both probes from the worker's host or network namespace every 10 seconds with a two-second request timeout. Keep port 8091 out of ingress, load balancers and public port mappings. Send sanitized status and structured logs to the operational collector. Deduplicate by environment, worker instance and event or metric name. For backlog totals, use one fresh snapshot per database.

| Signal | Route and response |
| --- | --- |
| Three consecutive `/livez` failures or connection errors after a 30-second startup grace period | Page worker on-call. Have the host watchdog request a supervisor restart with a bounded restart budget. Check supervisor exit status and logs if the replacement fails. |
| Three consecutive `/readyz` failures while `/livez` succeeds | Route to worker on-call and database on-call when `database_ready` is false. Check connectivity and credentials, then confirm recovery with a fresh `last_success_at`. Keep the worker running during a database outage. |
| `worker_threshold_exceeded` | Route pending count and age to worker on-call. Route unknown and failed outcomes to the authorized integration owner for review. |
| No recent `worker_metrics` or `worker_threshold_exceeded` events | Check that the worker is polling and that the log collector is receiving events. Compare with the private probes before intervening. |

Logs and probes omit tenant IDs, action IDs, payloads, provider receipts and exception messages. The Supervisor example handles process exits. Configure the private probe watchdog in the hosting environment for stalled-process restarts.

## Operator recovery

1. Check liveness, readiness, `last_poll_at`, and `last_success_at` together. For a live but unready worker, restore database connectivity and check that polls and successful timestamps advance. For a stalled worker, request a graceful restart and verify a successful poll from the replacement.
2. Review stale leases and failed or unknown actions through the authorized workflow or external-action interface. Preserve the operation key and audit trail. Avoid manual state changes or dispatch replay for any uncertain outcome.
3. Have the action's authorized owner request lookup-only reconciliation, then review the resulting evidence. Escalate unresolved outcomes to the integration owner.

Expired dispatch leases move to `unknown`. An authorized owner can request reconciliation through the existing external action transition API. It looks up the same operation key and owner/resource scope. A matching receipt verifies the action. A missing or mismatched receipt leaves it uncertain. Reconciliation and routine polling never requeue an ambiguous action. Without an adapter, reconciliation remains unavailable and the record stays unknown.

Task 22 exercised the real HTTP server and worker loop in local subprocesses with a disposable SQLite file. The outage returned live/ready HTTP 200/503. Restoring access returned 200/200. An exclusive database lock produced 503/503 until it was released. A SIGTERM raised inside each Windows subprocess exercised the installed handler and yielded exit code 0 with `worker_stopped`. A new PID then reached 200/200. The POSIX Supervisor configuration, host watchdog and PostgreSQL outage drill remain unverified. [Test report](TEST_REPORT.md)
