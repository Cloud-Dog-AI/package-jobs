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

from cloud_dog_jobs.backends.registry import select_backend
from cloud_dog_jobs.backends.sql_backend import SQLQueueBackend


def test_redis_fallback_to_sql(sqlite_database_url: str) -> None:
    backend = select_backend("redis", sql_url=sqlite_database_url, redis_url="redis://127.0.0.1:9/0")
    assert isinstance(backend, SQLQueueBackend)
