# platform-jobs — Architecture

**Package:** `cloud_dog_jobs`  
**Version:** 0.2.0 (pre-release)  
**Standard:** PS-75 (Job & Queue Management)  
**Status:** Draft

---

## OV1 — Overview

`cloud_dog_jobs` is a drop-in Python library that implements the PS-75 job/queue management standard. It provides pluggable queue backends (SQL, Redis/Valkey, hybrid, in-memory), safe multi-worker execution, concurrency controls, retry/backoff/cancellation, progress tracking, configurable state machines, admin tooling, async completion patterns, callback webhooks, and full audit/observability — all behind stable, framework-agnostic interfaces.

### Design Goals

- **Ports-and-adapters**: domain logic is backend-agnostic; SQL, Redis, hybrid, in-memory are pluggable backends.
- **Single module per project**: all background work routes through `cloud_dog_jobs`.
- **Multi-server safe**: atomic claims, heartbeats, distributed concurrency enforcement.
- **Progressive adoption**: start with in-memory/SQL; add Redis, concurrency, fan-out incrementally.
- **Full audit trail**: every job operation emits audit events (PS-40 L3).
- **Async-first**: all public APIs have async variants; sync wrappers optional.
- **Compatible with existing projects**: clean migration from expert-agent (Redis+SQL), sql-agent (in-memory+DB), notification-agent (delivery worker+state machine).

---

## SA1 — Module Layout

```
cloud_dog_jobs/
  __init__.py                          # Public API: JobQueue, Worker, get_job_queue
  config/
    models.py                          # Pydantic settings (backend, limits, retry, maintenance)
  domain/
    models.py                          # Job, JobRequest, JobResult, JobContext, Progress
    errors.py                          # Portable error taxonomy
    enums.py                           # JobStatus, QueuePriority, OperationType
    state_machine.py                   # Configurable state machine with transition rules
  backends/
    base.py                            # QueueBackend interface (ABC)
    sql_backend.py                     # Default SQL backend (SQLAlchemy)
    redis_backend.py                   # Redis/Valkey backend (sorted sets)
    hybrid_backend.py                  # Hybrid: Redis queue + SQL state
    memory_backend.py                  # In-memory backend (threading)
    registry.py                        # Backend registry (configure active backend)
  storage/
    sqlalchemy/
      models.py                        # jobs table, job_call_logs, job_deliveries, job_callbacks
      repo.py                          # Atomic claim/update queries (FOR UPDATE SKIP LOCKED)
      migrations/                      # Alembic migrations
  scheduler/
    dispatcher.py                      # Select eligible jobs: priority, concurrency, fairness
    policies.py                        # Backoff, retry, fairness policies
    concurrency.py                     # Concurrency limit enforcement (global/type/tenant/user)
  worker/
    worker.py                          # Run loop: poll, claim, execute, heartbeat, finalise
    handlers.py                        # Handler registry (job_type -> handler)
    context.py                         # JobContext: cancellation, progress, DI hooks
    heartbeat.py                       # Heartbeat manager (periodic updates)
    pause.py                           # Pause/resume/stop controls
  admin/
    service.py                         # Admin CRUD + operational actions
    bulk.py                            # Bulk operations (filter + action)
  callbacks/
    manager.py                         # Webhook callback registration, trigger, retry
  async_jobs/
    mcp_adapter.py                     # MCP wait=false pattern: submit -> poll -> result
  fanout/
    manager.py                         # Parent/child job fan-out, status aggregation
  polling/
    poller.py                          # External provider status polling
  ttl/
    expiry.py                          # TTL processing, expiry transitions
    retention.py                       # Retention policies, safe purge
  maintenance/
    reaper.py                          # Automated: stuck detection, TTL, retention sweeps
  idempotency/
    manager.py                         # Idempotency key tracking, deduplication
  observability/
    audit.py                           # Audit event emitters (PS-40 L3 schema)
    metrics.py                         # Metrics hooks/counters
    otel.py                            # OpenTelemetry tracing integration
    logging.py                         # Structured logging helpers (PS-40 L2/L4)
  security/
    rbac.py                            # RBAC integration hooks (PS-70)
    secrets.py                         # Secret resolution for callbacks/webhooks
  extensions/
    state_extensions.py                # Domain state-machine extensions (FR1.36)
    fallback_policies.py               # Explicit fallback policy config (FR1.35)
  mcp/
    job_tools.py                       # MCP tool definitions for job ops (FR1.37)
    validation.py                      # Payload validation, size limits
    secrets.py                         # Secret exclusion checks
  api/
    fastapi/
      router.py                        # Optional admin + job REST endpoints
      middleware.py                     # RBAC middleware for FastAPI
  testing/
    conformance.py                     # Multi-worker claim tests, retry/timeout tests
    fixtures.py                        # Shared test fixtures (mock backends, test jobs)
    mock_backends.py                   # Mock queue backends for unit testing
```

