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

"""UT-B3: Redis/Valkey backend unit tests using fakeredis.

Covers:
  UT-B3-01  Enqueue + dequeue round-trip preserves all Job fields
  UT-B3-02  Atomic claim prevents double-claim
  UT-B3-03  Heartbeat renews lease TTL
  UT-B3-04  Lease expiry triggers reap
  UT-B3-05  Full conformance suite passes against fakeredis
"""

from __future__ import annotations

import time
from unittest.mock import patch

import fakeredis
import pytest

from cloud_dog_jobs.backends.redis_backend import RedisQueueBackend
from cloud_dog_jobs.domain.enums import JobStatus
from cloud_dog_jobs.domain.models import Job, JobRequest
from cloud_dog_jobs.queue import JobQueue
from cloud_dog_jobs.testing.conformance import (
    run_basic_backend_conformance,
    run_dependency_scheduler_conformance,
    run_resource_pool_conformance,
)


@pytest.fixture()
def fake_redis():
    """Return a fakeredis server instance shared across a single test."""
    return fakeredis.FakeServer()


@pytest.fixture()
def backend(fake_redis):
    """Return a RedisQueueBackend backed by fakeredis."""
    b = RedisQueueBackend.__new__(RedisQueueBackend)
    client = fakeredis.FakeRedis(server=fake_redis, decode_responses=True)
    b._client = client
    b._prefix = "test_b3"
    b._queue_key = "test_b3:queue"
    b._lease_timeout = 5
    b._claim_script = client.register_script(
        RedisQueueBackend.__init__.__code__  # unused — overridden below
    ) if False else client.register_script(
        # Re-register the Lua scripts on the fake client
        __import__("cloud_dog_jobs.backends.redis_backend", fromlist=["_CLAIM_LUA"])._CLAIM_LUA
    )
    b._heartbeat_script = client.register_script(
        __import__("cloud_dog_jobs.backends.redis_backend", fromlist=["_HEARTBEAT_LUA"])._HEARTBEAT_LUA
    )
    return b


def _make_backend(fake_redis) -> RedisQueueBackend:
    """Factory for conformance helpers."""
    import cloud_dog_jobs.backends.redis_backend as mod

    b = RedisQueueBackend.__new__(RedisQueueBackend)
    client = fakeredis.FakeRedis(server=fake_redis, decode_responses=True)
    b._client = client
    b._prefix = f"test_cf_{id(b)}"
    b._queue_key = f"{b._prefix}:queue"
    b._lease_timeout = 60
    b._claim_script = client.register_script(mod._CLAIM_LUA)
    b._heartbeat_script = client.register_script(mod._HEARTBEAT_LUA)
    return b


# UT-B3-01: Enqueue + dequeue round-trip preserves all Job fields
def test_enqueue_dequeue_round_trip(backend: RedisQueueBackend) -> None:
    queue = JobQueue(backend)
    req = JobRequest(
        job_type="test.round_trip",
        queue_name="demo",
        payload={"key": "value"},
        priority=5,
        resources={"gpu": 1},
        depends_on=["dep-1"],
        user_id="user-42",
        correlation_id="corr-99",
    )
    job_id = queue.submit(req)

    jobs = queue.list(limit=10)
    assert len(jobs) == 1
    job = jobs[0]
    assert job.job_id == job_id
    assert job.job_type == "test.round_trip"
    assert job.queue_name == "demo"
    assert job.payload == {"key": "value"}
    assert job.priority == 5
    assert job.status == JobStatus.QUEUED
    assert job.resources == {"gpu": 1}
    assert job.depends_on == ["dep-1"]
    assert job.user_id == "user-42"
    assert job.correlation_id == "corr-99"
    assert job.attempt == 0
    assert job.version == 0


