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

from cloud_dog_jobs.domain.models import Job
from cloud_dog_jobs.domain.enums import JobStatus
from cloud_dog_jobs.worker.context import JobContext
from datetime import datetime, timezone


def test_job_context_progress_and_cancel() -> None:
    now = datetime.now(timezone.utc)
    job = Job("1", "x", "default", {}, JobStatus.QUEUED, 0, now, now)
    ctx = JobContext(job)
    p = ctx.update_progress(20.0, stage="step1")
    assert p["percentage"] == 20.0
    ctx.cancellation.set()
    assert ctx.is_cancelled()
    with pytest.raises(RuntimeError):
        ctx.check_cancellation()
