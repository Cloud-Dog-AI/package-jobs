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

from datetime import datetime, timezone

from cloud_dog_jobs.domain.enums import JobStatus
from cloud_dog_jobs.domain.models import Job
from cloud_dog_jobs.worker.context import JobContext


def test_progress_tracking_snapshot() -> None:
    now = datetime.now(timezone.utc)
    ctx = JobContext(Job("id", "t", "q", {}, JobStatus.QUEUED, 0, now, now))
    snapshot = ctx.update_progress(55.0, stage="half", counters={"done": 5})
    assert snapshot["percentage"] == 55.0
    assert snapshot["counters"]["done"] == 5
