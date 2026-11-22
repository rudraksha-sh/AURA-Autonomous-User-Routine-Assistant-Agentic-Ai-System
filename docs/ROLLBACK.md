# Rollback and recovery

## Database transactions

A workflow start or resumed transition runs in a single SQLAlchemy transaction. The checkpoint or result, grant consumption, task writes and verification receipt share one commit boundary. Failure before commit rolls them back together.

- **Atomicity.** Creation, receipt verification and terminal status commit as one unit.
- **Consistency.** Ownership checks precede action. Foreign keys bind runs and grants to users and goals.
- **Isolation.** PostgreSQL uses read committed isolation with conditional updates on workflow revisions and grant counters. Row locks protect goals during writes and unchanged tasks during undo.
- **Durability.** The approval journal is durable at request boundaries. A new request reconstructs graph state. After a lost response, retrieve the run or replay the same start UUID and input. Before repeating a decision, obtain the current revision.

## Application undo

Undo removes only tasks from a selected workflow when each task matches its stored fingerprint and has no subtasks, logged activity or schedule entries. It requires confirmation and the current revision. If one task changed or went missing, the whole undo is rejected. Verification can report the original tasks unverified after undo. Grant usage stays recorded.

## External effects and release recovery

External systems cannot share a PostgreSQL transaction. An external execution path needs an atomic outbox insert, leased retries, backoff, provider idempotency, dead letters, reconciliation and a scoped compensation policy. Irreversible external actions have no undo.

Capture a database snapshot and test restore in a separate environment before deployment. Keep managed backups and point-in-time recovery enabled. Roll back the application first while preserving additive tables. The migration downgrade deletes new workflow data and needs explicit operational approval. Keep checkpoint library pins while approvals are pending or test the format before upgrading. [PostgreSQL backup and restore](https://www.postgresql.org/docs/current/backup.html)
