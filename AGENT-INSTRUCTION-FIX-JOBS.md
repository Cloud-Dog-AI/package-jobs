# Agent Instruction — Fix cloud_dog_jobs (v0.2.0)

**Package:** `cloud_dog_jobs`
**Target version:** 0.2.0
**Date:** 2026-02-18 (updated with full gap analysis)
**Scope:** 5 new features (FR1.33–FR1.37) — **ALL DELIVERED AND VERIFIED**

---

## Status: ✅ COMPLETE (1 minor TESTS.md documentation gap noted)

All 5 issues from cross-project impact assessment have been implemented, tested, and verified. This document is retained for reference and future maintenance.

**Verified on 2026-02-18:**
- 102 tests passed (full suite), 0 failed, 0 skipped
- v0.1.0 baseline: 86 tests → v0.2.0: 102 tests (+16 new)
- Lint and format clean (`ruff check` + `ruff format --check`, 138 files)
- Build produces `cloud_dog_jobs-0.2.0.tar.gz` + `cloud_dog_jobs-0.2.0-py3-none-any.whl`
- All SA1 modules present (56 source files across 19 subpackages)
- All test directories present (41 UT + 12 ST + 13 IT + 5 AT + 6 QT = 77 dirs)
- Zero config-delegation violations (no `os.environ`/`hvac`/Vault reads)
- `security/secrets.py` and `mcp/secrets.py` are payload sanitisation (rejecting secrets in job data), NOT config resolution — compliant with PS-80

**Governing documents:**
1. `platform-jobs/REQUIREMENTS.md` (v0.2.0) — FR1.33–FR1.37
2. `platform-jobs/ARCHITECTURE.md` (v0.2.0) — SA1 module layout
3. `platform-jobs/TESTS.md` (v0.2.0) — UT1.37–UT1.41, ST1.8, AT1.5
4. `packages/backend/AGENT-INSTRUCTION.md` — Integrity Warranty and Config Delegation — ZERO TOLERANCE (MANDATORY)

---

## Delivery Summary

### Issue 1 — Durable Callback Registry ✅ DELIVERED

**FR:** FR1.33 | **Tests:** UT1.29, UT1.30, AT1.5

- `cloud_dog_jobs/callbacks/manager.py` (231 lines) — `CallbackManager` with durable SQL persistence via `build_job_callbacks_table()`
- `register_callback(job_id, callback_url, headers, retry_policy)` persists to storage
- `trigger_job_completion()` fires with standard payload (`job_id`, `status`, `result_summary`, `duration_ms`)
- At-least-once delivery with configurable `RetryPolicy` (exponential backoff, max delay, max attempts)
- Backward-compatible `register()` and `trigger()` APIs preserved
- Injectable `requester` and `sleeper` for test isolation

---

### Issue 2 — Fan-Out Job Pattern ✅ DELIVERED

**FR:** FR1.34 | **Tests:** UT1.32, UT1.33, ST1.9

- `cloud_dog_jobs/fanout/manager.py` (124 lines) — `FanOutManager` with parent/child linking
- `create_fan_out(parent_job_id, child_specs)` creates linked child jobs with `__fanout_parent_job_id` in payload
- `aggregate_parent_status()` with all-success/any-failure semantics
- Optional `partial_success_threshold` for partial success mode
- `cancel_parent_and_children()` cascade cancellation
- `ChildJobSpec` dataclass + dict-based spec support

---

### Issue 3 — Explicit Fallback Policies ✅ DELIVERED

**FR:** FR1.35 | **Tests:** UT1.38 (ErrorTaxonomy covers fallback path)

- `cloud_dog_jobs/extensions/fallback_policies.py` (111 lines) — `FallbackPolicyManager` with per-job-type policies
- `FallbackAction` enum: `retry`, `dead_letter`, `notify`, `ignore`
- Dead-letter queue: creates new job in configurable DLQ with error payload and source reference
- Webhook notification: fires POST to `notify_url` with failure details
- Returns `FallbackDecision` with action, status, should_raise flag, and optional dead_letter_job_id
- Exported from `__init__.py`: `FallbackAction`, `FallbackPolicy`, `FallbackPolicyManager`

---

### Issue 4 — Domain State-Machine Extension ✅ DELIVERED

**FR:** FR1.36 | **Tests:** UT1.9 (DomainStateExtensions)

- `cloud_dog_jobs/extensions/state_extensions.py` (59 lines) — `StateExtensionRegistry` with validation
- `register_state_extension(job_type, custom_states, custom_transitions)` convenience API
- Validates that transition sources exist in custom states
- Module-level `REGISTRY` singleton for convenience access
- `StateExtension` frozen dataclass with `job_type`, `custom_states`, `custom_transitions`

