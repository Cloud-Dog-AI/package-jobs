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

# cloud_dog_jobs — Handler registry
"""Job type to handler registration and retrieval."""

from __future__ import annotations

from collections.abc import Callable

from cloud_dog_jobs.worker.context import JobContext

JobHandler = Callable[[JobContext], dict]


class HandlerRegistry:
    """Registry of handlers keyed by job type."""

    def __init__(self) -> None:
        self._handlers: dict[str, JobHandler] = {}

    def register(self, job_type: str, handler: JobHandler) -> None:
        """Register a handler for a job type."""
        self._handlers[job_type] = handler

    def get(self, job_type: str) -> JobHandler:
        """Get handler for job type; raise if not registered."""
        if job_type not in self._handlers:
            raise KeyError(f"Unknown job_type: {job_type}")
        return self._handlers[job_type]
