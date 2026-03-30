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

from cloud_dog_jobs.domain.models import JobRequest, Job


def test_job_model_from_request() -> None:
    req = JobRequest(job_type="ingest", payload={"a": 1}, priority=3)
    job = Job.from_request(req)
    assert job.job_type == "ingest"
    assert job.payload["a"] == 1
    assert job.priority == 3
