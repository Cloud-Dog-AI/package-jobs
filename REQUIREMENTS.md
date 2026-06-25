# platform-jobs — Requirements

**Package:** `cloud_dog_jobs`  
**Version:** 0.2.0 (pre-release)  
**Standard:** PS-75 (Job & Queue Management)  
**Status:** Draft

---

## Scope / Vision

### SV1.1
The package SHALL provide a single, reusable job/queue management library for all Cloud-Dog Python services, implementing PS-75.

### SV1.2
The package SHALL support pluggable queue backends, safe multi-worker execution, concurrency controls, retry/backoff/cancellation, progress tracking, state machines, admin tooling, async completion, and full audit/observability.

### SV1.3
The package SHALL be compatible with existing project implementations (expert-agent Redis+SQL queue, sql-agent in-memory job manager, notification-agent delivery worker) and provide a clean migration path.

---

## Business Objectives

### BO1.1
Eliminate per-project job/queue reimplementation — centralise queue backends, worker logic, retry policies, and admin tooling.

### BO1.2
Enable consistent job tracking and observability across all services — same status model, same audit events, same metrics.

### BO1.3
Support progressive adoption: services can start with in-memory/SQL backend and add Redis, concurrency controls, and fan-out incrementally.

---

## Functional Requirements

### FR1.1 — Queue Backend Interface
The package MUST define an abstract `QueueBackend` interface:
- `enqueue(job_request) -> job_id`
- `dequeue(limit, job_type?) -> list[Job]`
- `claim(job_id, host_id, worker_id) -> bool`
- `release(job_id) -> bool`
- `heartbeat(job_id) -> bool`
- `get_queue_status() -> QueueStatus`
- `health_check() -> bool`

### FR1.2 — SQL Backend (Default)
The package MUST provide a SQL backend:
- SQLAlchemy models + Alembic migrations.
- Atomic claim: `SELECT ... FOR UPDATE SKIP LOCKED` or optimistic locking with version column.
- Indexes for queue scanning and admin queries.
- Compatible with PostgreSQL, MySQL/MariaDB, SQLite.

### FR1.3 — Redis/Valkey Backend (Optional)
The package MUST provide a Redis/Valkey backend:
- Sorted sets for priority queue (`zadd`/`zrevrange` as per expert-agent).
- Coordination store for claims and heartbeats.
- Durable job state persisted to SQL or configurable durability policy.
- Recovery strategy if Redis flushed/restarted.
- Graceful fallback to SQL if Redis unavailable.

### FR1.4 — Hybrid Backend (Recommended)
The package MUST provide a hybrid mode: Redis/Valkey for fast queue ops, SQL for source-of-truth.

### FR1.5 — In-Memory Backend (Testing/Simple)
The package MUST provide an in-memory backend:
- Thread-safe queue with priority support.
- Optional DB persistence for history (as per sql-agent `JobManager`).
- Suitable for single-server deployments and testing.

### FR1.6 — Custom / Extension Backends
Any additional backend MUST be pluggable via the `QueueBackend` interface without changing the domain API.

### FR1.7 — Job Model
The package MUST define a canonical `Job` model with all fields from PS-75 JQ3:
- `job_id`, `app_id`, `tenant_id`, `host_id`, `worker_id`, `queue_name`, `job_type`, `priority`
- `payload` (JSON, size-limited), `idempotency_key`, `correlation_id`, `user_id`, `session_id`, `channel_id`
- `callback_url`, `callback_method`, `callback_headers`
- Request metadata: `request_source`, `request_ip`, `request_auth_method`, `request_auth_identity`, `request_user_agent`
- All timestamps (RFC3339 UTC).

### FR1.8 — State Machine
The package MUST provide a configurable state machine:
- Default states: `queued`, `scheduled`, `running`, `succeeded`, `failed`, `retry_wait`, `cancelled`, `paused`, `timeout`.
- `can_transition_to(target) -> bool` validation.
- `is_terminal() -> bool`, `is_retryable() -> bool`.
- Support for domain-specific state extensions (as per notification-agent `DeliveryState`).
- All transitions MUST be enforced; invalid transitions rejected.

### FR1.9 — Handler Registry
The package MUST provide a handler registration mechanism:
- `Worker.register_handler(job_type, handler)`.
- Handlers receive `JobContext` with: job metadata, cancellation token, progress reporter, dependency injection hooks.
- Unknown `job_type` MUST be rejected with a clear error.

