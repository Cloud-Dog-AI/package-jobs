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

import time
import pytest

from cloud_dog_jobs.backends.memory_backend import MemoryQueueBackend
from cloud_dog_jobs.domain.enums import JobStatus
from cloud_dog_jobs.domain.models import JobRequest
from cloud_dog_jobs.queue import JobQueue
from cloud_dog_jobs.worker.worker import Worker


def test_worker_run_once() -> None:
    backend = MemoryQueueBackend()
    queue = JobQueue(backend)
    job_id = queue.submit(JobRequest(job_type="demo", payload={}))

    worker = Worker(backend)

    def handler(ctx):
        ctx.update_progress(100, stage="done")
        return {"ok": True}

    worker.register_handler("demo", handler)
    assert worker.run_once() is True
    assert queue.get(job_id).status == JobStatus.SUCCEEDED


def test_worker_timeout_marks_status() -> None:
    backend = MemoryQueueBackend()
    queue = JobQueue(backend)
    job_id = queue.submit(JobRequest(job_type="slow", payload={}))
    worker = Worker(backend, run_timeout_seconds=0.01)

    def slow_handler(ctx):
        time.sleep(0.1)

    worker.register_handler("slow", slow_handler)
    with pytest.raises(TimeoutError):
        worker.run_once()
    assert queue.get(job_id).status == JobStatus.FAILED
