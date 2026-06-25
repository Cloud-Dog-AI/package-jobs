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

import pytest

from cloud_dog_jobs.backends.memory_backend import MemoryQueueBackend
from cloud_dog_jobs.domain.enums import JobStatus
from cloud_dog_jobs.domain.models import JobRequest
from cloud_dog_jobs.queue import JobQueue
from cloud_dog_jobs.worker.worker import Worker


def test_submit_to_fail() -> None:
    backend = MemoryQueueBackend()
    queue = JobQueue(backend)
    job_id = queue.submit(JobRequest(job_type="demo"))
    worker = Worker(backend)

    def boom(ctx):
        raise RuntimeError("boom")

    worker.register_handler("demo", boom)
    with pytest.raises(RuntimeError):
        worker.run_once()
    assert queue.get(job_id).status == JobStatus.FAILED
