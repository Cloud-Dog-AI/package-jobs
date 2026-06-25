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
from cloud_dog_jobs.domain.models import JobRequest
from cloud_dog_jobs.queue import JobQueue
from cloud_dog_jobs.worker.worker import Worker


def test_multi_server_workers_claim_once() -> None:
    backend = MemoryQueueBackend()
    queue = JobQueue(backend)
    queue.submit(JobRequest(job_type="m"))
    w1 = Worker(backend, host_id="h1", worker_id="w1")
    w2 = Worker(backend, host_id="h2", worker_id="w2")
    w1.register_handler("m", lambda ctx: {"ok": True})
    w2.register_handler("m", lambda ctx: {"ok": True})
    assert w1.run_once() is True
    assert w2.run_once() is False
