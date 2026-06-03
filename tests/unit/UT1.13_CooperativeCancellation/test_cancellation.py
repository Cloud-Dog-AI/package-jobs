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
from datetime import datetime, timezone

from cloud_dog_jobs.domain.enums import JobStatus
from cloud_dog_jobs.domain.models import Job
from cloud_dog_jobs.worker.context import JobContext


def test_cooperative_cancellation() -> None:
    job = Job("j1", "t", "q", {}, JobStatus.RUNNING, 0, datetime.now(timezone.utc), datetime.now(timezone.utc))
    ctx = JobContext(job)
    ctx.cancellation.set()
    with pytest.raises(RuntimeError):
        ctx.check_cancellation()
