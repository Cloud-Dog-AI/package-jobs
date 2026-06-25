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

# cloud_dog_jobs — PS-75 Job & Queue Management for Cloud-Dog services
"""
Public API for cloud_dog_jobs.

Provides pluggable queue backends (SQL, Redis/Valkey, hybrid, in-memory),
safe multi-worker execution, concurrency controls, retry/backoff/cancellation,
progress tracking, configurable state machines, admin tooling, async completion
patterns, callback webhooks, and full audit/observability.
"""

__version__ = "0.1.0"

# Public API will be exported here after implementation:
# from cloud_dog_jobs.domain.models import Job, JobRequest, JobResult, JobContext, Progress
# from cloud_dog_jobs.domain.state_machine import StateMachine
# from cloud_dog_jobs.backends.registry import BackendRegistry
# from cloud_dog_jobs.worker.engine import Worker
# from cloud_dog_jobs.admin.service import AdminService
