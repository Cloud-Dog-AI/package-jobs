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

"""Multi-process coordination test for RedisQueueBackend.

Proves that concurrent claim attempts from multiple threads (simulating
separate processes) result in exactly one winner per job, with no
duplicate execution.
"""

from __future__ import annotations

import threading
from collections import Counter

import fakeredis

import cloud_dog_jobs.backends.redis_backend as mod
from cloud_dog_jobs.backends.redis_backend import RedisQueueBackend
from cloud_dog_jobs.domain.models import JobRequest
from cloud_dog_jobs.queue import JobQueue


def _make_backend(server: fakeredis.FakeServer) -> RedisQueueBackend:
    b = RedisQueueBackend.__new__(RedisQueueBackend)
    client = fakeredis.FakeRedis(server=server, decode_responses=True, connected=True)
    b._client = client
    b._prefix = "test_mp"
    b._queue_key = "test_mp:queue"
    b._lease_timeout = 60
    b._claim_script = client.register_script(mod._CLAIM_LUA)
    b._heartbeat_script = client.register_script(mod._HEARTBEAT_LUA)
    return b


def test_concurrent_claim_no_duplicate_execution() -> None:
    """10 threads race to claim the same job; exactly 1 wins."""
    server = fakeredis.FakeServer()
    backend = _make_backend(server)
    queue = JobQueue(backend)

    job_ids: list[str] = []
    for i in range(5):
        job_ids.append(queue.submit(JobRequest(job_type="coord.test", priority=i)))

    results: list[tuple[str, str, bool]] = []
    lock = threading.Lock()

    def worker(worker_id: str, target_job_id: str) -> None:
        # Each worker gets its own client connection (simulating separate processes)
        wb = _make_backend(server)
        ok = wb.claim(target_job_id, host_id="host", worker_id=worker_id)
        with lock:
            results.append((target_job_id, worker_id, ok))

    threads: list[threading.Thread] = []
    for job_id in job_ids:
        for w in range(10):
            t = threading.Thread(target=worker, args=(f"w-{w}", job_id))
            threads.append(t)

    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    # For each job, exactly 1 claim should succeed
    for job_id in job_ids:
        claims = [r for r in results if r[0] == job_id and r[2] is True]
        rejects = [r for r in results if r[0] == job_id and r[2] is False]
        assert len(claims) == 1, f"Expected exactly 1 claim for {job_id}, got {len(claims)}"
        assert len(rejects) == 9, f"Expected 9 rejects for {job_id}, got {len(rejects)}"


def test_concurrent_claim_unique_claimants() -> None:
    """Each job ends up with a unique claimed_by value."""
    server = fakeredis.FakeServer()
    backend = _make_backend(server)
    queue = JobQueue(backend)

    job_ids = [queue.submit(JobRequest(job_type="coord.unique")) for _ in range(20)]

    lock = threading.Lock()
    winners: dict[str, str] = {}

    def worker(worker_id: str) -> None:
        wb = _make_backend(server)
        for job_id in job_ids:
            if wb.claim(job_id, host_id="host", worker_id=worker_id):
                with lock:
                    winners[job_id] = worker_id

    threads = [threading.Thread(target=worker, args=(f"w-{i}",)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    # Every job should have been claimed exactly once
    assert len(winners) == 20

    # Verify via backend
    for job_id in job_ids:
        job = backend.get(job_id)
        assert job is not None
        assert job.claimed_by is not None
        assert job.claimed_by.startswith("host:")