### FR1.10 — Worker Engine
The package MUST provide a worker with:
- Poll/subscribe loop for eligible jobs.
- Atomic claim (single-claim semantics).
- Handler execution with cancellation and timeout support.
- Periodic heartbeat updates while running.
- Final status write with result/error (redacted).
- `run_once()` and `run_forever()` modes.

### FR1.11 — Cooperative Cancellation
The package MUST support cooperative cancellation:
- Cancellation flag on `JobContext` (`ctx.is_cancelled()`, `ctx.check_cancellation()`).
- Handlers check at safe points.
- Cancel pending jobs by removing from queue.
- Cancel running jobs by setting flag + marking cancelled after timeout.

### FR1.12 — Pause/Resume
The package SHOULD support pause/resume for long-running operations:
- `pause_task()` blocks handler at next checkpoint.
- `resume_task()` unblocks.
- `stop_task(immediate)` for graceful or forced stop.

### FR1.13 — Concurrency Limits
The package MUST support:
- Global max concurrent jobs per queue.
- Per-job-type limits.
- Per-tenant/namespace limits (recommended).
- Per-user session limits (as per expert-agent `ConcurrencyManager`).
- Enforcement across multiple workers/servers.

### FR1.14 — Priority Dispatch
The package MUST support priority-based dispatch:
- Numeric priority (higher = more important, default 0).
- Named levels: `LOW`, `NORMAL`, `HIGH`, `URGENT`.
- Priority ordering in Redis (sorted sets) and SQL (`ORDER BY priority DESC, next_run_at ASC`).

### FR1.15 — Retry Policy
The package MUST support:
- Max attempts (configurable per job type and per job).
- Retryable error classification (`is_transient` flag).
- Exponential backoff + jitter: `min(base * 2^attempt, max) + random(0, backoff*0.1)`.
- Optional fixed backoff.
- Transition to `retry_wait` with computed `next_run_at`.

### FR1.16 — Stuck Job Detection and Recovery
The package MUST support:
- Stuck definition: `running` + `last_heartbeat_at` older than `claim_timeout_ms`.
- Multi-tier detection (early crash + long stuck, as per notification-agent).
- Recovery actions: mark failed, reschedule, force-cancel, quarantine.
- Automated maintenance sweep (configurable interval).

### FR1.17 — TTL and Expiry
The package MUST support:
- Per-job TTL from creation.
- Default TTL per queue/job_type.
- Expiry handling: transition to `ttl_expired`, cancel pending sub-jobs.
- Result retention policy by status with configurable age limits.
- Safe purge of expired rows and blobs.

### FR1.18 — Idempotency
The package MUST support `idempotency_key`:
- Same key within configurable window returns existing `job_id` (no duplicate submission).
- Key indexed for fast lookup.

### FR1.19 — Progress Tracking
The package MUST support:
- `update_progress(percentage, stage, counters, current_item, estimated_completion)`.
- `get_progress(job_id) -> Progress`.
- Long-running operation tracking with operation types.

### FR1.20 — Admin CRUD
The package MUST provide:
- `submit_job`, `get_job`, `list_jobs` (with filters + paging), `update_job`, `delete_job`.
- `cancel_job`, `reschedule_job`, `retry_now`, `resubmit_job`.
- `clear_old_jobs(policy)`, `clear_stuck_jobs(filter, action)`.
- `reassign_queue`, `bulk_update(filter, action)`.
- `get_queue_status()` with counts by status and Redis queue sizes.
- RBAC enforcement on all admin operations (PS-70).

### FR1.21 — Callback Webhooks
The package MUST support:
- Register callback URL + method + headers per job.
- Trigger callback on completion (succeeded/failed).
- Retry callback delivery on failure (bounded retries, backoff).
- Unregister callback.

### FR1.22 — MCP Async Job Mode
The package MUST support:
- `wait=false` immediate `job_id` return.
- Poll `/jobs/{job_id}` for status/result.
- Return result when completed.

### FR1.23 — Message Fan-Out
The package SHOULD support:
- Parent job with multiple child sub-jobs/deliveries.
- Parent status aggregated from child statuses.

### FR1.24 — Confirmation Polling
The package SHOULD support:
- Poll external provider APIs for delivery status.
- Configurable polling interval, max poll age cutoff.
- Per-delivery poll tracking.

