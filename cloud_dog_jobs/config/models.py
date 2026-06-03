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

# cloud_dog_jobs — Config models
"""Configuration models for backend, retry, and maintenance settings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class BackendSettings:
    """Represent backend settings."""
    preferred: str = "memory"
    sql_url: str | None = None
    redis_url: str | None = None


@dataclass(frozen=True, slots=True)
class RetrySettings:
    """Represent retry settings."""
    max_attempts: int = 3
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0


@dataclass(frozen=True, slots=True)
class MaintenanceSettings:
    """Represent maintenance settings."""
    claim_timeout_seconds: int = 60
    max_age_seconds: int = 86_400


@dataclass(frozen=True, slots=True)
class ConcurrencySettings:
    """Concurrency cap settings (PS-95 §6.2, W28D-304)."""
    global_max: int = 10
    per_type_max: int = 5
    per_tenant_max: int = 3
    per_user_max: int = 2


@dataclass(frozen=True, slots=True)
class ResourcePoolSettings:
    """Resource pool limits (PS-95 §6.1, W28D-304)."""
    limits: dict[str, int] | None = None


@dataclass(frozen=True, slots=True)
class JobsConfig:
    """Represent jobs config."""
    backend: BackendSettings = BackendSettings()
    retry: RetrySettings = RetrySettings()
    maintenance: MaintenanceSettings = MaintenanceSettings()
    payload_max_bytes: int = 16_384
    concurrency: ConcurrencySettings = ConcurrencySettings()
    resource_pool: ResourcePoolSettings = ResourcePoolSettings()


def jobs_config_from_dict(raw: dict[str, Any]) -> JobsConfig:
    """Handle jobs config from dict."""
    backend_raw = raw.get("backend") if isinstance(raw.get("backend"), dict) else {}
    retry_raw = raw.get("retry") if isinstance(raw.get("retry"), dict) else {}
    maint_raw = raw.get("maintenance") if isinstance(raw.get("maintenance"), dict) else {}
    conc_raw = raw.get("concurrency") if isinstance(raw.get("concurrency"), dict) else {}
    rpool_raw = raw.get("resource_pool") if isinstance(raw.get("resource_pool"), dict) else {}

    rpool_limits = rpool_raw.get("limits")
    if isinstance(rpool_limits, dict):
        rpool_limits = {str(k): int(v) for k, v in rpool_limits.items()}
    else:
        rpool_limits = None

    return JobsConfig(
        backend=BackendSettings(
            preferred=str(backend_raw.get("preferred", "memory")),
            sql_url=(str(backend_raw["sql_url"]) if backend_raw.get("sql_url") else None),
            redis_url=(str(backend_raw["redis_url"]) if backend_raw.get("redis_url") else None),
        ),
        retry=RetrySettings(
            max_attempts=int(retry_raw.get("max_attempts", 3)),
            initial_delay_seconds=float(retry_raw.get("initial_delay_seconds", 1.0)),
            max_delay_seconds=float(retry_raw.get("max_delay_seconds", 30.0)),
        ),
        maintenance=MaintenanceSettings(
            claim_timeout_seconds=int(maint_raw.get("claim_timeout_seconds", 60)),
            max_age_seconds=int(maint_raw.get("max_age_seconds", 86_400)),
        ),
        payload_max_bytes=int(raw.get("payload_max_bytes", 16_384)),
        concurrency=ConcurrencySettings(
            global_max=int(conc_raw.get("global_max", 10)),
            per_type_max=int(conc_raw.get("per_type_max", 5)),
            per_tenant_max=int(conc_raw.get("per_tenant_max", 3)),
            per_user_max=int(conc_raw.get("per_user_max", 2)),
        ),
        resource_pool=ResourcePoolSettings(limits=rpool_limits),
    )
