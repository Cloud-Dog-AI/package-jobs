# platform-jobs — TESTS.md

**Package:** `cloud_dog_jobs`  
**Version:** 0.2.0 (pre-release)  
**Standard:** PS-75, PS-95  
**Status:** Draft

---

## Test Strategy

### Overview

Tests organised per PS-95 hierarchy:

- **UT** — Unit tests for individual components (backends, state machine, scheduler, worker, callbacks, admin)
- **ST** — System tests for end-to-end flows with in-memory/mock backends
- **IT** — Integration tests with real SQL and Redis backends (env-gated)
- **AT** — Application tests simulating real service patterns
- **QT** — Security tests for RBAC, payload validation, secret exclusion, audit completeness

### Test Principles (PS-95 / RULES.md Compliance)

- `--env` mandatory for all test runs; ZERO hardcoded values.
- UT tests use mock/in-memory backends.
- IT tests require real SQL (PostgreSQL/SQLite) and Redis — env-gated and fail-fast when backends are unavailable.
- 100% REAL systems in IT/AT tests — no mocks, no stubs, no fakes.
- IT/AT/QT tests MUST NOT use `pytest.skip()` for missing mandatory backends; these preconditions fail explicitly.
- Validate 100% of outputs — structure, format, content, quality.
- Test ALL paths — success, failure, edge cases, alternative configs.
- Run tests ONE AT A TIME with real-time output monitoring.
- Report honestly — summary table with PASS/FAIL.
- ALL source files: header blocks (licence, ownership, related reqs/tasks/arch/tests).
- ALL functions/methods/classes: documentation. UK English throughout.
- Stop on failure.

---

## Test Directory Structure

```
tests/
  conftest.py
  env-UT
  env-ST
  env-IT
  env-AT
  unit/
    UT1.1_QueueBackendInterface/
      test_backend_interface.py
    UT1.2_SQLBackend/
      test_sql_backend.py
    UT1.3_RedisBackend/
      test_redis_backend.py
    UT1.4_HybridBackend/
      test_hybrid_backend.py
    UT1.5_MemoryBackend/
      test_memory_backend.py
    UT1.6_JobModel/
      test_job_model.py
    UT1.7_StateMachine/
      test_state_machine.py
    UT1.8_StateTransitions/
      test_transitions.py
    UT1.9_DomainStateExtensions/
      test_domain_states.py
    UT1.10_HandlerRegistry/
      test_handler_registry.py
    UT1.11_WorkerEngine/
      test_worker.py
    UT1.12_JobContext/
      test_job_context.py
    UT1.13_CooperativeCancellation/
      test_cancellation.py
    UT1.14_PauseResume/
      test_pause_resume.py
    UT1.15_Heartbeat/
      test_heartbeat.py
    UT1.16_ConcurrencyLimits/
      test_concurrency.py
    UT1.17_PriorityDispatch/
      test_priority.py
    UT1.18_FairnessPolicy/
      test_fairness.py
    UT1.19_RetryPolicy/
      test_retry_policy.py
    UT1.20_ExponentialBackoff/
      test_backoff.py
    UT1.21_StuckDetection/
      test_stuck_detection.py
    UT1.22_StuckRecovery/
      test_stuck_recovery.py
    UT1.23_TTLExpiry/
      test_ttl_expiry.py
    UT1.24_RetentionPurge/
      test_retention.py
    UT1.25_Idempotency/
      test_idempotency.py
    UT1.26_ProgressTracking/
      test_progress.py
    UT1.27_AdminCRUD/
      test_admin_crud.py
    UT1.28_AdminBulkOps/
      test_admin_bulk.py
    UT1.29_CallbackManager/
      test_callbacks.py
    UT1.30_CallbackRetry/
      test_callback_retry.py
    UT1.31_MCPAsyncAdapter/
      test_mcp_async.py
    UT1.32_FanOut/
      test_fanout.py
    UT1.33_FanOutAggregation/
      test_fanout_aggregation.py
    UT1.34_ConfirmationPoller/
      test_poller.py
    UT1.35_MaintenanceReaper/
      test_reaper.py
    UT1.36_AuditEmitter/
      test_audit_emitter.py
    UT1.37_AuditEventSchema/
      test_audit_schema.py
    UT1.38_ErrorTaxonomy/
      test_errors.py
    UT1.39_PayloadValidation/
      test_payload_validation.py
    UT1.40_ScheduledJobs/
      test_scheduled.py
    UT1.41_MCPJobAdapter/
      test_mcp_job_tools.py
  system/
    ST1.1_SubmitToComplete/
      test_submit_complete.py
    ST1.2_SubmitToFail/
      test_submit_fail.py
    ST1.3_RetryEndToEnd/
      test_retry_e2e.py
    ST1.4_CancelEndToEnd/
      test_cancel_e2e.py
    ST1.5_TTLEndToEnd/
      test_ttl_e2e.py
    ST1.6_PriorityEndToEnd/
      test_priority_e2e.py
    ST1.7_ConcurrencyEndToEnd/
      test_concurrency_e2e.py
    ST1.8_CallbackEndToEnd/
      test_fanout_concurrency.py
    ST1.9_FanOutEndToEnd/
      test_fanout_e2e.py
    ST1.10_AdminEndToEnd/
      test_admin_e2e.py
    ST1.11_MaintenanceEndToEnd/
      test_maintenance_e2e.py
    ST1.12_AuditCompleteness/
      test_audit_completeness.py
  integration/
    IT1.1_SQLAtomicClaim/
      test_sql_atomic_claim.py
    IT1.2_SQLConcurrentWorkers/
      test_sql_concurrent_workers.py
    IT1.3_SQLPriorityOrdering/
      test_sql_priority.py
    IT1.4_RedisEnqueueDequeue/
      test_redis_enqueue.py
    IT1.5_RedisPriorityQueue/
      test_redis_priority.py
    IT1.6_RedisFallbackToSQL/
      test_redis_fallback.py
    IT1.7_HybridEndToEnd/
      test_hybrid_e2e.py
    IT1.8_MultiWorkerClaim/
      test_multi_worker_claim.py
    IT1.9_ConcurrencyAcrossWorkers/
      test_cross_worker_concurrency.py
    IT1.10_RetryWithRealBackend/
      test_retry_real.py
    IT1.11_StuckDetectionReal/
      test_stuck_real.py
    IT1.12_RetentionPurgeReal/
      test_retention_real.py
    IT1.13_IdempotencyReal/
      test_idempotency_real.py
  application/
    AT1.1_ServiceStartupPattern/
      test_service_startup.py
    AT1.2_FullJobLifecycle/
      test_full_lifecycle.py
    AT1.3_MultiServerWorkers/
      test_multi_server.py
    AT1.4_FastAPIIntegration/
      test_fastapi_routes.py
    AT1.5_ConformanceSuite/
      test_callback_delivery_e2e.py
  security/
    QT1.1_RBACEnforcement/
      test_rbac.py
    QT1.2_PayloadSizeLimit/
      test_payload_size.py
    QT1.3_SecretNeverInPayload/
      test_secret_exclusion.py
    QT1.4_SecretNeverInLogs/
      test_log_secret_scan.py
    QT1.5_CallbackURLValidation/
      test_callback_url.py
    QT1.6_AuditEventIntegrity/
      test_audit_integrity.py
```