### FR1.25 — Scheduler / Dispatcher
The package MUST provide:
- Select eligible jobs respecting concurrency limits and priority.
- Scheduled jobs (future `next_run_at`).
- Fairness across tenants and job types (recommended).

### FR1.26 — Maintenance Reaper
The package MUST provide automated maintenance:
- Retention purge (age-based, status-based).
- Stuck detection sweeps.
- TTL expiry processing.
- Configurable interval via config system.

### FR1.27 — FastAPI Integration (Optional)
The package SHOULD provide a FastAPI router for admin + job endpoints:
- `GET /jobs`, `GET /jobs/{job_id}`, `DELETE /jobs/{job_id}`, `POST /jobs/{job_id}/resubmit`, `POST /jobs/{job_id}/stop`
- `GET /jobs/queue/status`
- RBAC middleware integration.

### FR1.28 — LLM Call Logging (Optional)
The package SHOULD support per-job LLM call logging:
- Provider, model, input/output tokens, latency, cost.

---

## Observability Requirements (PS-40 Alignment)

### OB1.1 — Audit Events (PS-40 L3)
The package MUST emit audit events (JSON Lines, append-only) for:
- `job.submit`, `job.claim`, `job.transition` (with `from_state`, `to_state`)
- `job.cancel`, `job.reschedule`, `job.resubmit`
- `job.admin.bulk_update`, `job.admin.purge`, `job.admin.stuck_recovery`
- `job.callback.trigger`

Each audit event MUST include: `timestamp` (UTC), `service`, `service_instance`, `environment`, `event_type=system_function`, `action`, `outcome`, `severity`, `trace_id`, `request_id`, `actor`, `target` (per PS-40 L3 schema).

### OB1.2 — Application Logging (PS-40 L2/L4)
- JSON Lines format, UTC ISO8601 timestamps.
- Correlation IDs (`trace_id`, `request_id`) on all log events.
- NEVER log secrets.
- Levels: INFO (lifecycle), WARNING (retries/degraded), ERROR (failures), DEBUG (claims/heartbeats).

### OB1.3 — Metrics Hooks
Expose counters/hooks for: jobs submitted/started/succeeded/failed/cancelled/timed_out, queue depth, latency, retry counts, stuck counts, worker utilisation, callback success/failure.

### OB1.4 — OpenTelemetry
The package SHOULD support OpenTelemetry tracing hooks for job lifecycle spans.

---

## Security Requirements (PS-70/PS-90 Alignment)

### CS1.1
Admin operations MUST require RBAC permissions (PS-70).

### CS1.2
Payloads MUST be validated and size-limited.

### CS1.3
Secrets MUST NEVER be embedded in job payloads. Credential fields (Redis password, database URI, callback auth headers) MUST arrive pre-resolved by `cloud_dog_config` (PS-80). This package MUST NOT read `os.environ` for credentials, import `hvac`, navigate Vault JSON, or implement its own secret resolution logic.

### CS1.4
Secrets MUST NEVER appear in logs, audit events, or error messages.

### CS1.5
Worker identities/hosts MUST be authenticated/authorised in multi-server mode.

### CS1.6
Callback URLs MUST be validated (allow-list or domain restrictions).

### CS1.7
Request metadata (source, IP, auth) SHOULD be captured on submission.

---

## Testing Requirements (PS-95 Alignment)

### TS1.1
Tests MUST follow PS-95: UT/ST/IT/AT/QT hierarchy. Folder naming: `{TYPE}{NUMBER}_{DescriptiveName}`.

### TS1.2
`--env` mandatory; ZERO hardcoded values; tests MUST fail without `--env`.

### TS1.3
Conformance tests required for: atomic claim concurrency, concurrency limits, retry/backoff, timeout/stuck detection, state machine enforcement, admin operations, TTL/retention, Redis/SQL parity, callbacks, audit events, idempotency.

### TS1.4
ALL source files: header blocks. ALL functions: documentation. UK English throughout.

### TS1.5
`TESTS.md` with traceability to requirements and architecture. Results recorded and tracked.

### R-JOBS-IT-01
Integration-tier tests (IT/AT/QT) MUST fail explicitly when required real backends or Vault credentials are unavailable. `pytest.skip()` is forbidden for mandatory backend preconditions.

### R-JOBS-IT-02
Integration-tier tests MUST execute against real backends only (SQL/Redis). Tests using local-only adapters, mocks, or stubs MUST be classified as UT/ST instead of IT/AT.