---

## SA2 — Component Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                     Service (FastAPI / Agent / CLI)                   │
│                                                                      │
│  JobQueue.submit() / Worker.run_forever() / AdminService.*()         │
│         │                                                            │
│         ▼                                                            │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │                  JobQueue (main entry)                     │       │
│  │                                                           │       │
│  │  domain/state_machine.py ──→ enforce transitions          │       │
│  │  idempotency/manager.py ──→ deduplicate submissions       │       │
│  │  observability/audit.py ──→ emit audit events             │       │
│  │         │                                                 │       │
│  │         ▼                                                 │       │
│  │  ┌─────────────────────────────────────────────────┐     │       │
│  │  │           backends/registry.py                   │     │       │
│  │  │  Active backend: sql | redis | hybrid | memory   │     │       │
│  │  │         │                                        │     │       │
│  │  │         ├──→ sql_backend.py ──→ SQLAlchemy       │     │       │
│  │  │         ├──→ redis_backend.py ──→ redis.asyncio  │     │       │
│  │  │         ├──→ hybrid_backend.py ──→ Redis + SQL   │     │       │
│  │  │         └──→ memory_backend.py ──→ threading     │     │       │
│  │  └─────────────────────────────────────────────────┘     │       │
│  └──────────────────────────────────────────────────────────┘       │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │              Worker Engine                                │       │
│  │                                                           │       │
│  │  1. scheduler/dispatcher.py ──→ select eligible jobs      │       │
│  │  2. backends/ ──→ atomic claim                            │       │
│  │  3. worker/handlers.py ──→ dispatch to registered handler │       │
│  │  4. worker/context.py ──→ JobContext (cancel, progress)   │       │
│  │  5. worker/heartbeat.py ──→ periodic heartbeats           │       │
│  │  6. domain/state_machine.py ──→ final status transition   │       │
│  │  7. callbacks/manager.py ──→ trigger webhooks             │       │
│  │  8. observability/audit.py ──→ emit events                │       │
│  │                                                           │       │
│  │  scheduler/concurrency.py ──→ enforce limits              │       │
│  │  scheduler/policies.py ──→ backoff, retry                 │       │
│  └──────────────────────────────────────────────────────────┘       │
│                                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │ admin/      │  │ ttl/        │  │ fanout/     │                 │
│  │ service.py  │  │ expiry.py   │  │ manager.py  │                 │
│  │ bulk.py     │  │ retention   │  │ aggregation │                 │
│  └─────────────┘  └─────────────┘  └─────────────┘                 │
│                                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │ callbacks/  │  │ async_jobs/ │  │ polling/    │                 │
│  │ manager.py  │  │ mcp_adapter │  │ poller.py   │                 │
│  └─────────────┘  └─────────────┘  └─────────────┘                 │
│                                                                      │
│  ┌────────────────────────────────────────────────────────┐         │
│  │ maintenance/reaper.py                                   │         │
│  │  Sweeps: stuck detection, TTL expiry, retention purge   │         │
│  └────────────────────────────────────────────────────────┘         │
│                                                                      │
│  ┌────────────────────────────────────────────────────────┐         │
│  │ observability/                                          │         │
│  │  audit.py ← metrics.py ← otel.py ← logging.py          │         │
│  └────────────────────────────────────────────────────────┘         │
└──────────────────────────────────────────────────────────────────────┘
```

---

## CC1 — Core Components

### CC1.1 JobQueue (Main Entry Point)

```python
class JobQueue:
    def __init__(self, config, backend: QueueBackend): ...
    
    async def submit(self, request: JobRequest) -> str: ...
    async def get(self, job_id: str) -> Job: ...
    async def list(self, filters: JobFilter, paging: Paging) -> Page[Job]: ...
    async def cancel(self, job_id: str) -> bool: ...
    async def get_queue_status(self) -> QueueStatus: ...
    async def health(self) -> bool: ...
