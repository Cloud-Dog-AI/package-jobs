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

"""Tests for in-memory queue operations."""

from __future__ import annotations

from cloud_dog_jobs.backends.memory_backend import MemoryQueueBackend
from cloud_dog_jobs.domain.enums import JobStatus
from cloud_dog_jobs.domain.models import JobRequest
from cloud_dog_jobs.queue import JobQueue


def test_memory_backend_submit_and_claim() -> None:
    """Submit a job, then claim and release it."""
    queue = JobQueue(MemoryQueueBackend())
    job_id = queue.submit(JobRequest(job_type="email", priority=3, payload={"x": 1}))

    jobs = queue.list(limit=10)
    assert len(jobs) == 1
    assert jobs[0].job_id == job_id

    backend = queue._backend
    assert backend.claim(job_id, host_id="hostA", worker_id="worker1") is True
    assert backend.get(job_id).status == JobStatus.RUNNING

    assert backend.release(job_id) is True
    assert backend.get(job_id).status == JobStatus.QUEUED