# UT-B3-02: Atomic claim prevents double-claim
def test_atomic_claim_prevents_double_claim(backend: RedisQueueBackend) -> None:
    queue = JobQueue(backend)
    job_id = queue.submit(JobRequest(job_type="test.claim"))

    first = backend.claim(job_id, host_id="host-a", worker_id="w1")
    assert first is True

    second = backend.claim(job_id, host_id="host-b", worker_id="w2")
    assert second is False

    job = backend.get(job_id)
    assert job is not None
    assert job.status == JobStatus.RUNNING
    assert job.claimed_by == "host-a:w1"


# UT-B3-03: Heartbeat renews lease TTL
def test_heartbeat_renews_lease(backend: RedisQueueBackend) -> None:
    queue = JobQueue(backend)
    job_id = queue.submit(JobRequest(job_type="test.heartbeat"))

    backend.claim(job_id, host_id="h1", worker_id="w1")
    ttl_before = backend.lease_ttl(job_id)
    assert ttl_before > 0

    ok = backend.heartbeat(job_id)
    assert ok is True
    ttl_after = backend.lease_ttl(job_id)
    assert ttl_after > 0


# UT-B3-04: Lease expiry triggers reap
def test_lease_expiry_triggers_reap(backend: RedisQueueBackend) -> None:
    queue = JobQueue(backend)
    job_id = queue.submit(JobRequest(job_type="test.reap"))

    backend.claim(job_id, host_id="h1", worker_id="w1")
    job = backend.get(job_id)
    assert job is not None and job.status == JobStatus.RUNNING

    # Manually delete the lease key to simulate expiry
    backend._client.delete(backend._lease_key(job_id))
    assert backend.lease_ttl(job_id) == -2

    reaped = backend.reap_expired_leases()
    assert job_id in reaped

    job = backend.get(job_id)
    assert job is not None and job.status == JobStatus.QUEUED
    assert job.claimed_by is None


# UT-B3-05: Full conformance suite passes against fakeredis
def test_basic_conformance(fake_redis) -> None:
    run_basic_backend_conformance(lambda: _make_backend(fake_redis))


def test_resource_pool_conformance(fake_redis) -> None:
    run_resource_pool_conformance(lambda: _make_backend(fake_redis))


def test_dependency_scheduler_conformance(fake_redis) -> None:
    run_dependency_scheduler_conformance(lambda: _make_backend(fake_redis))


# Additional: record_attempt, update_progress, store_result
def test_record_attempt_and_progress(backend: RedisQueueBackend) -> None:
    queue = JobQueue(backend)
    job_id = queue.submit(JobRequest(job_type="test.progress"))

    assert backend.record_attempt(job_id, error="timeout") is True
    job = backend.get(job_id)
    assert job is not None and job.attempt == 1
    assert job.last_error == {"message": "timeout"}

    assert backend.update_progress(job_id, {"pct": 50}) is True
    job = backend.get(job_id)
    assert job is not None and job.progress == {"pct": 50}

    assert backend.store_result(job_id, {"output": "done"}) is True
    job = backend.get(job_id)
    assert job is not None and job.result_ref is not None


# Additional: release clears lease
def test_release_clears_lease(backend: RedisQueueBackend) -> None:
    queue = JobQueue(backend)
    job_id = queue.submit(JobRequest(job_type="test.release"))

    backend.claim(job_id, host_id="h1", worker_id="w1")
    assert backend.lease_ttl(job_id) > 0

    backend.release(job_id)
    assert backend.lease_ttl(job_id) == -2
    job = backend.get(job_id)
    assert job is not None and job.status == JobStatus.QUEUED


# Additional: update_status to terminal clears lease
def test_terminal_status_clears_lease(backend: RedisQueueBackend) -> None:
    queue = JobQueue(backend)
    job_id = queue.submit(JobRequest(job_type="test.terminal"))

    backend.claim(job_id, host_id="h1", worker_id="w1")
    assert backend.lease_ttl(job_id) > 0

    backend.update_status(job_id, JobStatus.SUCCEEDED.value)
    assert backend.lease_ttl(job_id) == -2
    job = backend.get(job_id)
    assert job is not None
    assert job.finished_at is not None
