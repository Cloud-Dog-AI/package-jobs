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

# cloud_dog_jobs — Backend registry
"""Factory helpers for backend selection and graceful fallback."""

from cloud_dog_jobs.backends.memory_backend import MemoryQueueBackend
from cloud_dog_jobs.backends.redis_backend import RedisQueueBackend
from cloud_dog_jobs.backends.sql_backend import SQLQueueBackend


def select_backend(preferred: str, *, sql_url: str | None = None, redis_url: str | None = None):
    """Select backend by name with fallback to SQL/memory."""
    if preferred == "redis" and redis_url:
        backend = RedisQueueBackend(redis_url)
        if backend.health_check():
            return backend
        if sql_url:
            return SQLQueueBackend(sql_url)
        return MemoryQueueBackend()
    if preferred == "sql" and sql_url:
        return SQLQueueBackend(sql_url)
    return MemoryQueueBackend()
