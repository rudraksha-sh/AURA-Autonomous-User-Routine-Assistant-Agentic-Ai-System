# Task 25 security audit

This audit covered the repository and disposable local environments. It excluded public deployment, live provider calls, load testing and exploitation.

## Findings and remediation

| Severity | Finding and evidence | Remediation and status |
| --- | --- | --- |
| CRITICAL | The npm baseline flagged Next.js 16.3.1 for several critical advisories, including two relevant to deployed runtime surfaces. [Windows server advisory](https://github.com/vercel/next.js/security/advisories/GHSA-p293-qw3h-jr36) and [image optimization advisory](https://github.com/vercel/next.js/security/advisories/GHSA-2464-fhr4-w9xw) | Updated to Next.js 16.4.6 and resolved the affected Sharp dependency. The fresh npm lockfile scan returned zero findings. |
| CRITICAL | The dependency scan flagged python-jose 3.4.0 for PYSEC-2026-4298 with no fix listed. AURA restricted verification to the configured algorithm and used an HMAC secret by default. Account compromise was not demonstrated. [PyPA advisory](https://github.com/pypa/advisory-database/blob/main/vulns/python-jose/PYSEC-2026-4298.yaml) | Replaced python-jose with PyJWT 2.15.1, kept the configured algorithm allowlist and required the expiry claim. The resolved Python scan returned zero findings. |
| HIGH | The Python baseline flagged old Starlette and multipart parser versions. The npm scan also flagged Sharp, Zod and tooling dependencies. [Starlette security advisories](https://github.com/Kludex/starlette/security/advisories) and [Zod advisory](https://github.com/advisories/GHSA-mrhx-c7xc-m3w5) | Updated the affected packages and related HTTP, cryptography and development dependencies against scanner remediation versions. FastAPI 0.165.0 and Starlette 1.10.0 resolved together. Python and npm rescans found zero known vulnerabilities in their respective scanned sets. |
| MEDIUM | Most API request bodies reached parsing without an application-wide byte ceiling. The rate limiter retained expired key buckets indefinitely. | Added a 6 MiB ASGI request ceiling for declared and streamed bodies. Expired rate-limit keys are pruned, and each limiter caps active keys without displacing live budgets. Verified with small boundary fixtures. |
| MEDIUM | Signed tokens without expiry could pass decoding. Production accepted arbitrary configured CORS strings, presented API schema docs, and lacked an explicit cache policy for token responses. | Require expiry, accept exact HTTPS CORS origins in production, disable credentialed CORS and production docs, and mark API/auth responses no-store. Verified production-shaped configuration locally. |
| MEDIUM | Validation log details could include caller-provided keys. Access logging filtered the canonical Google callback only, and the callback referrer policy still permitted same-origin forwarding. | Log route templates and error counts, strip access-log queries, and send no-referrer on OAuth callbacks. Frontend responses now disable framing and MIME sniffing. |
| LOW | The initial pattern scan flagged the OTP field, but Task 26.1 confirmed both historical assignments were empty. The candidate was a newline-matching false positive. | Production now requires a freshly generated, independent OTP pepper. Rotate any value known to have been exposed outside the scanned history. History was preserved. |
| INFORMATIONAL | The route inventory identified 91 handlers, with seven public account and recovery endpoints, the state-protected OAuth callback, and authorization dependencies on the other 83 handlers. | Inventory and selected ownership paths were reviewed. Existing regression tests exercise representative tenant boundaries across goals, tasks, workflows, context, memory, autonomy and external actions. |

## Verified controls and limits

- Authentication uses Argon2 password verification, purpose-scoped and expiring OTPs, and token-version and timestamp checks after logout and sensitive account changes. Tests cover rejection, expiry, session invalidation and replay across the supported test paths.
- Reviewed SQL use was parameterized or contained fixed application-owned DDL. Tenant ownership is enforced before resource reads and writes in inspected paths. React renders reviewed user text as text. Google and AI clients use fixed provider destinations. The application uses explicitly attached bearer tokens and OAuth state for the callback. Deployment-specific proxy, egress, forwarded headers, TLS and HSTS were not exercised.
- OAuth state is bounded, time-limited and consumed once. Tokens are encrypted with Fernet, service scopes are checked against read-only allowlists, and callback errors are sanitized. Historical live OAuth evidence is in Tasks 23.3 and 23.4. This audit used mocked providers.
- Workflow retrieval checks tenant, source and version, and provides references to the workflow. Deterministic planner inputs and explicit approval, grant and idempotency checks bound local tool execution. RAG poisoning and prompt-injection evidence is limited to the exercised paths.
- The separate assistant tool registry allows a fixed set of tenant-owned CRUD operations and checks idempotency. Its browser confirmation is a UX step. Workflow approvals and autonomy grants have independent server-side checks.
- Outbox transitions use revision guards, bounded retries and stale-lease recovery to an uncertain state. Recovery requires lookup before continuing. The live provider adapter registry is empty. Multi-process production supervision and provider-specific behavior were outside this audit.
- Secret scanning used local patterns over 274 tracked paths and 5,800 unique reachable Git blobs across 46 commits. Only paths and finding classes were emitted. The OTP field was the sole candidate and was cleared by the Task 26.1 line-scoped review. Ignored local secrets, unreachable Git objects, external logs and vendor-side key validity were excluded. Pattern scanning does not detect arbitrary secret formats.

## Residual release risks

- **MEDIUM** | Browser bearer tokens remain in local storage. Frame protection is in place, and a script-restricting site-wide CSP and browser token-storage migration remain unverified.
- **MEDIUM** | Production now requires PostgreSQL-backed OAuth state and rate limits. Verify hosted ingress limits, trusted edge behavior and database capacity before scaling.
- **LOW** | Production secret rotation, TLS/HSTS, monitoring and retention controls need infrastructure evidence. Verify fresh OTP pepper provisioning in the chosen environment.

## Local verification

- Focused security and affected route checks returned 37 passes in 5.31 s.
- The final disposable PostgreSQL run returned 208 passes, zero failures and zero skips in 101.70 s.
- The final full SQLite run returned 205 passes and three PostgreSQL-only skips in 68.01 s.
- The final Chromium run returned four passes in 32.7 s against the production frontend, mocked providers and disposable SQLite.
- Production-shaped FastAPI checks verified debug off, documentation routes returning 404, exact CORS origin behavior and OAuth callback no-referrer and no-store. The Next.js production manifest verified framing, MIME and callback referrer headers.
- ESLint, TypeScript, the Next.js production build and git diff --check passed. The scans used the npm lockfile and a separately resolved Python development dependency target. Optional dependencies outside the declared Python requirements require their own deployment scan.
## Task 26.2 distributed controls

| Severity | Evidence | Remaining gate |
| --- | --- | --- |
| MEDIUM | PostgreSQL rolling limits share one admission budget across API replicas. The database clock, per-policy transaction lock, expiry and size bounds apply to each keyed bucket. Verified with concurrent contenders. | Measure lock contention and database connection headroom at expected hosted traffic. |
| MEDIUM | PostgreSQL OAuth states are stored as digests, bind owner and requested scopes, expire after ten minutes and are consumed via conditional DELETE RETURNING. Concurrent use admitted one consumer. Replica switch and restart were exercised locally without provider traffic. | Verify the hosted edge supplies an authenticated client IP and strips caller-supplied identity headers. Confirm provider-edge logging redacts callback queries before live staging OAuth. |
| LOW | Local HTTPS Next.js forwarding and API ingress rejection were exercised with synthetic inputs. The private proxy requires the shared credential and disables Uvicorn forwarded-header trust. PostgreSQL failure responses are sanitized and fail closed. | Verify hosted TLS/HSTS, external ingress bounds, private DB TLS, outage behavior, alert delivery and restore objectives. |
## Task 26.3B.3 secret scan

The modified/untracked release candidate scan examined 4,424 candidate files with path-only output. Two pattern matches require review: a private-key marker occurred in ignored Node compile-cache data, and a generic credential assignment pattern matched the Google credentials implementation. The latter is a detector false-positive candidate, not confirmation of an exposed credential. A follow-up content review is required before staging. Reachable history scan examined 6,905 unique blobs and produced nine generic assignment matches, including historical application source and vendored Python package paths. The generic detector matched names/patterns rather than confirmed secrets; no values were emitted. This scan is heuristic and does not establish that arbitrary secret formats are absent.


## Task 26.3B.3a release integrity review

Reviewed all 11 matches from the prior heuristic scan. Two were current-tree candidates: (1) ignored `.aura-test-temp/node-compile-cache/v24.6.0-x64-ef5a0af0/1ee5b179`, an untracked V8 cache file whose 66-byte PEM-like fragment contains only begin/end markers and fails private-key parsing; classified false positive/cache artifact, excluded by `.gitignore`; (2) `backend/app/integrations/google/credentials.py`, line 48, where the generic assignment detector matches the `client_secret` field receiving the configured `settings.google_client_secret`; classified false positive/source code, not a literal credential. The source working-tree blob ID is `928a8779b68cfabb87bd462aa1ac4247bf5a8dbb`.

Nine reachable-history matches were also reviewed by blob and path. `c957b2220110a32cdb95f94e8675a31dc42a8cc2`, `a0aa7865ce5e2068456aa77896f8dda7da4bacfc`, `0818820865d4ead6accfa2dab322c44c19607d79`, and `266ec831bc44335fd2c1a98f2ad5549d7122f950` are `backend/app/agents/planner/service.py` generic matches on source assignments; `0751a2d0915d0ce2a61a1206ad2f54cd7fef604f` is the corresponding historical `.before_ai_integration.bak` source backup; `3e62878a9ac8c4597d75419cdaa6c74c0ea98722` and `898b321eebad4c2dbd0706dc124e3006614a143c` match Google credential source assignments; `1cadc143742332d4cb7d45c629317f89e55b92ec` and `16449d6ff719398267e117eaf5095c91fd0e51e1` are generic matches in vendored pip and Python urllib authentication code. These are false-positive source/vendor patterns, not confirmed secrets. No confirmed secret was found in these 11 findings; no rotation is indicated by this scan. History was not rewritten.

The deleted root `test.py` contains only `print("clone working")`; repository search found no imports or references. It is an unrelated clone-check artifact, but its deletion is not justified by the release task. It remains deleted in the working tree and is excluded from the release manifest and proposed commits pending owner decision; it was neither restored nor deleted by this review.

The targeted scan of newly changed candidate files found no additional secret pattern beyond the previously reviewed Google source assignment. Scan limits remain: regex patterns do not establish absence of arbitrary credentials, unreachable objects, ignored files beyond explicitly reviewed matches, or externally issued keys.


Final manifest verification: targeted scan of the 146 proposed release paths produced one repeat hit, the reviewed `client_secret` configuration assignment in `backend/app/integrations/google/credentials.py`; no additional pattern class or file was found. `git diff --check` passed (Git emitted only line-ending normalization notices). The manifest matches all 146 proposed paths exactly. Worktree inventory is 147 changed paths: 80 modified, 6 deleted, 61 untracked; the deleted `test.py` is excluded. Proposed files include the four Alembic revisions, `backend/requirements.txt`, `backend/requirements-dev.txt`, `backend/requirements.production.lock`, and `render.yaml`. The only secret-like data reviewed in ignored local artifacts was the non-key PEM marker fragment described above; ignored envs, TLS fixture keys, benchmark outputs, database/profile artifacts and caches remain excluded by ignore rules and are not in the manifest.


## Task 26.3B.4 final verification

No security architecture changed. Full PostgreSQL regression passed 217/0/0 and SQLite passed 212 with five PostgreSQL-only skips. A live, disposable `aura_runtime` smoke verified registration, console-captured verification code, login, goal/plan creation, workflow approval/execution, and listing on `aura_fresh` at loopback port 25433. AI was disabled, email was console-only, and no Google/provider calls were made. The missing trusted-ingress identity probe returned 503; ingress was not weakened. The prior OAuth, TLS and secret-history evidence remains unchanged.

Resource limits did show a capacity concern rather than a security defect: PostgreSQL cgroup peak 202.8 MiB on a 256 MiB limit, 20.8% headroom, and 90.8% throttled CPU periods at 0.1 CPU during the successful 10-user sample. Upgrade/re-profile before staging. cgroup OOM-kill deltas were zero. Hosted TLS certificate validation, trusted edge identity, alert delivery, managed restore and secret rotation remain staging gates.
