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

from cloud_dog_jobs.backends.memory_backend import MemoryQueueBackend
from cloud_dog_jobs.scheduler.concurrency import ConcurrencyLimits, ConcurrencyManager
from cloud_dog_jobs.scheduler.dispatcher import Dispatcher
from cloud_dog_jobs.domain.models import JobRequest
from cloud_dog_jobs.queue import JobQueue


def test_dispatcher_with_concurrency_limits() -> None:
    backend = MemoryQueueBackend()
    queue = JobQueue(backend)
    queue.submit(JobRequest(job_type="a", priority=1))
    queue.submit(JobRequest(job_type="a", priority=2))
    dispatcher = Dispatcher(
        backend, ConcurrencyManager(ConcurrencyLimits(global_max=1, per_type_max=1, per_tenant_max=1, per_user_max=1))
    )
    selected = dispatcher.select_eligible(limit=10)
    assert len(selected) == 1
