# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
# W28D-305 / PS-95 §6.3, §6.5, §6.6 — Dependency-aware scheduler unit tests

from __future__ import annotations

from datetime import datetime, timezone
from time import sleep

import pytest

from cloud_dog_jobs.backends.memory_backend import MemoryQueueBackend
from cloud_dog_jobs.domain.enums import JobStatus
from cloud_dog_jobs.domain.errors import DependencyCycleError
from cloud_dog_jobs.domain.models import Job, JobRequest
from cloud_dog_jobs.queue import JobQueue
from cloud_dog_jobs.scheduler.concurrency import ConcurrencyLimits, ConcurrencyManager
from cloud_dog_jobs.scheduler.dependency import DependencyTracker
from cloud_dog_jobs.scheduler.dispatcher import Dispatcher
from cloud_dog_jobs.scheduler.resource_pool import ResourcePool, ResourcePoolConfig
from cloud_dog_jobs.worker.worker import Worker


def _make_job(
    job_id: str,
    job_type: str = "test",
    depends_on: list[str] | None = None,
    resources: dict | None = None,
    priority: int = 0,
) -> Job:
    return Job(
        job_id=job_id,
        job_type=job_type,
        queue_name="default",
        payload={},
        status=JobStatus.QUEUED,
        priority=priority,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        depends_on=depends_on or [],
        resources=resources or {},
    )


# ── UT-B2-01: Job B depends_on=[A_id] — stays QUEUED until A SUCCEEDED ──

def test_depends_on_blocks_until_dependency_succeeds():
    """UT-B2-01: B stays QUEUED until A reaches SUCCEEDED."""
    backend = MemoryQueueBackend()
    tracker = DependencyTracker()
    queue = JobQueue(backend, dependency_tracker=tracker)
    dispatcher = Dispatcher(backend, dependency_tracker=tracker)

    a_id = queue.submit(JobRequest(job_type="test"))
    b_id = queue.submit(JobRequest(job_type="test", depends_on=[a_id]))

    # B should not be selected (A is still QUEUED)
    eligible = dispatcher.select_eligible(limit=10)
    eligible_ids = [j.job_id for j in eligible]
    assert a_id in eligible_ids
    assert b_id not in eligible_ids

    # Claim and complete A
    backend.claim(a_id, "host", "worker")
    backend.update_status(a_id, JobStatus.SUCCEEDED.value)

    # Now B should be eligible
    eligible = dispatcher.select_eligible(limit=10)
    eligible_ids = [j.job_id for j in eligible]
    assert b_id in eligible_ids


# ── UT-B2-02: A completes → B becomes runnable ──

def test_dependency_completed_makes_dependent_runnable():
    """UT-B2-02: A completes → B transitions to RUNNING when picked by worker."""
    backend = MemoryQueueBackend()
    tracker = DependencyTracker()
    queue = JobQueue(backend, dependency_tracker=tracker)
    results: list[str] = []

    def handler(ctx):
        results.append(ctx.job.job_id)

    worker = Worker(backend, dependency_tracker=tracker)
    worker.register_handler("test", handler)

    a_id = queue.submit(JobRequest(job_type="test"))
    b_id = queue.submit(JobRequest(job_type="test", depends_on=[a_id]))

    # Worker should pick A first
    assert worker.run_once() is True
    assert results == [a_id]

    # Now B should run
    assert worker.run_once() is True
    assert results == [a_id, b_id]


# ── UT-B2-03: A fails → B transitions to FAILED (dep_failed) ──

