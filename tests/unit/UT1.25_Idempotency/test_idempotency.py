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

from cloud_dog_jobs.idempotency.manager import IdempotencyManager


def test_idempotency_returns_existing_job_id() -> None:
    mgr = IdempotencyManager(ttl_seconds=60)
    first = mgr.register_or_get("same-key", "job-1")
    second = mgr.register_or_get("same-key", "job-2")
    assert first == "job-1"
    assert second == "job-1"
