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

# cloud_dog_jobs — Heartbeat manager
"""Heartbeat update helper."""

from cloud_dog_jobs.backends.base import QueueBackend


class HeartbeatManager:
    """Backend heartbeat wrapper."""

    def __init__(self, backend: QueueBackend) -> None:
        self._backend = backend

    def touch(self, job_id: str) -> bool:
        """Handle touch."""
        return self._backend.heartbeat(job_id)
