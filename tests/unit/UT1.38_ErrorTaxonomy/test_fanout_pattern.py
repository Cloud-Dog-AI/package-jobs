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


def test_create_fan_out_and_aggregate_status() -> None:
    queue = JobQueue(MemoryQueueBackend())
    parent_id = queue.submit(JobRequest(job_type="parent", payload={}))
    fanout = FanOutManager(queue)

    child_ids = fanout.create_fan_out(
        parent_id,
        [
            {"job_type": "child", "payload": {"i": 1}},
            {"job_type": "child", "payload": {"i": 2}},
            {"job_type": "child", "payload": {"i": 3}},
        ],
    )

    assert len(child_ids) == 3
    assert fanout.aggregate_parent_status(parent_id) == JobStatus.RUNNING.value

    queue._backend.update_status(child_ids[0], JobStatus.SUCCEEDED.value)  # noqa: SLF001
    queue._backend.update_status(child_ids[1], JobStatus.SUCCEEDED.value)  # noqa: SLF001
    queue._backend.update_status(child_ids[2], JobStatus.FAILED.value)  # noqa: SLF001

    assert fanout.aggregate_parent_status(parent_id) == JobStatus.FAILED.value
    assert fanout.aggregate_parent_status(parent_id, partial_success_threshold=0.66) == JobStatus.SUCCEEDED.value


def test_cancel_parent_and_children() -> None:
    queue = JobQueue(MemoryQueueBackend())
    parent_id = queue.submit(JobRequest(job_type="parent", payload={}))
    fanout = FanOutManager(queue)
    child_ids = fanout.create_fan_out(parent_id, [{"job_type": "child", "payload": {"i": 1}}])

    cancelled = fanout.cancel_parent_and_children(parent_id)
    assert cancelled == 2
    assert queue.get(parent_id).status == JobStatus.CANCELLED
    assert queue.get(child_ids[0]).status == JobStatus.CANCELLED
