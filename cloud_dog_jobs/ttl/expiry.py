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

# cloud_dog_jobs — TTL expiry utilities
"""TTL expiration checks and transitions."""

from datetime import datetime, timezone


def is_ttl_expired(created_at: datetime, ttl_seconds: int, now: datetime | None = None) -> bool:
    """Return true when TTL has elapsed."""
    current = now or datetime.now(timezone.utc)
    return (current - created_at).total_seconds() > ttl_seconds