```

Orchestrates: idempotency check → backend enqueue → audit event → callback registration.

### CC1.2 QueueBackend Interface (`backends/base.py`)

```python
class QueueBackend(ABC):
    @abstractmethod
    async def enqueue(self, job: Job) -> str: ...
    @abstractmethod
    async def dequeue(self, limit: int, job_type: str = None) -> list[Job]: ...
    @abstractmethod
    async def claim(self, job_id: str, host_id: str, worker_id: str) -> bool: ...
    @abstractmethod
    async def release(self, job_id: str) -> bool: ...
    @abstractmethod
    async def heartbeat(self, job_id: str) -> bool: ...
    @abstractmethod
    async def update_status(self, job_id: str, status: str, **fields) -> bool: ...
    @abstractmethod
    async def get_queue_status(self) -> QueueStatus: ...
    @abstractmethod
    async def health_check(self) -> bool: ...
```

### CC1.3 SQL Backend (`backends/sql_backend.py`)

- SQLAlchemy async session.
- Atomic claim: `SELECT ... FOR UPDATE SKIP LOCKED` (PostgreSQL/MySQL) or `WHERE version=N` (optimistic).
- Priority ordering: `ORDER BY priority DESC, next_run_at ASC`.
- Compatible with existing expert-agent `JobManager` + `QueueManager`.

### CC1.4 Redis Backend (`backends/redis_backend.py`)

- `redis.asyncio` client.
- Sorted sets (`ZADD`/`ZREVRANGE`) for priority queue.
- Claim via `ZREM` (atomic pop).
- Heartbeat via Redis hash or key TTL.
- Graceful fallback to SQL if Redis unavailable (as per expert-agent).

### CC1.5 State Machine (`domain/state_machine.py`)

```python
class JobStateMachine:
    def __init__(self, transitions: dict[str, set[str]]): ...
    def can_transition(self, from_state: str, to_state: str) -> bool: ...
    def transition(self, job: Job, to_state: str) -> Job: ...  # raises on invalid
    def is_terminal(self, state: str) -> bool: ...
    def is_retryable(self, state: str) -> bool: ...
```

Default transitions (extensible per PS-75 JQ4). Projects can register domain-specific states (notification-agent `DeliveryState` pattern).

### CC1.6 Worker (`worker/worker.py`)

```python
class Worker:
    def __init__(self, queue: JobQueue, backend: QueueBackend): ...
    
    def register_handler(self, job_type: str, handler: JobHandler): ...
    async def run_once(self) -> Optional[JobResult]: ...
    async def run_forever(self, poll_interval: float = 1.0): ...
    async def stop(self, graceful: bool = True): ...
```

Poll loop: dequeue → claim → heartbeat task → handler(ctx) → finalize → callbacks → audit.

### CC1.7 JobContext (`worker/context.py`)

```python
class JobContext:
    job: Job
    
    def is_cancelled(self) -> bool: ...
    def check_cancellation(self) -> None: ...  # raises CancelledError
    async def update_progress(self, percentage, stage, counters, current_item): ...
    
    # Dependency injection
    db: Session
    config: Any
    logger: Logger  # pre-bound with correlation_id, job_id
```

### CC1.8 Scheduler / Dispatcher (`scheduler/dispatcher.py`)

```python
class Dispatcher:
    async def select_eligible(self, limit: int) -> list[Job]: ...
```

Selects jobs respecting: priority, concurrency limits (global/type/tenant/user), fairness, scheduled time.

### CC1.9 Admin Service (`admin/service.py`)

```python
class AdminService:
    async def cancel(self, job_id: str) -> bool: ...
    async def reschedule(self, job_id: str, next_run_at: datetime) -> bool: ...
    async def retry_now(self, job_id: str) -> bool: ...
    async def resubmit(self, job_id: str) -> str: ...
    async def clear_old_jobs(self, policy: RetentionPolicy) -> int: ...
    async def clear_stuck_jobs(self, filter: JobFilter, action: str) -> int: ...
    async def bulk_update(self, filter: JobFilter, action: str) -> int: ...
```

All operations: RBAC check → execute → audit event.

### CC1.10 Callback Manager (`callbacks/manager.py`)

```python
class CallbackManager:
    def register(self, job_id: str, url: str, method: str, headers: dict): ...
    async def trigger(self, job_id: str, status: str, result: dict) -> bool: ...
    def unregister(self, job_id: str) -> bool: ...
