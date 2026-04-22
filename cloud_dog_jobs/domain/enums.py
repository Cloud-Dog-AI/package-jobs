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

# cloud_dog_jobs — Domain enums for job and queue state
"""Enum definitions for job status."""

from __future__ import annotations

from enum import Enum


class JobStatus(str, Enum):
    """Canonical job lifecycle states (PS-75 JQ4).

    Core states (MUST): QUEUED through CANCELLED.
    Extended states (OPTIONAL): CREATED through ARCHIVED for services
    needing the full 13-state lifecycle.
    """

    # --- Core states (PS-75 JQ4.1) ---
    QUEUED = "queued"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    RETRY_WAIT = "retry_wait"
    PAUSED = "paused"
    TIMEOUT = "timeout"
    TTL_EXPIRED = "ttl_expired"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"

    # --- Extended states (PS-75 JQ4, W28A-655) ---
    CREATED = "created"
    VALIDATED = "validated"
    DISPATCHED = "dispatched"
    BLOCKED = "blocked"
    DEAD_LETTERED = "dead_lettered"
    ARCHIVED = "archived"
