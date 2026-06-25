# Agent Instruction — Fix platform-jobs Test Integrity

**Package:** `platform-jobs`
**Date:** 2026-02-20
**Status:** OPEN — HIGH
**Problem:** 5 IT tests use `pytest.skip()` instead of `pytest.fail()`. No env files exist.

---

## INTEGRITY WARRANTY

All rules from `cloud-dog-ai-platform-standards/RULES.md` apply. Read Sections 1, 2, 5 before any work.
**"ASK. DON'T GUESS. DON'T LIE. DON'T FUDGE."**

---

## PROBLEM

```
pytest tests/ -p no:cloud_dog_config --tb=no -q
→ 97 passed, 5 skipped in 3.13s
```

5 IT tests skip with: "Vault credentials not in environment". Per RULES.md § 5.3.10, IT tests MUST use `pytest.fail()` not `pytest.skip()` when backends are unavailable.

Additionally, no `tests/env-*` files exist. The `--env` plugin conflicts with `cloud_dog_config` (same issue as expert-agent).

---

## FIX

### Step 1 — Create env files

Create `tests/env-UT`, `tests/env-ST`, `tests/env-IT`, `tests/env-AT` with appropriate `TEST_ENV_TIER=<tier>` and non-secret config variables.

### Step 2 — Fix pytest plugin conflict

Add to `pyproject.toml`:
```toml
[tool.pytest.ini_options]
addopts = "-p no:cloud_dog_config"
```

Or remove duplicate `--env` registration from conftest if present.

### Step 3 — Replace pytest.skip with pytest.fail for IT

Find all `pytest.skip()` calls in IT test fixtures/files:
```bash
grep -rn "pytest.skip" tests/
```

For any in `integration/` or `application/` directories or fixtures used by IT/AT tests:
- Replace `pytest.skip(msg)` with `pytest.fail(msg)`
- Ensure error message includes: "Source env-vault first: set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a"

### Step 4 — Verify WITHOUT Vault (IT must FAIL not SKIP)

```bash
pytest tests/ -p no:cloud_dog_config --tb=no -q 2>&1 | tail -5
```

**Expected:** 97 passed, 0 skipped, 5 FAILED (with clear Vault message).

### Step 5 — Verify WITH Vault (IT must PASS)

```bash
set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a
pytest tests/ -p no:cloud_dog_config --tb=no -q 2>&1 | tail -5
```

**Expected:** 102 passed, 0 skipped, 0 failed.

---

## COMPLETION GATE

1. Env files created with `TEST_ENV_TIER`
2. Pytest plugin conflict resolved
3. `pytest.skip()` replaced with `pytest.fail()` in IT/AT fixtures
4. Without Vault: IT tests FAIL (not skip)
5. With Vault: all tests pass
6. Exact pass/fail/skip counts reported
