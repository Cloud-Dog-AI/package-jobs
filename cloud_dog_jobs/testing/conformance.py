# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# cloud_dog_jobs — Backend conformance helpers
"""Reusable conformance checks for queue backend implementations."""

from __future__ import annotations

from collections.abc import Callable

from cloud_dog_jobs.backends.base import QueueBackend
from cloud_dog_jobs.domain.enums import JobStatus
from cloud_dog_jobs.domain.models import JobRequest
from cloud_dog_jobs.queue import JobQueue


def run_basic_backend_conformance(backend_factory: Callable[[], QueueBackend]) -> None:
    """Run basic backend conformance."""
    backend = backend_factory()
    queue = JobQueue(backend)

    job_id = queue.submit(JobRequest(job_type="conformance.ping", payload={"ok": True}, priority=1))
    assert isinstance(job_id, str) and job_id

    listed = queue.list(limit=10)
    assert any(j.job_id == job_id for j in listed)

    claimed = backend.claim(job_id, host_id="conf-host", worker_id="conf-worker")
    assert claimed is True

    job = queue.get(job_id)
    assert job is not None
    assert job.status in {JobStatus.RUNNING, JobStatus.QUEUED}

    assert backend.update_status(job_id, JobStatus.SUCCEEDED.value)
    final = queue.get(job_id)
    assert final is not None and final.status == JobStatus.SUCCEEDED


def run_resource_pool_conformance(backend_factory: Callable[[], QueueBackend]) -> None:
    """Run resource pool conformance through the real Worker path.

    PS-95 §6.1 / W28D-304: proves resources on JobRequest are enforced
    by the Dispatcher inside Worker, and released on success and failure.
    """
    from cloud_dog_jobs.scheduler.concurrency import ConcurrencyLimits, ConcurrencyManager
    from cloud_dog_jobs.scheduler.resource_pool import ResourcePool, ResourcePoolConfig
    from cloud_dog_jobs.worker.worker import Worker

    backend = backend_factory()
    pool = ResourcePool(ResourcePoolConfig(limits={"llm-pool": 1}))
    concurrency = ConcurrencyManager(ConcurrencyLimits(global_max=10, per_type_max=5))

    results: list[str] = []

    def handler_success(ctx):
        results.append(f"success:{ctx.job.job_id}")

    def handler_fail(ctx):
        results.append(f"fail:{ctx.job.job_id}")
        raise RuntimeError("deliberate failure")

    worker = Worker(backend, resource_pool=pool, concurrency=concurrency)
    worker.register_handler("resource_test", handler_success)
    worker.register_handler("resource_fail_test", handler_fail)

    queue = JobQueue(backend)

    j1_id = queue.submit(JobRequest(job_type="resource_test", resources={"llm-pool": 1}))
    assert worker.run_once() is True
    assert len(results) == 1
    assert pool.can_acquire({"llm-pool": 1}), "Resource not released after success"

    j2_id = queue.submit(JobRequest(job_type="resource_fail_test", resources={"llm-pool": 1}))
    try:
        worker.run_once()
    except RuntimeError:
        pass
    assert pool.can_acquire({"llm-pool": 1}), "Resource not released after failure"
    assert len(results) == 2


def run_dependency_scheduler_conformance(backend_factory: Callable[[], QueueBackend]) -> None:
    """Run dependency-aware scheduler conformance through the real Worker path.

    PS-95 §6.3 / W28D-305: proves depends_on edges are enforced by the
    Dispatcher inside Worker, blocked jobs are skipped, and jobs become
    runnable after dependencies complete.
    """
    from cloud_dog_jobs.domain.errors import DependencyCycleError
    from cloud_dog_jobs.scheduler.dependency import DependencyTracker
    from cloud_dog_jobs.worker.worker import Worker

    backend = backend_factory()
    tracker = DependencyTracker()
    queue = JobQueue(backend, dependency_tracker=tracker)
    results: list[str] = []

    def handler(ctx):
        results.append(ctx.job.job_id)

    worker = Worker(backend, dependency_tracker=tracker)
    worker.register_handler("dep_test", handler)

    # Submit A (no deps) and B (depends on A)
    a_id = queue.submit(JobRequest(job_type="dep_test"))
    b_id = queue.submit(JobRequest(job_type="dep_test", depends_on=[a_id]))

    # B should NOT run yet (A is still queued)
    # Worker picks only eligible jobs — A should run first
    assert worker.run_once() is True
    assert len(results) == 1
    assert results[0] == a_id

    # Now A is SUCCEEDED — B should be runnable
    assert worker.run_once() is True
    assert len(results) == 2
    assert results[1] == b_id

    # Cycle detection: try to submit C depending on itself indirectly
    c_id = queue.submit(JobRequest(job_type="dep_test"))
    try:
        queue.submit(JobRequest(job_type="dep_test", depends_on=[c_id]))
        # This should work (no cycle — just depends on c)
    except DependencyCycleError:
        raise AssertionError("False cycle detected for valid dependency")