```

Retry on failure (bounded retries, backoff). Compatible with expert-agent `CallbackManager`.

### CC1.11 MCP Async Adapter (`async_jobs/mcp_adapter.py`)

```python
class MCPAsyncJobAdapter:
    async def submit_async(self, tool_name: str, arguments: dict) -> str: ...  # returns job_id
    async def get_result(self, job_id: str) -> dict: ...  # poll for result
```

Compatible with expert-agent MCP `wait=false` → `/jobs/{job_id}` pattern.

### CC1.12 Maintenance Reaper (`maintenance/reaper.py`)

```python
class MaintenanceReaper:
    async def run_sweep(self) -> MaintenanceSummary: ...
    async def run_forever(self, interval_seconds: float): ...
```

Sweeps: stuck detection → TTL expiry → retention purge. All actions audited.

### CC1.13 Audit Emitter (`observability/audit.py`)

```python
class JobAuditEmitter:
    def job_submitted(self, job: Job, actor: Actor): ...
    def job_claimed(self, job: Job, host_id: str, worker_id: str): ...
    def job_transitioned(self, job: Job, from_state: str, to_state: str): ...
    def job_cancelled(self, job: Job, actor: Actor, reason: str): ...
    def admin_action(self, action: str, actor: Actor, target_ids: list, outcome: str): ...
```

All events follow PS-40 L3 schema: `timestamp`, `service`, `event_type=system_function`, `action`, `outcome`, `actor`, `target`, `trace_id`, `request_id`.

---

## DM1 — Data Model

### Persistent (SQLAlchemy)

| Table | Purpose | Key fields |
|-------|---------|-----------|
| `jobs` | Job records | See PS-75 JQ18 schema |
| `job_call_logs` | LLM call tracking per job | job_id, provider, model, tokens, latency, cost |
| `job_deliveries` | Child deliveries for fan-out | parent_job_id, delivery_id, state, channel_id |

### In-Memory / Transient

| Object | Purpose |
|--------|---------|
| `Job` | Canonical job with all metadata |
| `JobRequest` | Submission request |
| `JobResult` | Handler result |
| `JobContext` | Handler execution context |
| `Progress` | Progress tracking |
| `QueueStatus` | Queue depth/counts |
| `JobFilter` | Admin query filters |
| `RetentionPolicy` | Retention config |

---

## DP1 — Dependency Policy

| Dependency | Status | Notes |
|-----------|--------|-------|
| `sqlalchemy` | Required | SQL backend (default) |
| `redis` | Optional | Redis/Valkey backend |
| `alembic` | Optional | Schema migrations |
| `httpx` | Optional | Callback webhooks |
| `opentelemetry-api` | Optional | Tracing integration |

---

## SE1 — Security Architecture

- Admin operations require RBAC (PS-70 integration hooks).
- Payload validation and size limits enforced on submission.
- Secrets NEVER in payloads, logs, or audit events.
- Worker host/identity authentication in multi-server mode.
- Callback URLs validated against allow-list/domain restrictions.
- Request metadata (source, IP, auth) captured for audit trail.

---

## Integration Pattern

```python
from cloud_dog_jobs import JobQueue, Worker, get_job_queue
from cloud_dog_jobs.domain.models import JobRequest, JobContext, JobResult

# At startup
queue = get_job_queue(config)

# Submit a job
job_id = await queue.submit(JobRequest(
    job_type="ingest",
    queue_name="default",
    payload={"source_uri": "s3://bucket/data.csv"},
    priority=5,
    correlation_id="req-123",
))

# Define handler
async def ingest_handler(ctx: JobContext) -> JobResult:
    for i, chunk in enumerate(chunks):
        ctx.check_cancellation()  # raises if cancelled
        await ctx.update_progress(percentage=i/total*100, stage="ingesting")
        await process(chunk)
    return JobResult(success=True, data={"records": total})

# Run worker
worker = Worker(queue)
worker.register_handler("ingest", ingest_handler)
await worker.run_forever(poll_interval=1.0)

# Admin
from cloud_dog_jobs.admin import AdminService
admin = AdminService(queue)
await admin.cancel(job_id)
await admin.clear_old_jobs(RetentionPolicy(succeeded_days=14, failed_days=30))
```
