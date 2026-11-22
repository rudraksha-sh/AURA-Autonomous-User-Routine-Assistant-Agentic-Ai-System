# Permissions and privacy

Autonomous mode lets AURA perform approved actions within the permissions and resource scopes you grant. Actions may modify data. Some external actions cannot be undone.

New workflows require review unless the user selects an active grant. A grant authorizes local task creation on one owned goal for 5–60 minutes. The user chooses up to five runs and three to eight tasks per run. Each run starts when the user submits it. The grant records the resource, operation, consent version, limits and timestamps. Replanning always requires individual review.

Execution atomically checks tenant, goal, operation, consent version, grant status, expiry and remaining uses. Users can pause, resume, revoke or use emergency stop. A transaction that commits before the stop takes effect has already created its tasks. Changed consent terms or scopes require a new grant. Legacy goal creation still offers its separate, explicit one-time task creation and scheduling option.

The graph exposes local task creation. Provider writes, financial operations, messaging and credential changes are outside its allowlist. Local undo requires individual confirmation.

JSON account export includes planning preferences, workflow results and grant records. CSV continues to export goals and tasks. Account deletion removes workflow rows, checkpoints and grants. Preferences can be reset separately. Workflow results remain until account deletion. Automated retention and per-run erasure remain open.

Existing Google OAuth still uses Calendar, Gmail and Drive read scopes. The graph does not retrieve provider content. Configure `INTEGRATION_TOKEN_KEY` to encrypt tokens written on connection, reconnection and refresh. Older plaintext rows remain readable during rollout. Full backfill, key rotation, narrower OAuth choices and provider-level revocation remain open. Store the key in the deployment secret manager and scrub OAuth callback query strings at access-log collection. [Fernet documentation](https://cryptography.io/en/latest/fernet/)

Workflow logs carry the run UUID, agent and outcome. Trace export excludes raw checkpoints, tokens and internal fingerprints. Protect database access, connections and backups.
