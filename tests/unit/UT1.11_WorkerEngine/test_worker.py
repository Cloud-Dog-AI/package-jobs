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
from cloud_dog_jobs.extensions.fallback_policies import (
    FallbackAction,
    FallbackPolicy,
    FallbackPolicyManager,
)
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


def test_worker_does_not_consume_its_dead_letter_queue() -> None:
    backend = MemoryQueueBackend()
    queue = JobQueue(backend)
    job_id = queue.submit(JobRequest(queue_name="primary", job_type="boom", payload={"value": 1}))
    fallback = FallbackPolicyManager(
        policies={
            "boom": FallbackPolicy(
                action=FallbackAction.DEAD_LETTER,
                dead_letter_queue="dead-letter",
            )
        }
    )
    worker = Worker(backend, queue_name="primary", fallback_policies=fallback)

    def failing_handler(ctx):
        raise RuntimeError(f"failed {ctx.job.payload['value']}")

    worker.register_handler("boom", failing_handler)

    assert worker.run_once() is True
    assert queue.get(job_id).status == JobStatus.FAILED
    dead_letters = [job for job in backend.all_jobs() if job.queue_name == "dead-letter"]
    assert len(dead_letters) == 1
    assert dead_letters[0].status == JobStatus.QUEUED
    assert dead_letters[0].payload["original_payload"] == {"value": 1}
    assert worker.run_once() is False