---

### Issue 5 — MCP Job Adapter ✅ DELIVERED

**FR:** FR1.37 | **Tests:** UT1.41 (MCPJobAdapter)

- `cloud_dog_jobs/mcp/job_tools.py` (121 lines) — `create_job_tools(job_manager)` returns 4 tool definitions
- Tools: `jobs.create`, `jobs.status`, `jobs.cancel`, `jobs.list`
- Each tool has MCP-compatible `inputSchema` (JSON Schema), `handler` function, and error mapping
- Error responses use `_mcp_error()` with code and message
- Exported from `__init__.py`: `create_job_tools`

---

## Public API Exports

All v0.2.0 APIs exported from `cloud_dog_jobs/__init__.py`:
- `FallbackAction`, `FallbackPolicy`, `FallbackPolicyManager`
- `register_state_extension`
- `create_job_tools`

Pre-existing exports (callbacks, fan-out used via direct module imports):
- `CallbackManager` available at `cloud_dog_jobs.callbacks.manager`
- `FanOutManager` available at `cloud_dog_jobs.fanout.manager`

---

## Minor Gap — TESTS.md Numbering Conflict

The "New Tests (v0.2.0)" section in TESTS.md lists UT1.37–UT1.41 as v0.2.0 tests, but UT1.37–UT1.40 in the base directory structure section already have names from the v0.1.0 spec (AuditEventSchema, ErrorTaxonomy, PayloadValidation, ScheduledJobs). Only UT1.41 (MCPJobAdapter) is uniquely a v0.2.0 test directory.

The v0.2.0 features are tested by:
- FR1.33 (callbacks) → UT1.29_CallbackManager + UT1.30_CallbackRetry (enhanced for durable persistence)
- FR1.34 (fan-out) → UT1.32_FanOut + UT1.33_FanOutAggregation + ST1.9_FanOutEndToEnd
- FR1.35 (fallback) → tested within UT1.38_ErrorTaxonomy and worker integration tests
- FR1.36 (state extensions) → UT1.9_DomainStateExtensions
- FR1.37 (MCP adapter) → UT1.41_MCPJobAdapter

**Recommended fix:** Update the "New Tests (v0.2.0)" section in TESTS.md to accurately map FR1.33–FR1.37 to their actual test directories rather than claiming UT1.37–UT1.40 as new directories.

---

## Verification — Full Suite

```bash
set -a; source /opt/iac/Development/cloud-dog-ai/env-vault-admin; set +a
.venv/bin/pytest tests --env IT -q
.venv/bin/ruff check cloud_dog_jobs tests
.venv/bin/ruff format --check cloud_dog_jobs tests
.venv/bin/python -m build --no-isolation
```

## pyproject.toml version

```toml
version = "0.2.0"
```

---

## MANDATORY COMPLETION REPORT

When finished, write your report to:
**`/opt/iac/Development/cloud-dog-ai/cloud-dog-ai-platform-standards/packages/backend/platform-jobs/working/W28A-120-FIX-JOBS-REPORT.md`**

Your report MUST include ALL of the following:

### 1. Run summary
- List every file changed and what was changed
- List every module implemented and its purpose

### 2. Test results (REAL counts from actual runs)
```
QT: Xp / Yf
UT: Xp / Yf
ST: Xp / Yf
IT: Xp / Yf
AT: Xp / Yf
Ruff: X issues
```

### 3. Verdict
State one of: **PASS** (100% green) / **PARTIAL** (some fixed, some remain) / **FAIL** (no improvement) / **BLOCKED** (cannot proceed)

If not PASS, list every remaining failure with classification: `CODE_BUG`, `ENV_CONFIG`, `INFRA_MISSING`, `EXT_SERVICE`

### 4. Evidence logs
All logs MUST be saved to `working/` directory:
```
working/w28a-120-qt.log
working/w28a-120-ut.log
working/w28a-120-st.log
working/w28a-120-it.log
working/w28a-120-at.log
working/w28a-120-ruff.log
```

### 5. RULES.md COMPLIANCE WARRANTY

Copy this EXACTLY into your report:
```
I warrant that:
1. I have read RULES.md IN FULL before starting work
2. ALL code I produced is 100% compliant with RULES.md
3. ALL test results reported are REAL — exact counts from actual runs
4. I have NOT weakened any test
5. I have NOT stored, copied, or exposed any credentials
6. ALL credentials come from Vault or git-ignored env files
7. I have NOT modified files outside this package
```
