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
"""Public API for cloud_dog_jobs."""

from cloud_dog_jobs.admin.service import AdminService
from cloud_dog_jobs.async_jobs.mcp_adapter import MCPAsyncJobAdapter
from cloud_dog_jobs.backends.hybrid_backend import HybridQueueBackend
from cloud_dog_jobs.backends.memory_backend import MemoryQueueBackend
from cloud_dog_jobs.backends.redis_backend import RedisQueueBackend
from cloud_dog_jobs.backends.sql_backend import SQLQueueBackend
from cloud_dog_jobs.domain.enums import JobStatus
from cloud_dog_jobs.domain.models import Job, JobRequest
from cloud_dog_jobs.domain.state_machine import JobStateMachine
from cloud_dog_jobs.extensions.fallback_policies import FallbackAction, FallbackPolicy, FallbackPolicyManager
from cloud_dog_jobs.extensions.state_extensions import register_state_extension
from cloud_dog_jobs.mcp.job_tools import create_job_tools
from cloud_dog_jobs.queue import JobQueue
from cloud_dog_jobs.worker.worker import Worker

__all__ = [
    "AdminService",
    "HybridQueueBackend",
    "Job",
    "JobQueue",
    "JobRequest",
    "JobStateMachine",
    "JobStatus",
    "MCPAsyncJobAdapter",
    "MemoryQueueBackend",
    "FallbackAction",
    "FallbackPolicy",
    "FallbackPolicyManager",
    "create_job_tools",
    "register_state_extension",
    "RedisQueueBackend",
    "SQLQueueBackend",
    "Worker",
]

__version__ = "0.2.0"
