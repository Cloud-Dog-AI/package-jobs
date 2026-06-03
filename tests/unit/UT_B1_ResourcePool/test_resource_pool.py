# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
# W28D-304 / PS-95 §6.1-§6.2 — Resource pool + concurrency caps unit tests

from __future__ import annotations

import pytest

from cloud_dog_jobs.domain.enums import JobStatus
from cloud_dog_jobs.domain.models import Job, JobRequest
from cloud_dog_jobs.scheduler.concurrency import ConcurrencyLimits, ConcurrencyManager
from cloud_dog_jobs.scheduler.dispatcher import Dispatcher
from cloud_dog_jobs.scheduler.resource_pool import ResourcePool, ResourcePoolConfig
from cloud_dog_jobs.backends.memory_backend import MemoryQueueBackend


def _make_job(job_id: str, job_type: str = "test", resources: dict | None = None) -> Job:
    from datetime import datetime, timezone
    return Job(
        job_id=job_id,
        job_type=job_type,
        queue_name="default",
        payload={},
        status=JobStatus.QUEUED,
        priority=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        resources=resources or {},
    )


def _make_request(job_type: str = "test", resources: dict | None = None, priority: int = 0) -> JobRequest:
    return JobRequest(job_type=job_type, payload={}, priority=priority, resources=resources or {})


# ── UT-B1-01: Submit job with resources — field persisted ──

def test_job_request_resources_field():
    """UT-B1-01: JobRequest resources field is persisted in Job."""
    req = _make_request(resources={"llm-pool": 1})
    assert req.resources == {"llm-pool": 1}

    job = _make_job("j1", resources={"llm-pool": 1})
    assert job.resources == {"llm-pool": 1}


# ── UT-B1-02: max_running_per_resource enforced ──

def test_resource_pool_limits_enforcement():
    """UT-B1-02: 3 jobs needing llm-pool with limit=2: 2 run, 1 blocked."""
    pool = ResourcePool(ResourcePoolConfig(limits={"llm-pool": 2}))

    assert pool.acquire("j1", {"llm-pool": 1}) is True
    assert pool.acquire("j2", {"llm-pool": 1}) is True
    assert pool.acquire("j3", {"llm-pool": 1}) is False  # limit hit

    pool.release("j1")
    assert pool.acquire("j3", {"llm-pool": 1}) is True  # now available


# ── UT-B1-03: max_running_per_type via ConcurrencyManager ──

def test_concurrency_per_type_limit():
    """UT-B1-03: 3 jobs of same type with per_type_max=2: 2 run, 1 blocked."""
    mgr = ConcurrencyManager(ConcurrencyLimits(global_max=10, per_type_max=2))

    assert mgr.acquire("llm_query") is True
    assert mgr.acquire("llm_query") is True
    assert mgr.acquire("llm_query") is False

    mgr.release("llm_query")
    assert mgr.acquire("llm_query") is True


# ── UT-B1-04: Job completes → resource slot released ──

def test_resource_released_on_complete():
    """UT-B1-04: Completing a job releases its resource slots."""
    pool = ResourcePool(ResourcePoolConfig(limits={"llm-pool": 1}))
    pool.acquire("j1", {"llm-pool": 1})
    assert pool.can_acquire({"llm-pool": 1}) is False

    pool.release("j1")
    assert pool.can_acquire({"llm-pool": 1}) is True


# ── UT-B1-05: Job fails → resource slot released ──

def test_resource_released_on_failure():
    """UT-B1-05: Failed job still releases resource slots."""
    pool = ResourcePool(ResourcePoolConfig(limits={"gpu": 1}))
    pool.acquire("j1", {"gpu": 1})
    assert pool.can_acquire({"gpu": 1}) is False

    # Simulate failure — same release path
    pool.release("j1")
    assert pool.can_acquire({"gpu": 1}) is True


# ── UT-B1-06: Job cancelled → resource slot released ──

def test_resource_released_on_cancel():
    """UT-B1-06: Cancelled job releases resource slots."""
    pool = ResourcePool(ResourcePoolConfig(limits={"llm-pool": 2}))
    pool.acquire("j1", {"llm-pool": 1})
    pool.acquire("j2", {"llm-pool": 1})
    assert pool.can_acquire({"llm-pool": 1}) is False

    pool.release("j2")  # cancel j2
    assert pool.can_acquire({"llm-pool": 1}) is True


# ── UT-B1-07: Resource pool utilisation reporting ──

def test_resource_utilisation_report():
    """UT-B1-07: utilisation() returns correct pool stats."""
    pool = ResourcePool(ResourcePoolConfig(limits={"llm-pool": 2, "gpu": 4}))
    pool.acquire("j1", {"llm-pool": 1, "gpu": 2})

    util = pool.utilisation()
    assert util["llm-pool"] == {"used": 1, "max": 2, "available": 1}
    assert util["gpu"] == {"used": 2, "max": 4, "available": 2}
    assert pool.blocked_count() == 0

    pool.acquire("j2", {"llm-pool": 1})
    util = pool.utilisation()
    assert util["llm-pool"]["available"] == 0
    assert pool.blocked_count() == 1


# ── Dispatcher integration with resource pool ──

def test_dispatcher_respects_resource_pool():
    """Dispatcher skips jobs that exceed resource pool limits."""
    backend = MemoryQueueBackend()
    pool = ResourcePool(ResourcePoolConfig(limits={"llm-pool": 1}))
    dispatcher = Dispatcher(backend, resource_pool=pool)

    # Enqueue 2 jobs both needing llm-pool
    req1 = _make_request(resources={"llm-pool": 1})
    req2 = _make_request(resources={"llm-pool": 1})
    backend.enqueue(_make_job("j1", resources={"llm-pool": 1}))
    backend.enqueue(_make_job("j2", resources={"llm-pool": 1}))

    selected = dispatcher.select_eligible(limit=5)
    assert len(selected) == 1  # only 1 slot available
    assert selected[0].job_id == "j1"


def test_dispatcher_release_frees_slots():
    """Dispatcher.release_job frees both concurrency and resource slots."""
    backend = MemoryQueueBackend()
    concurrency = ConcurrencyManager(ConcurrencyLimits(global_max=10, per_type_max=1))
    pool = ResourcePool(ResourcePoolConfig(limits={"llm-pool": 1}))
    dispatcher = Dispatcher(backend, concurrency=concurrency, resource_pool=pool)

    job = _make_job("j1", resources={"llm-pool": 1})
    backend.enqueue(job)
    selected = dispatcher.select_eligible(limit=5)
    assert len(selected) == 1

    # No more slots
    backend.enqueue(_make_job("j2", resources={"llm-pool": 1}))
    assert len(dispatcher.select_eligible(limit=5)) == 0

    # Release j1
    dispatcher.release_job(selected[0])
    assert pool.can_acquire({"llm-pool": 1}) is True
    assert concurrency.active_by_type("test") == 0


def test_job_without_resources_always_eligible():
    """Jobs with no resource requirements are not blocked by the pool."""
    pool = ResourcePool(ResourcePoolConfig(limits={"llm-pool": 1}))
    pool.acquire("other", {"llm-pool": 1})  # pool full

    # Job with no resources should still pass
    assert pool.can_acquire({}) is True
    assert pool.acquire("j1", {}) is True
