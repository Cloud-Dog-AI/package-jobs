# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
# Licensed under the Apache License, Version 2.0

"""cloud_dog_jobs.broker — Priority queues, tenant fair-share, and capacity enforcement.

W28B-307: Extends cloud_dog_jobs with broker primitives for agentic workloads.
"""

from cloud_dog_jobs.broker.priority import Priority, PriorityQueue
from cloud_dog_jobs.broker.fairshare import FairShareScheduler, TenantQuota
from cloud_dog_jobs.broker.capacity import CapacityEnforcer, ResourceSlot
from cloud_dog_jobs.broker.registry import ServiceRegistry, ServiceRecord
from cloud_dog_jobs.broker.deadlock import DeadlockGuard

__all__ = [
    "CapacityEnforcer",
    "DeadlockGuard",
    "FairShareScheduler",
    "Priority",
    "PriorityQueue",
    "ResourceSlot",
    "ServiceRecord",
    "ServiceRegistry",
    "TenantQuota",
]