### R-JOBS-IT-03
The package MUST provide and consume `tests/env-UT`, `tests/env-ST`, `tests/env-IT`, and `tests/env-AT` via mandatory `--env <file>` test execution. Runs without `--env` MUST fail.

---

## Configuration Requirements (PS-80 Alignment)

### CF1.1
All settings via config system: `jobs.*`, `redis.*`, `queue.*`.

### CF1.2
Required config keys (never hardcoded):
- `jobs.backend` (`sql`/`redis`/`hybrid`/`memory`)
- `jobs.default_max_attempts`, `jobs.default_run_timeout_ms`, `jobs.default_claim_timeout_ms`
- `jobs.default_priority`, `jobs.default_ttl_seconds`
- `jobs.concurrency.global_max`, `jobs.concurrency.per_type.*`
- `jobs.retry.base_backoff_ms`, `jobs.retry.max_backoff_ms`, `jobs.retry.jitter_factor`
- `jobs.maintenance.sweep_interval_seconds`, `jobs.maintenance.retention.*`
- `redis.host`, `redis.port`, `redis.db`, `redis.username`, `redis.password`, `redis.socket_connect_timeout_seconds`

### FR1.33 — Durable Callback Registry
The package MUST provide a durable callback registry for job completion notifications:
- `register_callback(job_id, callback_url, headers=None, retry_policy=None)` — persist callback config.
- Callbacks executed after job completes (success or failure).
- Delivery is at-least-once with configurable retry.
- Callback payload includes: `job_id`, `status`, `result_summary`, `duration_ms`.
- Failed callback deliveries logged and retried per policy.
- **Source**: expert-agent (durable callback registry abstraction).

### FR1.34 — Fan-Out Job Pattern
The package MUST provide a reference fan-out pattern:
- `create_fan_out(parent_job_id, child_specs: list[JobSpec])` — creates child jobs linked to parent.
- Parent status aggregated from children (all success → parent success; any failure → parent failed).
- Optional: partial success mode (configurable threshold).
- Child jobs execute independently with standard concurrency controls.
- **Source**: foresight (parallel processing patterns used by sql-agent, expert-agent).

### FR1.35 — Explicit Fallback Policies
The package MUST support explicit fallback policy configuration per job type:
- `fallback_action`: `retry` (default), `dead_letter`, `notify`, `ignore`.
- `dead_letter_queue` — configurable destination for permanently failed jobs.
- `notify_url` — webhook to call on permanent failure.
- **Source**: expert-agent (explicit fallback policy controls).

### FR1.36 — Domain State-Machine Extension
The package MUST support domain-specific state-machine extensions:
- `register_state_extension(job_type, custom_states, custom_transitions)` — extend the base state machine with domain states.
- Domain states coexist with base states (pending, running, completed, failed, cancelled).
- Domain transitions validated against the extended state machine.
- Use case: sql-agent has domain-specific job states; notification-agent has delivery states.
- **Sources**: sql-agent (bespoke job lifecycle), notification-agent (delivery state machine).

### FR1.37 — MCP Job Adapter
The package SHOULD provide an adapter for exposing job operations via MCP:
- `create_job_tools(job_manager)` — returns MCP tool definitions for create, status, cancel, list.
- Integrates with `cloud_dog_api_kit` MCP gateway (FR18.1).
- **Source**: chat-client (MCP client-facing adapter guidance).

---

## Non-Functional Requirements

### NF1.1
Runtime deps: `sqlalchemy` (SQL backend). Optional: `redis`, `alembic`, `httpx` (callbacks), `opentelemetry-api`.

### NF1.2
Queue operations (excluding network I/O) MUST add < 5ms overhead.

### NF1.3
All public APIs MUST have async variants.

### NF1.4
Python 3.10+.

---

## Acceptance Criteria

A project is compliant when:
- All background work goes through `cloud_dog_jobs`.
- Workers enforce concurrency, retries, timeouts.
- Multi-server workers safely share the queue.
- Admin tooling can list, cancel, resubmit, clear, recover.
- Audit events emitted for all operations (PS-40).
- Structured logs with correlation IDs, no secrets (PS-40).
- RBAC protects admin operations (PS-70).
- All config from config system (PS-80).
- No direct `os.environ`, `hvac`, or Vault reads for credentials — all config via `cloud_dog_config` (PS-80).
- Tests follow PS-95; conformance suite passes.