### Environment Matrix

| File | Tier | Purpose |
|------|------|---------|
| `tests/env-UT` | UT | Unit tier selection (`TEST_ENV_TIER=UT`) |
| `tests/env-ST` | ST | System tier selection (`TEST_ENV_TIER=ST`) |
| `tests/env-IT` | IT | Integration tier selection (`TEST_ENV_TIER=IT`) |
| `tests/env-AT` | AT | Application tier selection (`TEST_ENV_TIER=AT`) |

All test runs require `--env <file>`. Missing `--env` is a usage error.

---

## Coverage Map (Requirements → Tests)

### Functional Requirements
- **FR1.1** → UT1.1 (backend interface)
- **FR1.2** → UT1.2, IT1.1-IT1.3 (SQL backend)
- **FR1.3** → UT1.3, IT1.4-IT1.6 (Redis backend)
- **FR1.4** → UT1.4, IT1.7 (hybrid)
- **FR1.5** → UT1.5 (memory backend)
- **FR1.6** → UT1.1 (custom backend registration)
- **FR1.7** → UT1.6 (job model)
- **FR1.8** → UT1.7-UT1.9 (state machine)
- **FR1.9** → UT1.10 (handler registry)
- **FR1.10** → UT1.11 (worker engine)
- **FR1.11** → UT1.13 (cancellation), ST1.4
- **FR1.12** → UT1.14 (pause/resume)
- **FR1.13** → UT1.16, IT1.9, ST1.7 (concurrency)
- **FR1.14** → UT1.17, IT1.5, ST1.6 (priority)
- **FR1.15** → UT1.19-UT1.20, IT1.10, ST1.3 (retry/backoff)
- **FR1.16** → UT1.21-UT1.22, IT1.11 (stuck detection/recovery)
- **FR1.17** → UT1.23-UT1.24, IT1.12, ST1.5 (TTL/retention)
- **FR1.18** → UT1.25, IT1.13 (idempotency)
- **FR1.19** → UT1.26 (progress)
- **FR1.20** → UT1.27-UT1.28, ST1.10 (admin CRUD)
- **FR1.21** → UT1.29-UT1.30, ST1.8 (callbacks)
- **FR1.22** → UT1.31 (MCP async)
- **FR1.23** → UT1.32-UT1.33, ST1.9 (fan-out)
- **FR1.24** → UT1.34 (polling)
- **FR1.25** → UT1.17, UT1.40 (scheduler/dispatcher)
- **FR1.26** → UT1.35, ST1.11 (maintenance reaper)
- **FR1.27** → AT1.4 (FastAPI integration)
- **FR1.28** → (LLM call logging — optional extension test)

