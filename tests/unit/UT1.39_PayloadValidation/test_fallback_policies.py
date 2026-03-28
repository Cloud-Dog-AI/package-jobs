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

from __future__ import annotations

from cloud_dog_jobs.backends.memory_backend import MemoryQueueBackend
from cloud_dog_jobs.domain.enums import JobStatus
from cloud_dog_jobs.domain.models import JobRequest
from cloud_dog_jobs.extensions.fallback_policies import FallbackAction, FallbackPolicy, FallbackPolicyManager
from cloud_dog_jobs.queue import JobQueue


def _job_for(backend: MemoryQueueBackend, job_type: str):
    queue = JobQueue(backend)
    job_id = queue.submit(JobRequest(job_type=job_type, payload={"x": 1}))
    return queue.get(job_id)


def test_retry_action_sets_retry_wait() -> None:
    backend = MemoryQueueBackend()
    job = _job_for(backend, "retry-job")
    manager = FallbackPolicyManager(policies={"retry-job": FallbackPolicy(action=FallbackAction.RETRY)})

    decision = manager.apply(backend, job, RuntimeError("boom"))
    assert decision.action is FallbackAction.RETRY
    assert backend.get(job.job_id).status == JobStatus.RETRY_WAIT


def test_dead_letter_action_enqueues_dlq_job() -> None:
    backend = MemoryQueueBackend()
    job = _job_for(backend, "dlq-job")
    manager = FallbackPolicyManager(
        policies={"dlq-job": FallbackPolicy(action=FallbackAction.DEAD_LETTER, dead_letter_queue="dlq")}
    )

    decision = manager.apply(backend, job, RuntimeError("boom"))
    assert decision.action is FallbackAction.DEAD_LETTER
    assert decision.dead_letter_job_id is not None
    assert backend.get(job.job_id).status == JobStatus.FAILED
    assert backend.get(decision.dead_letter_job_id).queue_name == "dlq"


def test_notify_and_ignore_actions() -> None:
    backend = MemoryQueueBackend()
    notify_job = _job_for(backend, "notify-job")
    ignore_job = _job_for(backend, "ignore-job")
    calls: list[dict] = []

    def notifier(method, url, json=None, timeout=None):
        _ = method
        _ = timeout
        calls.append({"url": url, "json": json})

    manager = FallbackPolicyManager(
        policies={
            "notify-job": FallbackPolicy(action=FallbackAction.NOTIFY, notify_url="https://example.test/hook"),
            "ignore-job": FallbackPolicy(action=FallbackAction.IGNORE),
        },
        notifier=notifier,
    )

    notify_decision = manager.apply(backend, notify_job, RuntimeError("nope"))
    ignore_decision = manager.apply(backend, ignore_job, RuntimeError("nope"))

    assert notify_decision.should_raise is False
    assert ignore_decision.should_raise is False
    assert calls[0]["url"] == "https://example.test/hook"
    assert calls[0]["json"]["job_id"] == notify_job.job_id