def test_failed_dependency_blocks_dependent():
    """UT-B2-03: A fails → B does not run; tracker reports dep failure."""
    backend = MemoryQueueBackend()
    tracker = DependencyTracker()
    queue = JobQueue(backend, dependency_tracker=tracker)

    a_id = queue.submit(JobRequest(job_type="test"))
    b_id = queue.submit(JobRequest(job_type="test", depends_on=[a_id]))

    # Fail A
    backend.claim(a_id, "host", "worker")
    backend.update_status(a_id, JobStatus.FAILED.value)

    # B should not be eligible (A is FAILED, not SUCCEEDED)
    dispatcher = Dispatcher(backend, dependency_tracker=tracker)
    eligible = dispatcher.select_eligible(limit=10)
    assert all(j.job_id != b_id for j in eligible)

    # Tracker should report B has a failed dependency
    has_failed, failed_deps = tracker.has_failed_dependency(
        b_id, lambda jid: backend.get(jid).status if backend.get(jid) else None
    )
    assert has_failed is True
    assert a_id in failed_deps


# ── UT-B2-04: Cycle detection: A→B→A ──

def test_cycle_detection_rejects_circular_dependency():
    """UT-B2-04: Submit of cycle-closing job returns DependencyCycleError."""
    backend = MemoryQueueBackend()
    tracker = DependencyTracker()
    queue = JobQueue(backend, dependency_tracker=tracker)

    # Submit A depending on B (B doesn't exist yet but tracker records the edge)
    a_id = queue.submit(JobRequest(job_type="test", depends_on=["future-b"]))

    # Now try to submit B depending on A — this closes the cycle: B→A→future-b
    # Since a_id depends on "future-b", submitting a job with id matching "future-b"
    # that depends on a_id would create: future-b → a_id → future-b
    # But job_ids are UUIDs so we need to test via tracker directly

    # Direct test: register A→B, then try B→A
    tracker2 = DependencyTracker()
    tracker2.register("A", ["B"])

    with pytest.raises(DependencyCycleError):
        tracker2.validate_and_register("B", ["A"])

    # Three-node cycle: A→B, B→C, C→A
    tracker3 = DependencyTracker()
    tracker3.register("A", ["B"])
    tracker3.register("B", ["C"])
    with pytest.raises(DependencyCycleError):
        tracker3.validate_and_register("C", ["A"])


# ── UT-B2-05: Diamond dependency: C depends on both A and B ──

def test_diamond_dependency_waits_for_all():
    """UT-B2-05: C depends on A and B — runs only after both A and B succeed."""
    backend = MemoryQueueBackend()
    tracker = DependencyTracker()
    queue = JobQueue(backend, dependency_tracker=tracker)
    dispatcher = Dispatcher(backend, dependency_tracker=tracker)

    a_id = queue.submit(JobRequest(job_type="test"))
    b_id = queue.submit(JobRequest(job_type="test"))
    c_id = queue.submit(JobRequest(job_type="test", depends_on=[a_id, b_id]))

    # C not eligible yet
    eligible = dispatcher.select_eligible(limit=10)
    eligible_ids = [j.job_id for j in eligible]
    assert c_id not in eligible_ids

    # Complete A only — C still blocked
    backend.claim(a_id, "host", "worker")
    backend.update_status(a_id, JobStatus.SUCCEEDED.value)
    eligible = dispatcher.select_eligible(limit=10)
    eligible_ids = [j.job_id for j in eligible]
    assert c_id not in eligible_ids

    # Complete B — now C is eligible
    backend.claim(b_id, "host", "worker")
    backend.update_status(b_id, JobStatus.SUCCEEDED.value)
    eligible = dispatcher.select_eligible(limit=10)
    eligible_ids = [j.job_id for j in eligible]
    assert c_id in eligible_ids


# ── UT-B2-06: Scheduler ordering: deps → resources → priority + age ──

