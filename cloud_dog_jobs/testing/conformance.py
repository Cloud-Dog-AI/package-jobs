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
