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
from cloud_dog_jobs.callbacks.manager import CallbackManager
from cloud_dog_jobs.domain.models import JobRequest
from cloud_dog_jobs.extensions.fallback_policies import FallbackAction, FallbackPolicy, FallbackPolicyManager
from cloud_dog_jobs.queue import JobQueue
from cloud_dog_jobs.worker.worker import Worker


class _Resp:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


def test_callback_retries_then_delivers_and_dead_letter_on_failure() -> None:
    backend = MemoryQueueBackend()
    queue = JobQueue(backend)

    callback_calls: list[int] = []

    def callback_requester(method, url, json=None, headers=None, timeout=None):
        _ = method
        _ = url
        _ = json
        _ = headers
        _ = timeout
        callback_calls.append(1)
        return _Resp(500 if len(callback_calls) == 1 else 200)

    callbacks = CallbackManager(requester=callback_requester, sleeper=lambda _: None)
    success_job_id = queue.submit(JobRequest(job_type="ok", payload={}))
    callbacks.register_callback(success_job_id, "https://example.test/callback", retry_policy={"max_attempts": 2})

    delivered = callbacks.trigger_job_completion(
        success_job_id,
        status="succeeded",
        result_summary={"ok": True},
        duration_ms=12,
    )
    assert delivered is True
    assert len(callback_calls) == 2

    backend.update_status(success_job_id, "succeeded")
    failing_job_id = queue.submit(JobRequest(job_type="fail", payload={}))
    worker = Worker(
        backend,
        fallback_policies=FallbackPolicyManager(
            policies={"fail": FallbackPolicy(action=FallbackAction.DEAD_LETTER, dead_letter_queue="dlq")}
        ),
    )

    def boom(ctx):
        _ = ctx
        raise RuntimeError("boom")

    worker.register_handler("fail", boom)
    assert worker.run_once() is True
    dlq_jobs = [job for job in backend.all_jobs() if job.queue_name == "dlq"]
    assert len(dlq_jobs) == 1
    assert dlq_jobs[0].payload["source_job_id"] == failing_job_id