### Observability (PS-40 Alignment)
- **OB1.1** → UT1.36-UT1.37, ST1.12, QT1.6 (audit events)
- **OB1.2** → QT1.4 (application logging, secret scan)
- **OB1.3** → ST1.12 (metrics hooks)
- **OB1.4** → (OpenTelemetry — future test)

### Security (PS-70/PS-90 Alignment)
- **CS1.1** → QT1.1 (RBAC)
- **CS1.2** → QT1.2 (payload size)
- **CS1.3** → QT1.3 (secrets in payloads)
- **CS1.4** → QT1.4 (secrets in logs)
- **CS1.5** → IT1.8 (worker auth — multi-server)
- **CS1.6** → QT1.5 (callback URL validation)

### Testing (PS-95 Alignment)
- **TS1.1-TS1.5** → All tests follow hierarchy, env-driven, documented, traceable

---

## Unit Tests (UT) — Selected Detail

### UT1.2: SQL Backend
- **Scope**: SQL queue backend (SQLAlchemy)
- **What is being tested**: Enqueue, dequeue with priority ordering, atomic claim (FOR UPDATE SKIP LOCKED), release, heartbeat update, status updates, queue status counts
- **Related Requirements**: FR1.2
- **Related Architecture**: CC1.3

### UT1.7: State Machine
- **Scope**: Configurable state machine
- **What is being tested**: Default state transitions valid/rejected; `is_terminal()`, `is_retryable()`; domain-specific state extension (DeliveryState pattern); invalid transition raises error
- **Related Requirements**: FR1.8
- **Related Architecture**: CC1.5

### UT1.8: Multi-Worker Claim (IT)
- **Scope**: Atomic claim correctness under concurrency
- **What is being tested**: Multiple workers claim same job — exactly ONE succeeds; claim records host_id/worker_id; no double execution; race condition handling
- **Related Requirements**: FR1.10, JQ8.3
- **IT Prerequisite**: Real PostgreSQL or SQLite

### UT1.16: Concurrency Limits
- **Scope**: Global, per-type, per-tenant, per-user concurrency
- **What is being tested**: Jobs queued when at limit; dispatched when slot opens; limits enforced across simulated workers; priority respected within limits
- **Related Requirements**: FR1.13

### UT1.36: Audit Emitter
- **Scope**: Audit event emission for job operations
- **What is being tested**: Events emitted for: submit, claim, transition, cancel, reschedule, bulk ops, purge, callback. Schema matches PS-40 L3 (timestamp, service, event_type, action, outcome, actor, target, trace_id, request_id). No secrets in events.
- **Related Requirements**: OB1.1

### UT1.25: Idempotency
- **Scope**: Idempotency key deduplication
- **What is being tested**: Same key → same job_id returned; different key → different job_id; key expiry after configurable window; concurrent submissions with same key
- **Related Requirements**: FR1.18

---

## v0.2.0 Feature Coverage (FR1.33–FR1.37)

### FR1.33: Durable Callback Registry
- **Type**: UT
- **Scope**: Callback registration and delivery
- **What is being tested**: `register_callback()` persists config; callback fired on job completion (success); callback fired on job failure; retry on delivery failure; callback payload includes job_id, status, result_summary, duration_ms; at-least-once delivery semantics
- **Primary tests**: `UT1.29_CallbackManager`, `UT1.30_CallbackRetry`, `UT1.37_AuditEventSchema/test_durable_callback_registry.py`, `AT1.5_ConformanceSuite/test_callback_delivery_e2e.py`
- **Related Requirements**: FR1.33
- **Related Architecture**: callbacks/manager.py

