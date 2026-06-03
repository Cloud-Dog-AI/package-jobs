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

from datetime import datetime, timedelta, timezone

from cloud_dog_jobs.domain.enums import JobStatus
from cloud_dog_jobs.domain.models import Job
from cloud_dog_jobs.maintenance.reaper import MaintenanceReaper


class _Backend:
    def dequeue(self, limit, job_type=None):
        now = datetime.now(timezone.utc)
        return [Job("j1", "x", "q", {}, JobStatus.RUNNING, 0, now - timedelta(hours=2), now - timedelta(hours=2))]


def test_stuck_detection() -> None:
    reaper = MaintenanceReaper(_Backend(), claim_timeout_seconds=30)
    stuck = reaper.find_stuck_job_ids()
    assert "j1" in stuck
