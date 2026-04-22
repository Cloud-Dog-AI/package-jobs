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

# cloud_dog_jobs — Job execution context
"""Execution context provided to worker handlers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Event
from typing import Any

from cloud_dog_jobs.domain.models import Job


@dataclass(slots=True)
class JobContext:
    """Runtime context exposed to job handlers."""

    job: Job
    cancellation: Event = field(default_factory=Event)
    progress: dict[str, Any] = field(default_factory=dict)

    def is_cancelled(self) -> bool:
        """Return cancellation status."""
        return self.cancellation.is_set()

    def check_cancellation(self) -> None:
        """Raise if cancelled to support cooperative cancellation."""
        if self.is_cancelled():
            raise RuntimeError("Job cancelled")

    def update_progress(
        self,
        percentage: float,
        stage: str = "",
        counters: dict[str, int] | None = None,
        current_item: str | None = None,
    ) -> dict[str, Any]:
        """Update progress fields and return the current snapshot."""
        self.progress = {
            "percentage": percentage,
            "stage": stage,
            "counters": counters or {},
            "current_item": current_item,
            "updated_at": datetime.now(tz=timezone.utc).isoformat(),
        }
        return self.progress
