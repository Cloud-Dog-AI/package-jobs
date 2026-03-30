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

from datetime import timedelta

from cloud_dog_jobs.backends.memory_backend import MemoryQueueBackend
from cloud_dog_jobs.domain.models import JobRequest
from cloud_dog_jobs.maintenance.reaper import MaintenanceReaper
from cloud_dog_jobs.queue import JobQueue


class _Backend:
    def dequeue(self, limit, job_type=None):
        return []


def test_reaper_with_no_jobs() -> None:
    reaper = MaintenanceReaper(_Backend())
    assert reaper.find_stuck_job_ids() == []


def test_reaper_run_sweep_transitions() -> None:
    backend = MemoryQueueBackend()
    queue = JobQueue(backend)
    job_id = queue.submit(JobRequest(job_type="x"))
    job = backend.get(job_id)
    job.updated_at = job.updated_at - timedelta(days=2)
    job.created_at = job.created_at - timedelta(days=2)

    reaper = MaintenanceReaper(backend, claim_timeout_seconds=1)
    summary = reaper.run_sweep(ttl_seconds=60, retention_seconds=3600)
    assert summary["ttl_expired"] >= 1 or summary["retention_purged"] >= 1
