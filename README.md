# platform-jobs

**Package:** `cloud_dog_jobs`  
**Standard:** PS-75 (Job & Queue Management)  
**Status:** Pre-release (requirements + architecture defined)

## Purpose

Drop-in Python library implementing the PS-75 job/queue management standard. Provides pluggable queue backends, safe multi-worker execution, concurrency controls, retry/backoff/cancellation, progress tracking, configurable state machines, admin tooling, async completion patterns, and full audit/observability.

## Key Features

- **Queue backends**: SQL (default), Redis/Valkey, hybrid, in-memory — all behind `QueueBackend` interface
- **Job model**: Canonical job with identity, metadata, request tracking, correlation IDs
- **State machine**: Configurable transitions with enforcement; domain-specific extensions (e.g., delivery states)
- **Worker engine**: Poll/claim loop, heartbeats, cooperative cancellation, pause/resume, timeout enforcement
- **Handler registry**: Type-based routing with dependency injection (db, config, cancel token, progress)
- **Concurrency**: Global, per-type, per-tenant, per-user limits — enforced across workers/servers
- **Priority dispatch**: Numeric priority + named levels (LOW/NORMAL/HIGH/URGENT), fair scheduling
- **Retry policies**: Exponential backoff + jitter, fixed backoff, retryable error classification, dead-letter
- **Stuck detection**: Multi-tier (early crash + long stuck), automated recovery sweeps
- **TTL/expiry**: Per-job and per-queue TTL, retention policies, safe purge
- **Idempotency**: Deduplication via idempotency keys with configurable window
- **Progress tracking**: Percentage, stage, counters, current item, ETA
- **Admin tooling**: Full CRUD, cancel/reschedule/resubmit/retry, bulk operations, queue status
- **Callback webhooks**: Register URL per job, trigger on completion with retry
- **MCP async jobs**: `wait=false` → job_id → poll for result
- **Fan-out**: Parent/child jobs with status aggregation
- **Confirmation polling**: External provider status polling with interval/age controls
- **Maintenance reaper**: Automated stuck detection, TTL expiry, retention purge sweeps
- **Audit events**: Full PS-40 L3 compliance — all job operations audited with actor/target/correlation
- **Application logging**: PS-40 L2/L4 — JSON Lines, correlation IDs, no secrets
- **Metrics**: Submit/start/complete/fail/cancel counts, queue depth, latency, worker utilisation
- **Security**: RBAC (PS-70), payload validation, secret exclusion, callback URL validation
- **FastAPI integration**: Optional admin + job REST router with RBAC middleware

## Dependencies

- **Required:** `sqlalchemy`, `redis`, `httpx`
- **Optional:** `alembic`, `opentelemetry-api`

## Documents

- [REQUIREMENTS.md](REQUIREMENTS.md) — 28 functional + observability + security + testing + config requirements
- [ARCHITECTURE.md](ARCHITECTURE.md) — Module layout, component design, integration pattern
- [TESTS.md](TESTS.md) — Test plan, directory structure, coverage map (41 UT + 12 ST + 13 IT + 5 AT + 6 QT)

## Quick Start (planned)

```python
from cloud_dog_jobs import JobQueue, Worker, get_job_queue
from cloud_dog_jobs.domain.models import JobRequest, JobContext, JobResult

# At startup
queue = get_job_queue(config)

# Submit
job_id = await queue.submit(JobRequest(
    job_type="ingest",
    queue_name="default",
    payload={"source_uri": "s3://bucket/data.csv"},
    priority=5,
    correlation_id="req-123",
))

# Handler
async def ingest_handler(ctx: JobContext) -> JobResult:
    for i, chunk in enumerate(chunks):
        ctx.check_cancellation()
        await ctx.update_progress(percentage=i/total*100, stage="ingesting")
        await process(chunk)
    return JobResult(success=True, data={"records": total})

# Worker
worker = Worker(queue)
worker.register_handler("ingest", ingest_handler)
await worker.run_forever(poll_interval=1.0)

# Admin
from cloud_dog_jobs.admin import AdminService
admin = AdminService(queue)
await admin.cancel(job_id)
```

## Installation

```bash
pip install cloud-dog-jobs
```

## API Overview

- queue APIs submit, inspect, and complete jobs
- worker APIs claim and execute queued work
- admin APIs manage cancellation, retry, and operational status

## Examples

- Submit a background job with a typed payload and correlation identifier.
- Register a handler and run a worker loop against a configured backend.
- Use the admin service to cancel, retry, or inspect queued work.

## Standards Alignment

| Standard | Alignment |
|----------|-----------|
| PS-40 (Logging) | Audit events (L3), JSON Lines logging (L2/L4), correlation IDs, no secrets |
| PS-70 (IDAM) | RBAC on admin operations |
| PS-75 (Job/Queue) | Full implementation (JQ1-JQ18) |
| PS-80 (Config) | All settings from config system, zero hardcoded values |
| PS-90 (Security) | Payload validation, secret exclusion, callback URL validation |
| PS-95 (Testing) | UT/ST/IT/AT/QT hierarchy, env-driven, TESTS.md traceability |
| RULES.md | File headers, documentation, UK English, zero hardcoded values |

---

## Licence

Apache-2.0 — Copyright (c) 2026 Cloud-Dog, Viewdeck Engineering Limited
