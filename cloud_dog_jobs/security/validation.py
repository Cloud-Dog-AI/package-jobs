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

# cloud_dog_jobs — Security validation utilities
"""Payload and callback URL validation helpers."""

from __future__ import annotations

from urllib.parse import urlparse


def validate_payload_size(payload: dict, max_bytes: int = 16_384) -> None:
    """Raise when payload exceeds maximum byte size."""
    size = len(str(payload).encode("utf-8"))
    if size > max_bytes:
        raise ValueError(f"Payload size {size} exceeds max {max_bytes}")


def validate_callback_url(url: str) -> None:
    """Allow only HTTP/HTTPS callback URLs."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only http/https callback URLs are allowed")