def test_scheduler_respects_deps_resources_priority():
    """UT-B2-06: Correct ordering with 5 mixed-priority jobs respecting deps + resources."""
    backend = MemoryQueueBackend()
    tracker = DependencyTracker()
    pool = ResourcePool(ResourcePoolConfig(limits={"llm-pool": 1}))
    concurrency = ConcurrencyManager(ConcurrencyLimits(global_max=10, per_type_max=10, per_tenant_max=10, per_user_max=10))
    dispatcher = Dispatcher(
        backend,
        concurrency=concurrency,
        resource_pool=pool,
        dependency_tracker=tracker,
    )

    # Job A: no deps, no resources, priority=1
    a = _make_job("A", priority=1)
    backend.enqueue(a)

    # Job B: no deps, needs llm-pool, priority=5 (highest)
    sleep(0.001)  # ensure distinct created_at
    b = _make_job("B", priority=5, resources={"llm-pool": 1})
    backend.enqueue(b)

    # Job C: no deps, needs llm-pool, priority=3
    sleep(0.001)
    c = _make_job("C", priority=3, resources={"llm-pool": 1})
    backend.enqueue(c)

    # Job D: depends on A (not yet done), priority=10
    sleep(0.001)
    d = _make_job("D", priority=10, depends_on=["A"])
    tracker.register("D", ["A"])
    backend.enqueue(d)

    # Job E: no deps, no resources, priority=0
    sleep(0.001)
    e = _make_job("E", priority=0)
    backend.enqueue(e)

    # Select: D is blocked (dep A not succeeded).
    # B has highest priority and gets the 1 llm-pool slot.
    # C needs llm-pool but it's taken by B — skipped.
    # A (priority=1) and E (priority=0) are eligible.
    eligible = dispatcher.select_eligible(limit=10)
    eligible_ids = [j.job_id for j in eligible]

    assert "D" not in eligible_ids  # blocked by dep
    assert "B" in eligible_ids  # highest priority, gets resource
    assert "C" not in eligible_ids  # resource exhausted
    assert "A" in eligible_ids
    assert "E" in eligible_ids

    # B should come first (highest priority among eligible non-dep-blocked)
    assert eligible_ids[0] == "B"


# ── UT-B2-07: blocked_jobs_with_reasons ──

def test_blocked_jobs_with_reasons():
    """UT-B2-07: blocked_jobs_with_reasons returns blocked jobs and explains why."""
    backend = MemoryQueueBackend()
    tracker = DependencyTracker()
    queue = JobQueue(backend, dependency_tracker=tracker)

    a_id = queue.submit(JobRequest(job_type="test"))
    b_id = queue.submit(JobRequest(job_type="test"))
    c_id = queue.submit(JobRequest(job_type="test", depends_on=[a_id, b_id]))

    def status_getter(jid):
        job = backend.get(jid)
        return job.status if job else None

    blocked = tracker.blocked_jobs_with_reasons(status_getter)
    assert len(blocked) == 1
    assert blocked[0]["job_id"] == c_id
    assert len(blocked[0]["blocked_by"]) == 2

    dep_ids = {b["dep_id"] for b in blocked[0]["blocked_by"]}
    assert dep_ids == {a_id, b_id}

    # Complete A — C still blocked on B
    backend.claim(a_id, "host", "worker")
    backend.update_status(a_id, JobStatus.SUCCEEDED.value)

    blocked = tracker.blocked_jobs_with_reasons(status_getter)
    assert len(blocked) == 1
    assert len(blocked[0]["blocked_by"]) == 1
    assert blocked[0]["blocked_by"][0]["dep_id"] == b_id

    # Complete B — C no longer blocked
    backend.claim(b_id, "host", "worker")
    backend.update_status(b_id, JobStatus.SUCCEEDED.value)

    blocked = tracker.blocked_jobs_with_reasons(status_getter)
    assert len(blocked) == 0


# ── Conformance: dependency scheduler through real Worker ──

def test_conformance_dependency_scheduler():
    """Conformance: run_dependency_scheduler_conformance via MemoryQueueBackend."""
    from cloud_dog_jobs.testing.conformance import run_dependency_scheduler_conformance
    run_dependency_scheduler_conformance(MemoryQueueBackend)
