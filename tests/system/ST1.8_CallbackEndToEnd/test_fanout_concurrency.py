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
from cloud_dog_jobs.fanout.manager import FanOutManager
from cloud_dog_jobs.queue import JobQueue
from cloud_dog_jobs.scheduler.concurrency import ConcurrencyLimits, ConcurrencyManager
from cloud_dog_jobs.scheduler.dispatcher import Dispatcher


def test_fanout_executes_in_batches_with_concurrency_limit() -> None:
    backend = MemoryQueueBackend()
    queue = JobQueue(backend)
    parent_id = queue.submit(JobRequest(job_type="parent", payload={}))
    fanout = FanOutManager(queue)
    child_ids = fanout.create_fan_out(
        parent_id,
        [{"job_type": "child", "payload": {"idx": i}} for i in range(10)],
    )

    concurrency = ConcurrencyManager(ConcurrencyLimits(global_max=3, per_type_max=3, per_tenant_max=3, per_user_max=3))
    dispatcher = Dispatcher(backend, concurrency=concurrency)

    selected = dispatcher.select_eligible(limit=10)
    assert len(selected) == 3
    for job in selected:
        backend.update_status(job.job_id, JobStatus.SUCCEEDED.value)
        concurrency.release(job.job_type)

    selected2 = dispatcher.select_eligible(limit=10)
    assert len(selected2) == 3

    for child_id in child_ids:
        backend.update_status(child_id, JobStatus.SUCCEEDED.value)

    assert fanout.aggregate_parent_status(parent_id) == JobStatus.SUCCEEDED.value


def test_cancelling_parent_cancels_pending_children() -> None:
    backend = MemoryQueueBackend()
    queue = JobQueue(backend)
    parent_id = queue.submit(JobRequest(job_type="parent", payload={}))
    fanout = FanOutManager(queue)
    children = fanout.create_fan_out(
        parent_id, [{"job_type": "child", "payload": {}}, {"job_type": "child", "payload": {}}]
    )

    fanout.cancel_parent_and_children(parent_id)
    assert queue.get(parent_id).status == JobStatus.CANCELLED
    assert queue.get(children[0]).status == JobStatus.CANCELLED
    assert queue.get(children[1]).status == JobStatus.CANCELLED
