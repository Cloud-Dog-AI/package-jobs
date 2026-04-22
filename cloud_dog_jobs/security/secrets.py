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

# cloud_dog_jobs — Secret exclusion checks
"""Helpers to detect and reject likely secrets in payloads."""

from __future__ import annotations

from typing import Any

_SECRET_TOKENS = ("password", "secret", "token", "api_key", "private_key", "credential")


def payload_contains_secret(payload: Any) -> bool:
    """Handle payload contains secret."""
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_l = str(key).lower()
            if any(token in key_l for token in _SECRET_TOKENS):
                return True
            if payload_contains_secret(value):
                return True
        return False
    if isinstance(payload, list):
        return any(payload_contains_secret(item) for item in payload)
    if isinstance(payload, str):
        value_l = payload.lower()
        return any(token in value_l for token in ("bearer ", "sk-", "-----begin", "xox", "ghp_"))
    return False


def assert_no_secrets(payload: Any) -> None:
    """Handle assert no secrets."""
    if payload_contains_secret(payload):
        raise ValueError("Payload appears to contain secret material")
