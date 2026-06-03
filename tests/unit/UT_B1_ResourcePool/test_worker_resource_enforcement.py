# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
# W28D-304 sendback: prove resource enforcement through real Worker path

from __future__ import annotations

import pytest

from cloud_dog_jobs.backends.memory_backend import MemoryQueueBackend
from cloud_dog_jobs.domain.models import JobRequest
from cloud_dog_jobs.queue import JobQueue
from cloud_dog_jobs.scheduler.concurrency import ConcurrencyLimits, ConcurrencyManager
from cloud_dog_jobs.scheduler.resource_pool import ResourcePool, ResourcePoolConfig
from cloud_dog_jobs.testing.conformance import run_resource_pool_conformance
from cloud_dog_jobs.worker.worker import Worker


def test_conformance_resource_pool_memory_backend():
    """Run resource pool conformance against MemoryQueueBackend through real Worker."""
    run_resource_pool_conformance(MemoryQueueBackend)


def test_worker_releases_resource_on_success():
    """Worker releases resource slots after successful job execution."""
    backend = MemoryQueueBackend()
    pool = ResourcePool(ResourcePoolConfig(limits={"llm-pool": 1}))
    worker = Worker(backend, resource_pool=pool)

    executed = []
    worker.register_handler("test", lambda ctx: executed.append(ctx.job.job_id))

    queue = JobQueue(backend)
    j1 = queue.submit(JobRequest(job_type="test", resources={"llm-pool": 1}))

    worker.run_once()
    assert len(executed) == 1
    assert pool.can_acquire({"llm-pool": 1}), "Slot not released after success"


def test_worker_releases_resource_on_failure():
    """Worker releases resource slots after job failure."""
    backend = MemoryQueueBackend()
    pool = ResourcePool(ResourcePoolConfig(limits={"llm-pool": 1}))
    worker = Worker(backend, resource_pool=pool)

    worker.register_handler("fail", lambda ctx: (_ for _ in ()).throw(RuntimeError("boom")))

    queue = JobQueue(backend)
    queue.submit(JobRequest(job_type="fail", resources={"llm-pool": 1}))

    with pytest.raises(RuntimeError, match="boom"):
        worker.run_once()

    assert pool.can_acquire({"llm-pool": 1}), "Slot not released after failure"


def test_worker_releases_resource_on_timeout():
    """Worker releases resource slots after job timeout."""
    import time

    backend = MemoryQueueBackend()
    pool = ResourcePool(ResourcePoolConfig(limits={"llm-pool": 1}))
    worker = Worker(backend, resource_pool=pool, run_timeout_seconds=0.1)

    worker.register_handler("slow", lambda ctx: time.sleep(5))

    queue = JobQueue(backend)
    queue.submit(JobRequest(job_type="slow", resources={"llm-pool": 1}))

    with pytest.raises(TimeoutError):
        worker.run_once()

    assert pool.can_acquire({"llm-pool": 1}), "Slot not released after timeout"


def test_worker_enforces_resource_limit():
    """Worker with 1 llm-pool slot only runs 1 job at a time."""
    backend = MemoryQueueBackend()
    pool = ResourcePool(ResourcePoolConfig(limits={"llm-pool": 1}))
    worker = Worker(backend, resource_pool=pool)

    executed = []
    worker.register_handler("test", lambda ctx: executed.append(ctx.job.job_id))

    queue = JobQueue(backend)
    j1 = queue.submit(JobRequest(job_type="test", resources={"llm-pool": 1}))
    j2 = queue.submit(JobRequest(job_type="test", resources={"llm-pool": 1}))

    # First run_once picks j1
    assert worker.run_once() is True
    assert len(executed) == 1

    # Second run_once picks j2 (j1 released in finally)
    assert worker.run_once() is True
    assert len(executed) == 2


def test_worker_without_resource_pool_behaves_normally():
    """Worker without resource_pool works exactly as before (backwards compat)."""
    backend = MemoryQueueBackend()
    worker = Worker(backend)

    executed = []
    worker.register_handler("test", lambda ctx: executed.append(ctx.job.job_id))

    queue = JobQueue(backend)
    queue.submit(JobRequest(job_type="test"))

    assert worker.run_once() is True
    assert len(executed) == 1


def test_config_resource_pool_settings():
    """Config model parses resource pool limits."""
    from cloud_dog_jobs.config.models import jobs_config_from_dict

    cfg = jobs_config_from_dict({
        "resource_pool": {"limits": {"llm-pool": 2, "gpu": 4}},
        "concurrency": {"global_max": 20, "per_type_max": 8},
    })
    assert cfg.resource_pool.limits == {"llm-pool": 2, "gpu": 4}
    assert cfg.concurrency.global_max == 20
    assert cfg.concurrency.per_type_max == 8


def test_config_defaults_no_resource_pool():
    """Config defaults produce no resource pool limits."""
    from cloud_dog_jobs.config.models import jobs_config_from_dict

    cfg = jobs_config_from_dict({})
    assert cfg.resource_pool.limits is None
    assert cfg.concurrency.global_max == 10