### FR1.34: Fan-Out Job Pattern
- **Type**: UT
- **Scope**: Parent/child job fan-out
- **What is being tested**: `create_fan_out()` creates linked child jobs; all children succeed → parent success; any child fails → parent failed; partial success mode with threshold; child jobs respect concurrency controls; parent status query returns aggregate
- **Primary tests**: `UT1.32_FanOut`, `UT1.33_FanOutAggregation`, `UT1.38_ErrorTaxonomy/test_fanout_pattern.py`, `ST1.8_CallbackEndToEnd/test_fanout_concurrency.py`, `ST1.9_FanOutEndToEnd`
- **Related Requirements**: FR1.34
- **Related Architecture**: fanout/manager.py

### FR1.35: Explicit Fallback Policies
- **Type**: UT
- **Scope**: Per-type fallback policy configuration
- **What is being tested**: `fallback_action=retry` → standard retry; `dead_letter` → job moved to DLQ; `notify` → webhook called; `ignore` → job marked failed silently; dead_letter_queue configurable; notify_url called with failure details
- **Primary tests**: `UT1.39_PayloadValidation/test_fallback_policies.py`, `AT1.5_ConformanceSuite/test_callback_delivery_e2e.py`
- **Related Requirements**: FR1.35
- **Related Architecture**: extensions/fallback_policies.py

### FR1.36: Domain State-Machine Extension
- **Type**: UT
- **Scope**: Custom state-machine extensions per job type
- **What is being tested**: `register_state_extension()` adds custom states; custom transitions validated; base states still work; domain state coexists with base states; invalid custom transition rejected; multiple job types with different extensions
- **Primary tests**: `UT1.9_DomainStateExtensions`, `UT1.40_ScheduledJobs/test_domain_state_extension_v2.py`
- **Related Requirements**: FR1.36
- **Related Architecture**: extensions/state_extensions.py

### FR1.37: MCP Job Adapter
- **Type**: UT
- **Scope**: MCP tool definitions for job operations
- **What is being tested**: `create_job_tools()` returns tool definitions for create, status, cancel, list; tool definitions have correct schemas; tools delegate to job_manager; error responses mapped to MCP error format
- **Primary tests**: `UT1.41_MCPJobAdapter/test_mcp_job_tools.py`
- **Related Requirements**: FR1.37
- **Related Architecture**: mcp/job_tools.py

### ST1.8: Fan-Out with Concurrency
- **Type**: ST
- **Scope**: Fan-out under concurrency limits
- **What is being tested**: Fan-out with 10 children under concurrency limit of 3; children execute in batches; parent completes when all children done; cancelling parent cancels pending children
- **Related Requirements**: FR1.34, FR1.13

### AT1.5: Callback Delivery End-to-End
- **Type**: AT
- **Scope**: Full callback lifecycle
- **What is being tested**: Register callback → submit job → job completes → callback delivered to mock endpoint → verify payload; callback failure → retry → eventual delivery; dead-letter on max retries
- **Related Requirements**: FR1.33, FR1.35

---

## Test Run History

| Date (UTC) | Scope | Command | Status | Notes |
|------------|-------|---------|--------|-------|
| 2026-02-18 | Full package matrix (Vault-backed, venv toolchain) | `set -a; source /opt/iac/Development/cloud-dog-ai/env-vault-admin; set +a; .venv/bin/pytest tests --env IT -q` | PASS | 102 passed, 0 failed, 0 skipped |
| 2026-02-18 | Lint + format check (venv toolchain) | `.venv/bin/ruff check cloud_dog_jobs tests && .venv/bin/ruff format --check cloud_dog_jobs tests` | PASS | All checks passed; 138 files already formatted |
| 2026-02-18 | Build + install verification (venv toolchain) | `.venv/bin/python -m build && .venv/bin/python -m pip install --force-reinstall dist/cloud_dog_jobs-0.2.0-py3-none-any.whl && .venv/bin/python -c "import cloud_dog_jobs; print(cloud_dog_jobs.__version__)"` | PASS | Build succeeds, wheel reinstalls, version prints `0.2.0` |

---

## Latest Verified Run

| Date (UTC) | Scope | Command | Status | Notes |
|------------|-------|---------|--------|-------|
| 2026-02-18 | Full package matrix (Vault-backed, venv toolchain) | `set -a; source /opt/iac/Development/cloud-dog-ai/env-vault-admin; set +a; .venv/bin/pytest tests --env IT -q` | PASS | 102 passed, 0 failed, 0 skipped |
