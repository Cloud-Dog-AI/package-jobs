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

# cloud_dog_jobs — Retention utilities
"""Retention helpers for purging old records."""

from datetime import datetime, timezone


def should_purge(updated_at: datetime, max_age_seconds: int, now: datetime | None = None) -> bool:
    """Handle should purge."""
    current = now or datetime.now(timezone.utc)
    return (current - updated_at).total_seconds() > max_age_seconds
